"""
thermalcanary-setup — desktop integration for pipx / pip installs.

Creates:
  ~/.local/share/applications/thermalcanary.desktop
  ~/.config/autostart/thermalcanary.desktop
  ~/.local/share/icons/hicolor/256x256/apps/thermalcanary.png
"""

import importlib.resources
import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path


_DESKTOP = """\
[Desktop Entry]
Type=Application
Name=Thermal Canary
GenericName=Hardware Monitor
Comment=GPU and CPU thermal gauges for Linux gamers
Icon=thermalcanary
Exec=thermalcanary
Terminal=false
Categories=Utility;System;Monitor;
Keywords=temperature;thermal;gpu;cpu;ram;gauge;hardware;monitor;sensor;
StartupWMClass=thermalcanary
StartupNotify=false
"""

_AUTOSTART = """\
[Desktop Entry]
Type=Application
Name=Thermal Canary
Exec=bash -c 'sleep 8 && thermalcanary'
Hidden=false
X-GNOME-Autostart-enabled=true
"""


def main() -> None:
    if "--uninstall" in sys.argv:
        _uninstall()
        return
    _install()


def _install() -> None:
    home = Path.home()

    icon_dst = home / ".local/share/icons/hicolor/256x256/apps/thermalcanary.png"
    icon_dst.parent.mkdir(parents=True, exist_ok=True)
    pkg = importlib.resources.files("thermalcanary")
    with importlib.resources.as_file(pkg / "assets" / "icon.png") as src:
        shutil.copy2(src, icon_dst)
    print(f"icon      -> {icon_dst}")

    apps = home / ".local/share/applications/thermalcanary.desktop"
    apps.parent.mkdir(parents=True, exist_ok=True)
    apps.write_text(_DESKTOP)
    print(f"app entry -> {apps}")

    autostart = home / ".config/autostart/thermalcanary.desktop"
    autostart.parent.mkdir(parents=True, exist_ok=True)
    autostart.write_text(_AUTOSTART)
    print(f"autostart -> {autostart}")

    subprocess.run(["update-desktop-database", str(apps.parent)],  # nosec B603 B607
                   capture_output=True)
    subprocess.run(["gtk-update-icon-cache", "-f", "-t",  # nosec B603 B607
                    str(icon_dst.parent.parent.parent)],
                   capture_output=True)

    print("\nDone. Thermal Canary will appear in your app grid and auto-start on login.")


def _uninstall() -> None:
    home = Path.home()
    for p in [
        home / ".local/share/applications/thermalcanary.desktop",
        home / ".config/autostart/thermalcanary.desktop",
        home / ".local/share/icons/hicolor/256x256/apps/thermalcanary.png",
        Path(f"/run/user/{os.getuid()}/thermalcanary.lock"),
    ]:
        if p.exists():
            p.unlink()
            print(f"removed {p}")
    config_dir = home / ".config/thermalcanary"
    if config_dir.exists():
        shutil.rmtree(config_dir)
        print(f"removed {config_dir}")
    subprocess.run(["update-desktop-database",  # nosec B603 B607
                    str(home / ".local/share/applications")], capture_output=True)
    print("Done.")
