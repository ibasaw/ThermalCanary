#!/usr/bin/env bash
# IbaSaW SysGauge installer
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sysgauge"
CFG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/sysgauge"
VENV="$DATA_DIR/venv"
DESKTOP="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/sysgauge.desktop"

echo "=== IbaSaW SysGauge Installer ==="
echo "→ Project: $PROJECT_DIR"

# ── Distro detection ─────────────────────────────────────────────────────────
if [[ -f /etc/os-release ]]; then
  source /etc/os-release
  DISTRO_ID="${ID:-unknown}"
  DISTRO_LIKE="${ID_LIKE:-}"
else
  DISTRO_ID="unknown"
  DISTRO_LIKE=""
fi

detect_pkg_manager() {
  if command -v apt &>/dev/null; then   echo "apt";    return; fi
  if command -v dnf &>/dev/null; then   echo "dnf";    return; fi
  if command -v pacman &>/dev/null; then echo "pacman"; return; fi
  if command -v zypper &>/dev/null; then echo "zypper"; return; fi
  echo "unknown"
}

PKG_MGR="$(detect_pkg_manager)"

if [[ "$PKG_MGR" == "unknown" ]]; then
  echo "WARNING: Unsupported package manager — cannot install system packages automatically." >&2
  echo "         You may need to install Python 3.10+, python3-venv, and XCB cursor libraries manually." >&2
fi

# ── System checks ────────────────────────────────────────────────────────────
echo "→ Checking system requirements..."

if ! command -v nvidia-smi &>/dev/null; then
  echo "WARNING: nvidia-smi not found — GPU gauges will show 0." >&2
  echo "         Install NVIDIA drivers for your distro to enable GPU monitoring." >&2
fi

# ── System packages ──────────────────────────────────────────────────────────
echo "→ Checking system packages..."

install_packages_apt() {
  local missing=()
  for pkg in python3 python3-venv python3-pip libxcb-cursor0 libxcb-xinerama0 wmctrl; do
    dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed" \
      || missing+=("$pkg")
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo ""
    echo "  The following system packages will be installed via apt:"
    for pkg in "${missing[@]}"; do echo "    - $pkg"; done
    echo ""
    read -r -p "  Proceed? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    sudo apt install -y "${missing[@]}"
  else
    echo "  All system packages already installed."
  fi
}

install_packages_dnf() {
  local missing=()
  for pkg in python3 python3-pip xcb-util-cursor libxcb; do
    rpm -q "$pkg" &>/dev/null || missing+=("$pkg")
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo ""
    echo "  The following system packages will be installed via dnf:"
    for pkg in "${missing[@]}"; do echo "    - $pkg"; done
    echo ""
    read -r -p "  Proceed? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    sudo dnf install -y "${missing[@]}"
  else
    echo "  All system packages already installed."
  fi
}

install_packages_pacman() {
  local missing=()
  for pkg in python python-pip xcb-util-cursor; do
    pacman -Qi "$pkg" &>/dev/null || missing+=("$pkg")
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo ""
    echo "  The following system packages will be installed via pacman:"
    for pkg in "${missing[@]}"; do echo "    - $pkg"; done
    echo ""
    read -r -p "  Proceed? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    sudo pacman -S --noconfirm "${missing[@]}"
  else
    echo "  All system packages already installed."
  fi
}

install_packages_zypper() {
  local missing=()
  for pkg in python3 python3-pip xcb-util-cursor libxcb1; do
    rpm -q "$pkg" &>/dev/null || missing+=("$pkg")
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo ""
    echo "  The following system packages will be installed via zypper:"
    for pkg in "${missing[@]}"; do echo "    - $pkg"; done
    echo ""
    read -r -p "  Proceed? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    sudo zypper install -y "${missing[@]}"
  else
    echo "  All system packages already installed."
  fi
}

case "$PKG_MGR" in
  apt)    install_packages_apt ;;
  dnf)    install_packages_dnf ;;
  pacman) install_packages_pacman ;;
  zypper) install_packages_zypper ;;
  *)      echo "  Skipping automatic package install (unsupported distro)." ;;
esac

# Python version check (need 3.10+)
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found — install Python 3.10+ and re-run." >&2
  exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [[ "$PY_MAJOR" -lt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ) ]]; then
  echo "ERROR: Python 3.10+ required, found $PY_VER" >&2
  exit 1
fi
echo "  Python $PY_VER OK"

# ── App files ────────────────────────────────────────────────────────────────
echo "→ Copying app to $DATA_DIR..."
mkdir -p "$DATA_DIR"
rm -rf "$DATA_DIR/sysgauge"
cp -r "$PROJECT_DIR/sysgauge" "$DATA_DIR/sysgauge"
cp -r "$PROJECT_DIR/assets"   "$DATA_DIR/assets"

echo "→ Installing icon..."
ICON_SRC="$PROJECT_DIR/assets/sysgauge.png"
HICOLOR="$HOME/.local/share/icons/hicolor"
for size in 512 256 128 48; do mkdir -p "$HICOLOR/${size}x${size}/apps"; done
for size in 512 256 128 48; do
  cp -f "$ICON_SRC" "$HICOLOR/${size}x${size}/apps/sysgauge.png"
done
gtk-update-icon-cache -f -t "$HICOLOR" 2>/dev/null || true

echo "→ Installing application entry..."
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cat > "$APPS_DIR/sysgauge.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=IbaSaW SysGauge
Comment=Hardware gauge monitor
Icon=sysgauge
Exec=$VENV/bin/python3 -m sysgauge
Path=$DATA_DIR
Terminal=false
Categories=Utility;System;Monitor;
StartupWMClass=sysgauge
StartupNotify=false
EOF
update-desktop-database "$APPS_DIR" 2>/dev/null || true

# ── Python venv + dependencies ───────────────────────────────────────────────
echo "→ Creating Python virtual environment..."
python3 -m venv "$VENV"

echo "→ Installing Python dependencies..."
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q PyQt6 psutil nvidia-ml-py pyyaml

echo "→ Verifying dependencies..."
"$VENV/bin/python3" -c "import PyQt6, psutil, pynvml, yaml" \
  && echo "  All dependencies OK" \
  || { echo "ERROR: dependency check failed" >&2; exit 1; }

# ── Config ───────────────────────────────────────────────────────────────────
echo "→ Installing config..."
mkdir -p "$CFG_DIR"
cp -n "$PROJECT_DIR/config.example.yaml" "$CFG_DIR/config.yaml" \
  && echo "  Created $CFG_DIR/config.yaml" \
  || echo "  Config already exists — not overwritten"

# ── Autostart ────────────────────────────────────────────────────────────────
echo "→ Creating autostart entry..."
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=IbaSaW SysGauge
Comment=Hardware gauge monitor
Icon=sysgauge
Exec=bash -c 'sleep 8 && DISPLAY=:1 $VENV/bin/python3 -m sysgauge'
Path=$DATA_DIR
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF

# ── Launch ───────────────────────────────────────────────────────────────────
echo ""
echo "=== Done! ==="
echo "  App:       $DATA_DIR/sysgauge/"
echo "  Config:    $CFG_DIR/config.yaml"
echo "  Autostart: enabled (8s delay after login)"
echo ""
echo "→ Launching SysGauge..."
pkill -f "sysgauge" 2>/dev/null || true
sleep 0.5
rm -f "${XDG_RUNTIME_DIR:-/tmp}/sysgauge.lock"
DISPLAY=:1 "$VENV/bin/python3" -m sysgauge &
disown
