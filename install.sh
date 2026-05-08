#!/usr/bin/env bash
# Thermal Canary installer
#
# Usage:
#   bash install.sh               — check deps, print any missing, then install app
#   bash install.sh --install-deps — same but also invoke sudo to install missing system packages
#
# The app itself runs entirely as your user. sudo is only used for system
# package installation, and only when you explicitly pass --install-deps.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/thermalcanary"
CFG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/thermalcanary"
VENV="$DATA_DIR/venv"
DESKTOP="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/thermalcanary.desktop"

AUTO_INSTALL=0
for arg in "$@"; do
  [[ "$arg" == "--install-deps" ]] && AUTO_INSTALL=1
done

echo "=== Thermal Canary Installer ==="
echo "→ Project: $PROJECT_DIR"
[[ "$AUTO_INSTALL" == "1" ]] && echo "→ Mode: auto-install system dependencies (sudo will be invoked)"

# ── Distro / package manager detection ───────────────────────────────────────
if [[ -f /etc/os-release ]]; then
  source /etc/os-release
  DISTRO_ID="${ID:-unknown}"
else
  DISTRO_ID="unknown"
fi

detect_pkg_manager() {
  if command -v apt    &>/dev/null; then echo "apt";    return; fi
  if command -v dnf    &>/dev/null; then echo "dnf";    return; fi
  if command -v pacman &>/dev/null; then echo "pacman"; return; fi
  if command -v zypper &>/dev/null; then echo "zypper"; return; fi
  echo "unknown"
}

PKG_MGR="$(detect_pkg_manager)"

# ── NVIDIA driver check (informational only — never installs automatically) ──
echo ""
echo "→ Checking NVIDIA driver..."

if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "unknown")
  DRIVER_VER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1 || echo "unknown")
  echo "  NVIDIA GPU detected: $GPU_NAME (driver $DRIVER_VER) — GPU gauges enabled."
else
  echo "  WARNING: NVIDIA driver not found or not working."
  echo "  GPU gauges (temperature, fan, VRAM) will show 0. CPU/RAM gauges are unaffected."
  echo ""
  echo "  To enable GPU gauges, install the NVIDIA driver for your distro:"
  case "$PKG_MGR" in
    apt)    echo "    sudo apt install nvidia-driver" ;;
    dnf)    echo "    sudo dnf install akmod-nvidia  # requires RPM Fusion Non-Free repo" ;;
    pacman) echo "    sudo pacman -S nvidia nvidia-utils" ;;
    zypper) echo "    # See https://en.opensuse.org/SDB:NVIDIA_drivers" ;;
    *)      echo "    See https://www.nvidia.com/Download/index.aspx" ;;
  esac
  echo ""
  read -r -p "  Continue without GPU support? [Y/n] " confirm
  [[ "$confirm" =~ ^[Nn]$ ]] && { echo "Aborted."; exit 0; }
fi

# ── System package check ──────────────────────────────────────────────────────
echo ""
echo "→ Checking system packages..."
echo "  Note: coretemp/k10temp (CPU temp sensor) are auto-loaded by the kernel — no manual setup needed."

MISSING_PKGS=()
INSTALL_CMD=""

check_and_collect_apt() {
  local pkgs=(python3 python3-venv python3-pip lm-sensors libxcb-cursor0 libxcb-xinerama0)
  for pkg in "${pkgs[@]}"; do
    dpkg -s "$pkg" &>/dev/null || MISSING_PKGS+=("$pkg")
  done
  INSTALL_CMD="sudo apt install ${MISSING_PKGS[*]}"
}

check_and_collect_dnf() {
  local pkgs=(python3 python3-pip lm_sensors xcb-util-cursor libxcb)
  for pkg in "${pkgs[@]}"; do
    rpm -q "$pkg" &>/dev/null || MISSING_PKGS+=("$pkg")
  done
  INSTALL_CMD="sudo dnf install ${MISSING_PKGS[*]}"
}

check_and_collect_pacman() {
  local pkgs=(python python-pip lm_sensors xcb-util-cursor)
  for pkg in "${pkgs[@]}"; do
    pacman -Qi "$pkg" &>/dev/null || MISSING_PKGS+=("$pkg")
  done
  INSTALL_CMD="sudo pacman -S ${MISSING_PKGS[*]}"
}

check_and_collect_zypper() {
  local pkgs=(python3 python3-pip lm-sensors xcb-util-cursor libxcb1)
  for pkg in "${pkgs[@]}"; do
    rpm -q "$pkg" &>/dev/null || MISSING_PKGS+=("$pkg")
  done
  INSTALL_CMD="sudo zypper install ${MISSING_PKGS[*]}"
}

