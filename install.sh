#!/usr/bin/env bash
# IbaSaW SysGauge installer
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HOME/.local/share/sysgauge/venv"
DESKTOP="$HOME/.config/autostart/sysgauge.desktop"
SCRIPT="$PROJECT_DIR/monitor.py"

echo "=== IbaSaW SysGauge Installer ==="
echo "→ Project: $PROJECT_DIR"

echo "→ Creating Python virtual environment..."
python3 -m venv "$VENV"

echo "→ Installing dependencies..."
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q PyQt6 psutil nvidia-ml-py

chmod +x "$SCRIPT"

echo "→ Creating autostart entry..."
mkdir -p "$HOME/.config/autostart"
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
echo "Launch: $VENV/bin/python3 $SCRIPT"
echo "Autostart: enabled (8s delay after login)"
