<p align="center">
  <img src="https://raw.githubusercontent.com/ibasaw/thermalcanary/main/assets/logo.png" alt="Thermal Canary" width="600">
</p>

<p align="center">
  <a href="https://github.com/ibasaw/thermalcanary/actions/workflows/ci.yml"><img src="https://github.com/ibasaw/thermalcanary/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/ibasaw/thermalcanary/main/coverage-badge.json&cacheSeconds=300" alt="Coverage">
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/ibasaw/thermalcanary/main/mutation-badge.json&cacheSeconds=300" alt="Mutation score">
  <a href="https://pypi.org/project/thermalcanary/"><img src="https://img.shields.io/pypi/v/thermalcanary.svg" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/platform-Linux-lightgrey.svg" alt="Platform: Linux">
</p>

The Linux software for dedicated hardware monitoring screens — like AIDA64's sensor panel, but native to your desktop.

6 circular arc gauges (CPU temp, usage, RAM · GPU temp, fan, VRAM) built with PyQt6 and pynvml.
Smooth 60fps animation, rolling average stabilisation, dynamic heat colors. Auto-starts on login.

**Built for dedicated monitoring screens** — works out of the box on stretched panels (1920×480), small IPS monitors, or any secondary display you use as a permanent hardware panel.

> ⚠ **Important** — this is NOT an overlay. Thermal Canary is a fullscreen app intended for a **dedicated monitor**. Don't try to use it as an in-game overlay (use MangoHud for that).

**Fully responsive** — gauges scale to any resolution and orientation: ultrawide, portrait, rotated, compact.

**One-command install** — `pipx install thermalcanary` and you're done.

### Dedicated monitoring screen setup

Plug in a secondary screen (a stretched panel, a small IPS monitor, anything), select it in the Settings sidebar under **Monitor**, and click **Set as default**. Thermal Canary will always open on that screen at login — no configuration files to edit.  

