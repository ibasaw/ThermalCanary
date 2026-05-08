#!/usr/bin/env bash
# Thermal Canary uninstaller
set -euo pipefail

DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/thermalcanary"
CFG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/thermalcanary"
DESKTOP="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/thermalcanary.desktop"
APPS_ENTRY="$HOME/.local/share/applications/thermalcanary.desktop"

echo "=== Thermal Canary Uninstaller ==="
echo ""
echo "This will remove:"
echo "  $DATA_DIR"
echo "  $CFG_DIR"
echo "  $DESKTOP"
echo "  $APPS_ENTRY"
echo ""
read -r -p "Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

pkill -f "thermalcanary" 2>/dev/null && echo "→ Stopped running instance" || true

rm -rf "$DATA_DIR"       && echo "→ Removed $DATA_DIR"
rm -rf "$CFG_DIR"        && echo "→ Removed $CFG_DIR"
rm -f  "$DESKTOP"        && echo "→ Removed autostart entry"
rm -f  "$APPS_ENTRY"     && echo "→ Removed application entry"

HICOLOR="$HOME/.local/share/icons/hicolor"
for size in 512 256 128 48; do
  rm -f "$HICOLOR/${size}x${size}/apps/thermalcanary.png"
done
gtk-update-icon-cache -f -t "$HICOLOR" 2>/dev/null || true
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "=== Uninstall complete ==="
