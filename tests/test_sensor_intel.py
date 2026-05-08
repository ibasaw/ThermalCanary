import pytest
from pathlib import Path
from thermalcanary.intel import IntelGpuReader


def _make_intel_card(tmp_path, *, hwmon_name='xe', temp=None,
                     fan=None, fan_max=None) -> Path:
    device = tmp_path / 'card0' / 'device'
    hw = device / 'hwmon' / 'hwmon2'
    hw.mkdir(parents=True)
    (hw / 'name').write_text(hwmon_name)
    if temp    is not None: (hw / 'temp1_input').write_text(str(temp))
    if fan     is not None: (hw / 'fan1_input').write_text(str(fan))
    if fan_max is not None: (hw / 'fan1_max').write_text(str(fan_max))
    return tmp_path


def test_reads_temp_and_fan_xe(tmp_path):
    root = _make_intel_card(tmp_path, hwmon_name='xe', temp=55000,
                            fan=1200, fan_max=2400)
    r = IntelGpuReader('card0', sysfs_root=str(root))
    t, f, v = r.stats()
    assert t == 55.0
    assert f == 50.0
    assert v == 0.0  # Intel VRAM always 0.0


def test_reads_temp_i915(tmp_path):
    root = _make_intel_card(tmp_path, hwmon_name='i915', temp=48000)
    r = IntelGpuReader('card0', sysfs_root=str(root))
    assert r.temp() == 48.0


def test_missing_fan_max_returns_zero(tmp_path):
    root = _make_intel_card(tmp_path, temp=60000, fan=1000)
    r = IntelGpuReader('card0', sysfs_root=str(root))
    assert r.fan_percent() == 0.0


def test_missing_card_directory_all_zero(tmp_path):
    r = IntelGpuReader('card0', sysfs_root=str(tmp_path))
    assert r.stats() == (0.0, 0.0, 0.0)


def test_vram_always_zero(tmp_path):
    root = _make_intel_card(tmp_path, hwmon_name='xe', temp=50000)
    r = IntelGpuReader('card0', sysfs_root=str(root))
    assert r.vram_percent() == 0.0
