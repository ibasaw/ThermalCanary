# IbaSaW SysGauge

A hardware monitoring dashboard for Linux — built with PyQt6.

Circular arc gauges for CPU and GPU metrics, with smooth 60fps animation, a rolling average to stabilise noisy sensor readings, and a live settings sidebar.

![SysGauge preview](preview.png)

## Gauges

| Row | Gauge | Source |
|-----|-------|--------|
| CPU | CPU Temperature | `coretemp / Package id 0` via psutil |
| CPU | CPU Usage % | psutil |
| CPU | RAM Usage % | psutil |
| GPU | GPU Temperature | pynvml (NVML direct — no subprocess) |
| GPU | GPU Fan Speed % | pynvml |
| GPU | GPU VRAM Usage % | pynvml |

## Requirements

- Linux (Python 3.10+)
- NVIDIA GPU with drivers installed (for GPU metrics; CPU/RAM gauges work without)

Supported package managers for automatic dependency install: **apt** (Debian/Ubuntu), **dnf** (Fedora/RHEL), **pacman** (Arch), **zypper** (openSUSE).

## Install

```bash
git clone https://github.com/ibasaw/sysgauge.git
cd sysgauge
bash install.sh
```

The installer will:
1. Detect your distro and check/install system packages (Python 3.10+, XCB cursor library) — asks for confirmation before installing anything
2. Copy the app package and icon to `~/.local/share/sysgauge/`
3. Create a Python venv and install all Python dependencies
4. Verify all dependencies are working
5. Copy the default config to `~/.config/sysgauge/config.yaml` (only on first install — never overwrites existing config)
6. Register the app in `~/.local/share/applications/` for taskbar icon support
7. Register an autostart entry so the app launches automatically on login (8s delay)
8. Kill any running instance and launch the app immediately

The clone folder is only needed to run the installer. You can delete it afterwards.

## Installed file layout

| Path | What |
|------|------|
| `~/.local/share/sysgauge/sysgauge/` | App package |
| `~/.local/share/sysgauge/assets/` | App icon |
| `~/.local/share/sysgauge/venv/` | Python virtual environment |
| `~/.local/share/icons/hicolor/*/apps/sysgauge.png` | System icon (taskbar) |
| `~/.local/share/applications/sysgauge.desktop` | App entry (taskbar icon) |
| `~/.config/sysgauge/config.yaml` | User configuration |
| `~/.config/autostart/sysgauge.desktop` | Autostart on login |

## Launch manually

```bash
cd ~/.local/share/sysgauge && venv/bin/python3 -m sysgauge
```

## Settings

Press **Ctrl+,** or click the gear button (top-right) to open the settings sidebar. Changes apply live without restarting.

Available settings: monitor selection, poll rate, smoothing window, background/gauge colors, and corner radius.

## Configuration file

`~/.config/sysgauge/config.yaml` — the settings sidebar writes this automatically. You can also edit it by hand; changes take effect on next launch.

```yaml
screen_index: 2       # which monitor (0 = first, 1 = second, 2 = third...)
poll_ms:      1000    # sensor poll interval in milliseconds
smooth_n:     5       # rolling average window (number of samples)

bg_color:    "#252040"   # window background
inner_color: "#1e1a35"   # gauge inner circle
track_color: "#332e55"   # arc track (unfilled)
tick_color:  "#3d3860"   # tick marks
panel_radius: 18         # gauge border radius (px)
```

## Autostart caveat

The autostart entry uses `DISPLAY=:1` which is correct for most single-user setups. If your display number differs (check with `echo $DISPLAY`), edit `~/.config/autostart/sysgauge.desktop` accordingly.

## Uninstall

```bash
bash uninstall.sh
```

Removes the app, venv, icon, config, and all desktop entries after confirmation.

## Architecture

- **SensorWorker** runs in a `QThread` — all sensor reads are off the main thread
- GPU metrics use **pynvml** (direct NVML calls, <1ms each) instead of `subprocess nvidia-smi` (fork/exec causes observer-effect thermal spikes of 10–15°C)
- CPU temp and usage are stabilised with a rolling average (`smooth_n` samples, default 5)
- **Config** is reactive: `Config(QObject)` emits a signal on every change, enabling live apply without restart
- Single-instance lock via `fcntl.flock` on `$XDG_RUNTIME_DIR/sysgauge.lock`

## License

MIT — see [LICENSE](LICENSE)
