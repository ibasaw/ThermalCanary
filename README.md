# IbaSaW SysGauge

A premium hardware monitoring dashboard for Linux — built with PyQt6.

Circular arc gauges for CPU and GPU metrics, with smooth 60fps animation, a 5-sample rolling average to stabilise noisy sensor readings, and a fully transparent or solid background mode.

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

- Linux (Ubuntu 22.04+)
- Python 3.11+
- NVIDIA GPU with drivers installed (for GPU metrics)

## Install

```bash
git clone https://github.com/ibasaw/sysgauge.git
cd sysgauge
bash install.sh
```

The installer will:
1. Install system packages (`python3-venv`, `libxcb-cursor0`) via apt
2. Copy the app to `~/.local/share/sysgauge/`
3. Create a Python venv and install all Python dependencies
4. Copy the default config to `~/.config/sysgauge/config.yaml` (only on first install — never overwrites your edits)
5. Register an autostart entry so the app launches automatically on login (8s delay)
6. Launch the app immediately

The clone folder is only needed to run the installer. You can delete it afterwards.

## Installed file layout

| Path | What |
|------|------|
| `~/.local/share/sysgauge/sysgauge.py` | App script |
| `~/.local/share/sysgauge/venv/` | Python virtual environment |
| `~/.config/sysgauge/config.yaml` | User configuration |
| `~/.config/autostart/sysgauge.desktop` | Autostart entry |

## Launch manually

```bash
~/.local/share/sysgauge/venv/bin/python3 ~/.local/share/sysgauge/sysgauge.py
```

## Configuration

Edit `~/.config/sysgauge/config.yaml`:

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

Changes take effect on next launch. The default config template is `config.example.yaml` in the repo.

## Uninstall

```bash
bash uninstall.sh
```

Removes the app, venv, config, and autostart entry after confirmation.

## Architecture

- **SensorWorker** runs in a `QThread` — all sensor reads are off the main thread
- GPU metrics use **pynvml** (direct NVML calls, <1ms each) instead of `subprocess nvidia-smi` (150–400ms, causes thermal observer-effect spikes)
- CPU temp and usage are stabilised with a **5-sample rolling average** over real hardware readings

## License

MIT
