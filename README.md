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

The installer creates a Python venv at `~/.local/share/sysgauge/venv/`, installs dependencies, and registers an autostart entry so the app launches automatically on login.

## Launch manually

```bash
~/.local/share/sysgauge/venv/bin/python3 monitor.py
```

## Configuration

Edit the constants at the top of `monitor.py`:

```python
SCREEN_INDEX = 2       # which monitor (0-based)
POLL_MS      = 1000    # sensor poll interval in ms
SMOOTH_N     = 5       # rolling average window (samples)
BG_COLOR     = '#252040'  # background colour
```

## Architecture

- **SensorWorker** runs in a `QThread` — all sensor reads are off the main thread
- GPU metrics use **pynvml** (direct NVML calls, <1ms each) instead of `subprocess nvidia-smi` (150–400ms, causes thermal observer-effect spikes)
- CPU temp and usage are stabilised with a **5-sample rolling average** over real hardware readings

## License

MIT