case "$PKG_MGR" in
  apt)    check_and_collect_apt ;;
  dnf)    check_and_collect_dnf ;;
  pacman) check_and_collect_pacman ;;
  zypper) check_and_collect_zypper ;;
  *)
    echo "  WARNING: Unsupported package manager. Install manually:"
    echo "    Python 3.10+, python3-venv, lm-sensors, wmctrl, XCB cursor libs"
    ;;
esac

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
  echo ""
  echo "  Missing system packages: ${MISSING_PKGS[*]}"
  echo ""
  if [[ "$AUTO_INSTALL" == "1" ]]; then
    echo "  Installing via sudo..."
    case "$PKG_MGR" in
      apt)
        sudo apt update -qq
        sudo apt install -y "${MISSING_PKGS[@]}"
        ;;
      dnf)    sudo dnf install -y "${MISSING_PKGS[@]}" ;;
      pacman) sudo pacman -S --noconfirm "${MISSING_PKGS[@]}" ;;
      zypper) sudo zypper install -y "${MISSING_PKGS[@]}" ;;
    esac
  else
    echo "  Install them with:"
    echo "    $INSTALL_CMD"
    echo ""
    echo "  Then re-run this installer, or re-run with --install-deps to let it invoke sudo:"
    echo "    bash install.sh --install-deps"
    echo ""
    read -r -p "  Packages not yet installed. Continue anyway? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
  fi
else
  echo "  All system packages already installed."
fi

# ── Python version check ──────────────────────────────────────────────────────
echo ""
echo "→ Checking Python version..."
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
echo ""
echo "→ Copying app to $DATA_DIR..."
mkdir -p "$DATA_DIR"
rm -rf "$DATA_DIR/thermalcanary"
cp -r "$PROJECT_DIR/thermalcanary" "$DATA_DIR/thermalcanary"
cp -r "$PROJECT_DIR/assets"   "$DATA_DIR/assets"

echo "→ Installing icon..."
ICON_SRC="$PROJECT_DIR/assets/thermalcanary.png"
HICOLOR="$HOME/.local/share/icons/hicolor"
for size in 512 256 128 48; do mkdir -p "$HICOLOR/${size}x${size}/apps"; done
for size in 512 256 128 48; do
  cp -f "$ICON_SRC" "$HICOLOR/${size}x${size}/apps/thermalcanary.png"
done
gtk-update-icon-cache -f -t "$HICOLOR" 2>/dev/null || true

echo "→ Installing application entry..."
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cat > "$APPS_DIR/thermalcanary.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Thermal Canary
Comment=Hardware gauge monitor
Icon=thermalcanary
Exec=$VENV/bin/python3 -m thermalcanary
Path=$DATA_DIR
Terminal=false
Categories=Utility;System;Monitor;
StartupWMClass=thermalcanary
StartupNotify=false
EOF
update-desktop-database "$APPS_DIR" 2>/dev/null || true

# ── Python venv + dependencies ───────────────────────────────────────────────
echo ""
echo "→ Creating Python virtual environment..."
python3 -m venv "$VENV"

echo "→ Installing Python dependencies..."
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q PyQt6 psutil nvidia-ml-py pyyaml

echo "→ Verifying Python dependencies..."
"$VENV/bin/python3" -c "
import sys
ok = True
for mod in ('PyQt6', 'psutil', 'pynvml', 'yaml'):
    try:
        __import__(mod)
        print(f'  {mod} OK')
    except ImportError as e:
        print(f'  ERROR: {mod} — {e}', file=sys.stderr)
        ok = False
sys.exit(0 if ok else 1)
" || { echo "ERROR: dependency verification failed" >&2; exit 1; }

# ── Config ───────────────────────────────────────────────────────────────────
echo ""
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
Name=Thermal Canary
Comment=Hardware gauge monitor
Icon=thermalcanary
Exec=bash -c 'sleep 8 && DISPLAY="${DISPLAY:-:0}" $VENV/bin/python3 -m thermalcanary'
Path=$DATA_DIR
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "=== Done! ==="
echo "  App:       $DATA_DIR/thermalcanary/"
echo "  Config:    $CFG_DIR/config.yaml"
echo "  Autostart: enabled (8s delay after login)"
echo ""
echo "  Thermal Canary runs entirely as your user — no root needed at runtime."
echo ""
echo "→ Launching Thermal Canary..."
pkill -f "python3 -m thermalcanary" 2>/dev/null || true
sleep 0.5
rm -f "${XDG_RUNTIME_DIR:-$HOME/.cache/thermalcanary}/thermalcanary.lock"
DISPLAY="${DISPLAY:-:0}" "$VENV/bin/python3" -m thermalcanary &
disown
