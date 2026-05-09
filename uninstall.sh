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

TC_APP_UUID="99e18195-0d42-5165-826c-b6a04d5ed4d4"

# Kill all running instances by app UUID (zero false positives).
_tc_pids=$(pgrep -f "$TC_APP_UUID" 2>/dev/null || true)
if [[ -n "$_tc_pids" ]]; then
  kill $_tc_pids 2>/dev/null || true
  sleep 0.5
  echo "→ Stopped running instance(s)"
fi
rm -f "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/thermalcanary.lock"
rm -f "$HOME/.cache/thermalcanary/thermalcanary.lock"

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
