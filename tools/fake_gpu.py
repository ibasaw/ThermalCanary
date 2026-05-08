#!/usr/bin/env python3
"""
Fake GPU sysfs tree for testing AMD/Intel readers without real hardware.

Usage:
    python tools/fake_gpu.py --backend amd    # or intel
    # in another terminal:
    THERMALCANARY_SYSFS_ROOT=/tmp/fake-gpu uv run python -m thermalcanary

Press Ctrl+C to stop.
"""
import argparse
import math
import os
import signal
import sys
import time
from pathlib import Path

ROOT = Path('/tmp/fake-gpu')


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(value))


def setup_amd(device: Path, hwmon: Path) -> None:
    _write(hwmon / 'name',           'amdgpu')
    _write(device / 'mem_info_vram_total', str(8 * 1024 ** 3))


def setup_intel(device: Path, hwmon: Path) -> None:
    _write(hwmon / 'name', 'xe')


def update_amd(device: Path, hwmon: Path, t: float, apu: bool = False) -> None:
    temp_c  = 58 + 12 * math.sin(t / 8)
    vram_b  = int((2 + math.sin(t / 20)) * 1024 ** 3)
    _write(hwmon / 'temp1_input',         int(temp_c * 1000))
    _write(device / 'mem_info_vram_used', vram_b)
    if apu:
        busy = int(30 + 25 * math.sin(t / 6))
        _write(device / 'gpu_busy_percent', busy)
    else:
        fan_rpm = int(1800 + 600 * math.sin(t / 12))
        _write(hwmon / 'fan1_input', fan_rpm)
        _write(hwmon / 'fan1_max',   3600)


def update_intel(device: Path, hwmon: Path, t: float) -> None:
    temp_c  = 52 + 8 * math.sin(t / 10)
    fan_rpm = int(1200 + 400 * math.sin(t / 15))
    _write(hwmon / 'temp1_input', int(temp_c * 1000))
    _write(hwmon / 'fan1_input',  fan_rpm)
    _write(hwmon / 'fan1_max',    2400)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--backend', choices=['amd', 'amd-apu', 'intel'], default='amd')
    args = ap.parse_args()

    device = ROOT / 'card0' / 'device'
    hwmon  = device / 'hwmon' / 'hwmon0'

    if args.backend in ('amd', 'amd-apu'):
        setup_amd(device, hwmon)
        apu = args.backend == 'amd-apu'
        update_fn = lambda d, h, t: update_amd(d, h, t, apu=apu)
    else:
        setup_intel(device, hwmon)
        update_fn = update_intel

    print(f'Fake {args.backend.upper()} GPU at {ROOT}')
    print(f'Run the app with: THERMALCANARY_SYSFS_ROOT={ROOT} uv run python -m thermalcanary')
    print('Ctrl+C to stop.')

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    t = 0.0
    try:
        while True:
            update_fn(device, hwmon, t)
            t += 1.0
            time.sleep(1.0)
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()
