#!/usr/bin/env bash
# IbaSaW SysGauge installer
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sysgauge"
CFG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/sysgauge"
VENV="$DATA_DIR/venv"
SCRIPT="$DATA_DIR/monitor.py"
DESKTOP="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/sysgauge.desktop"

echo "=== IbaSaW SysGauge Installer ==="
echo "→ Project: $PROJECT_DIR"

echo "→ Installing system dependencies..."
sudo apt install -y python3-venv python3-pip libxcb-cursor0 libxcb-xinerama0

echo "→ Copying app to $DATA_DIR..."
mkdir -p "$DATA_DIR"
cp "$PROJECT_DIR/monitor.py" "$DATA_DIR/monitor.py"
chmod +x "$SCRIPT"

echo "→ Creating Python virtual environment..."
python3 -m venv "$VENV"

echo "→ Installing Python dependencies..."
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q PyQt6 psutil nvidia-ml-py pyyaml

echo "→ Installing config..."
mkdir -p "$CFG_DIR"
cp -n "$PROJECT_DIR/config.example.yaml" "$CFG_DIR/config.yaml" \
  && echo "  Created $CFG_DIR/config.yaml" \
  || echo "  Config already exists — not overwritten"

echo "→ Creating autostart entry..."
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=IbaSaW SysGauge
Comment=Premium hardware gauge monitor
Exec=bash -c 'sleep 8 && DISPLAY=:1 $VENV/bin/python3 $SCRIPT'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF

echo ""
echo "=== Done! ==="
echo "  App:      $SCRIPT"
echo "  Config:   $CFG_DIR/config.yaml"
echo "  Autostart: enabled (8s delay after login)"
echo ""
echo "→ Launching SysGauge..."
DISPLAY=:1 "$VENV/bin/python3" "$SCRIPT" &
