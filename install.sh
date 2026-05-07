#!/usr/bin/env bash
# IbaSaW SysGauge installer
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sysgauge"
CFG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/sysgauge"
VENV="$DATA_DIR/venv"
SCRIPT="$DATA_DIR/sysgauge.py"
DESKTOP="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/sysgauge.desktop"

echo "=== IbaSaW SysGauge Installer ==="
echo "→ Project: $PROJECT_DIR"

# ── System checks ────────────────────────────────────────────────────────────
echo "→ Checking system requirements..."

# Ubuntu / Debian only
if ! command -v apt &>/dev/null; then
  echo "ERROR: apt not found — this installer requires Ubuntu / Debian." >&2
  exit 1
fi

# NVIDIA driver
if ! command -v nvidia-smi &>/dev/null; then
  echo "WARNING: nvidia-smi not found — GPU gauges will show 0." >&2
  echo "         Install NVIDIA drivers: sudo ubuntu-drivers autoinstall" >&2
fi

# ── System packages ──────────────────────────────────────────────────────────
echo "→ Checking system packages..."

MISSING=()
for pkg in python3 python3-venv python3-pip libxcb-cursor0 libxcb-xinerama0; do
  dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed" \
    || MISSING+=("$pkg")
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo ""
  echo "  The following system packages will be installed via apt:"
  for pkg in "${MISSING[@]}"; do
    echo "    - $pkg"
  done
  echo ""
  read -r -p "  Proceed with installation? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
  sudo apt install -y "${MISSING[@]}"
else
  echo "  All system packages already installed."
fi

# Python version check (need 3.10+)
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
cp "$PROJECT_DIR/sysgauge.py" "$DATA_DIR/sysgauge.py"
chmod +x "$SCRIPT"

echo "→ Installing icon..."
ICON_SRC="$PROJECT_DIR/sysgauge.png"
HICOLOR="$HOME/.local/share/icons/hicolor"
for size in 512 256 128 48; do mkdir -p "$HICOLOR/${size}x${size}/apps"; done
for size in 512 256 128 48; do
    cp -f "$ICON_SRC" "$HICOLOR/${size}x${size}/apps/sysgauge.png"
done
cp -f "$ICON_SRC" "$DATA_DIR/sysgauge.png"
gtk-update-icon-cache -f -t "$HICOLOR" 2>/dev/null || true

echo "→ Installing application entry..."
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cat > "$APPS_DIR/sysgauge.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=IbaSaW SysGauge
Comment=Premium hardware gauge monitor
Icon=sysgauge
Exec=$VENV/bin/python3 $SCRIPT
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

# Verify critical imports
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
Comment=Premium hardware gauge monitor
Icon=sysgauge
Exec=bash -c 'sleep 8 && DISPLAY=:1 $VENV/bin/python3 $SCRIPT'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF

# ── Launch ───────────────────────────────────────────────────────────────────
echo ""
echo "=== Done! ==="
echo "  App:       $SCRIPT"
echo "  Config:    $CFG_DIR/config.yaml"
echo "  Autostart: enabled (8s delay after login)"
echo ""
echo "→ Launching SysGauge..."
pkill -f "sysgauge.py" 2>/dev/null || true
sleep 0.5
rm -f "${XDG_RUNTIME_DIR:-/tmp}/sysgauge.lock"
DISPLAY=:1 "$VENV/bin/python3" "$SCRIPT" &