![Thermal Canary preview](https://raw.githubusercontent.com/ibasaw/thermalcanary/main/screenshot.png)

![Thermal Canary with settings sidebar open](https://raw.githubusercontent.com/ibasaw/thermalcanary/main/screenshot-settings.png)

## Gauges

| Row | Gauge | Source |
|-----|-------|--------|
| CPU | CPU Temperature | `psutil.sensors_temperatures()` — coretemp/k10temp (configurable) |
| CPU | CPU Usage % | psutil |
| CPU | RAM Usage % | psutil |
| GPU | GPU Temperature | NVIDIA: pynvml · AMD: sysfs hwmon · Intel: xe/i915 sysfs |
| GPU | GPU Fan Speed % | NVIDIA: pynvml · AMD: sysfs hwmon (0% = fans stopped or AMD integrated GPU with no fan) |
| GPU | GPU VRAM Usage % | NVIDIA: pynvml · AMD: sysfs hwmon · Intel: always 0 (not exposed by driver) |

## Requirements

> **Tested and supported on Ubuntu 24.04 LTS.** Other distros (Fedora, Arch, openSUSE) are supported by the installer but have not been formally tested yet. Ubuntu versions below 24.04 may work but are not guaranteed.

The installer checks and installs everything automatically. Here is the full dependency list:

**System packages** (installed automatically via your distro's package manager):

| Dependency | Purpose |
|------------|---------|
| Python 3.10+ | Runtime |
| `python3-venv` | Isolated Python environment |
| `lm-sensors` | Populates `/sys/class/hwmon` for CPU temperature |
| XCB cursor libs (`libxcb-cursor0` / `xcb-util-cursor`) | Required by PyQt6 on X11 |

**NVIDIA driver** — checked separately. The installer prints distro-specific install instructions if the driver is missing. GPU gauges (temperature, fan, VRAM) require the driver for NVIDIA; AMD and Intel GPUs are read via sysfs without any driver installation.

> **GPU backends**: NVIDIA (`pynvml`, direct NVML — no `nvidia-smi` subprocess), AMD (`amdgpu` sysfs hwmon — kernel driver, no extra install), Intel (`xe`/`i915` sysfs hwmon). The backend is auto-detected at startup or can be forced in the Settings sidebar. If no GPU is detected, all three GPU gauges show `—`.

**Python libraries** (installed automatically into a venv):

| Library | Purpose |
|---------|---------|
| `PyQt6` | GUI framework |
| `psutil` | CPU temperature, CPU usage, RAM usage |
| `nvidia-ml-py` (`pynvml`) | GPU metrics via direct NVML calls — no `nvidia-smi` subprocess |
| `PyYAML` | Config file read/write |

Supported package managers: **apt** (Debian/Ubuntu), **dnf** (Fedora/RHEL), **pacman** (Arch), **zypper** (openSUSE).

## Install

### Prerequisites

Install these system packages once before the first run (needed by PyQt6 on X11):

| Distro | Command |
|--------|---------|
| Ubuntu / Debian | `sudo apt install lm-sensors libxcb-cursor0 libxcb-xinerama0` |
| Fedora / RHEL | `sudo dnf install lm_sensors xcb-util-cursor` |
| Arch | `sudo pacman -S lm_sensors xcb-util-cursor` |
| openSUSE | `sudo zypper install lm-sensors xcb-util-cursor` |

**NVIDIA users**: GPU gauges require the proprietary NVIDIA driver. Without it the three GPU gauges show `—` but everything else works fine.

### Install

```bash
pipx install thermalcanary
thermalcanary
```

**Thermal Canary runs entirely as your user — no root needed at runtime.**

On first launch, it automatically installs the app grid icon and sets up autostart on login (8-second delay to let the desktop session initialize). No extra commands needed.

### Migrating from a previous `bash install.sh` install

```bash
# Remove old install.sh files
rm -rf ~/.local/share/thermalcanary
rm -f ~/.config/autostart/thermalcanary.desktop
rm -f ~/.local/share/applications/thermalcanary.desktop

# Install fresh
pipx install thermalcanary
thermalcanary
```

## Installed file layout

| Path | What |
|------|------|
| `~/.local/share/pipx/venvs/thermalcanary/` | pipx-managed venv |
| `~/.local/bin/thermalcanary` | Entry point |
| `~/.local/share/icons/hicolor/256x256/apps/thermalcanary.png` | App icon |
| `~/.local/share/applications/thermalcanary.desktop` | App grid entry |
| `~/.config/thermalcanary/config.yaml` | User configuration (auto-saved by the app) |
| `~/.config/autostart/thermalcanary.desktop` | Autostart on login (8s delay) |

## Launch manually

```bash
thermalcanary
```

## Settings sidebar

Two buttons sit in the top-right corner: **⚙** opens the settings sidebar, **✕** closes the app (with confirmation). Press **Ctrl+,** to toggle the sidebar from the keyboard. All changes apply live without restarting.

| Section | Setting | Description |
|---------|---------|-------------|
| Display | Monitor | Which monitor to display on — works with any number of monitors and any orientation |
| Display | Set as default | Save the current monitor as the startup monitor — the app always opens here on launch |
| Sampling | Poll rate | Sensor poll interval (100ms – 10s) |
| Sampling | Smoothing | Rolling average window size (1–60 samples) |
| Colors | Background | Window background color |
| Colors | Inner circle | Gauge center fill color |
| Colors | Arc track | Unfilled arc track color |
| Colors | Tick marks | Tick mark color |

The **Reset to defaults** button restores all colors and sampling values to factory settings while keeping your saved default monitor.

## Configuration file

`~/.config/thermalcanary/config.yaml` is written automatically by the settings sidebar. You can also edit it by hand; changes take effect on next launch.

```yaml
poll_ms:  1000     # sensor poll interval in milliseconds
smooth_n: 5        # rolling average window (number of samples)

bg_color:    "#252040"   # window background
inner_color: "#1e1a35"   # gauge inner circle
track_color: "#332e55"   # arc track (unfilled)
tick_color:  "#3d3860"   # tick marks

# screen_index and default_screen_index are set via the Settings sidebar
```

## Autostart caveat

The autostart entry inherits `$DISPLAY` from the login session, falling back to `:0`. If the app doesn't start on login, check your display number with `echo $DISPLAY` and edit `~/.config/autostart/thermalcanary.desktop` accordingly.

## Uninstall

```bash
thermalcanary-setup --uninstall   # removes icon, desktop entry, autostart, config dir, lock file
pipx uninstall thermalcanary      # removes venv and entry point
```

## Architecture

- **SensorWorker** runs in a `QThread` — all sensor reads are off the main thread
- GPU metrics use **pynvml** (direct NVML calls, <1ms) — never `subprocess nvidia-smi` which causes observer-effect CPU temperature spikes of 10–15°C
- CPU temp and usage are stabilised with a `deque`-based rolling average
- **Config** is reactive: `Config(QObject)` emits a signal on every change, all settings apply live
- Window runs **fullscreen** (`showFullScreen`) — no title bar, fills the entire monitor. This bypasses Mutter's `WM_NORMAL_HINTS` enforcement which otherwise clamps window geometry to `minimumSizeHint`, making maximize unreliable on short or rotated monitors
- Monitor switching uses an event-driven state machine: `showNormal()` → wait for `WindowStateChange` (Mutter ack) → `windowHandle().setScreen()` + `setGeometry()` → 50ms → `showFullScreen()`. `wmctrl` is called once after first show to set `_NET_WM_STATE_SKIP_TASKBAR/SKIP_PAGER` (hides the window from GNOME Dash without using `Qt.WindowType.Tool`, which would break cross-monitor placement on Mutter)
- Monitor indices are validated against actual connected screens at startup — safe on any number of monitors
- Single-instance lock via `fcntl.flock` on `$XDG_RUNTIME_DIR/thermalcanary.lock`
- Runs entirely as the logged-in user — no root required at runtime

## License

MIT — see [LICENSE](LICENSE)
