"""Tests for thermalcanary._gpu_sysfs._SysfsGpuReader.

We exercise via AmdGpuReader (concrete subclass) because the base class has
empty _HWMON_NAMES and _SYSFS_ENV — the interesting mutations live in paths
that subclass values activate.
"""
import os
import stat
import pytest
from pathlib import Path
from thermalcanary.amd import AmdGpuReader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_device(tmp_path: Path, *, hwmon_name: str = 'amdgpu',
                 temp_millideg: int | None = None) -> Path:
    """Create a minimal sysfs card layout under tmp_path and return it."""
    device = tmp_path / 'card0' / 'device'
    hw = device / 'hwmon' / 'hwmon0'
    hw.mkdir(parents=True)
    (hw / 'name').write_text(hwmon_name)
    if temp_millideg is not None:
        (hw / 'temp1_input').write_text(str(temp_millideg))
    return tmp_path


# ---------------------------------------------------------------------------
# __init__ — root selection
# ---------------------------------------------------------------------------

def test_init_uses_sysfs_root_param(tmp_path):
    """sysfs_root parameter is used directly instead of /sys/class/drm."""
    _make_device(tmp_path)
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    assert str(r._device) == str(tmp_path / 'card0' / 'device')


def test_init_uses_env_var_when_test_flag_set(tmp_path, monkeypatch):
    """When THERMALCANARY_TEST is set, THERMALCANARY_SYSFS_ROOT is used as root."""
    _make_device(tmp_path)
    monkeypatch.setenv('THERMALCANARY_TEST', '1')
    monkeypatch.setenv('THERMALCANARY_SYSFS_ROOT', str(tmp_path))
    r = AmdGpuReader('card0', sysfs_root=None)
    assert str(r._device) == str(tmp_path / 'card0' / 'device')


def test_init_falls_back_to_sys_class_drm_without_test_flag(monkeypatch):
    """Without THERMALCANARY_TEST, root must default to /sys/class/drm."""
    monkeypatch.delenv('THERMALCANARY_TEST', raising=False)
    monkeypatch.setenv('THERMALCANARY_SYSFS_ROOT', '/should/be/ignored')
    r = AmdGpuReader('card0', sysfs_root=None)
    assert r._device == Path('/sys/class/drm') / 'card0' / 'device'


# ---------------------------------------------------------------------------
# _find_hwmon — hwmon selection
# ---------------------------------------------------------------------------

def test_find_hwmon_returns_none_when_hwmon_dir_missing(tmp_path):
    """No hwmon directory → _hwmon is None."""
    device = tmp_path / 'card0' / 'device'
    device.mkdir(parents=True)
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    assert r._hwmon is None


def test_find_hwmon_returns_named_match_over_first(tmp_path):
    """hwmon with name in _HWMON_NAMES is returned even if it is not alphabetically first."""
    device = tmp_path / 'card0' / 'device'
    hw0 = device / 'hwmon' / 'hwmon0'
    hw1 = device / 'hwmon' / 'hwmon1'
    hw0.mkdir(parents=True)
    hw1.mkdir(parents=True)
    (hw0 / 'name').write_text('k10temp')       # not in AmdGpuReader._HWMON_NAMES
    (hw0 / 'temp1_input').write_text('99000')
    (hw1 / 'name').write_text('amdgpu')        # in _HWMON_NAMES
    (hw1 / 'temp1_input').write_text('60000')
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    assert r._hwmon == hw1


def test_find_hwmon_returns_first_alphabetically_when_no_name_matches(tmp_path):
    """When no hwmon name matches _HWMON_NAMES, the first (sorted) hwmon is used."""
    device = tmp_path / 'card0' / 'device'
    hw0 = device / 'hwmon' / 'hwmon0'
    hw2 = device / 'hwmon' / 'hwmon2'
    hw0.mkdir(parents=True)
    hw2.mkdir(parents=True)
    (hw0 / 'name').write_text('unknown_chip')
    (hw0 / 'temp1_input').write_text('50000')
    (hw2 / 'name').write_text('also_unknown')
    (hw2 / 'temp1_input').write_text('75000')
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    assert r._hwmon == hw0


# ---------------------------------------------------------------------------
# temp()
# ---------------------------------------------------------------------------

def test_temp_divides_by_1000(tmp_path):
    """temp() must divide temp1_input by exactly 1000."""
    root = _make_device(tmp_path, temp_millideg=85000)
    r = AmdGpuReader('card0', sysfs_root=str(root))
    assert r.temp() == 85.0


def test_temp_returns_zero_when_hwmon_is_none(tmp_path):
    """temp() returns 0.0 when _hwmon is None (no hwmon directory)."""
    device = tmp_path / 'card0' / 'device'
    device.mkdir(parents=True)
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    assert r._hwmon is None
    assert r.temp() == 0.0


def test_temp_returns_zero_when_temp1_input_missing(tmp_path):
    """temp() returns 0.0 when temp1_input file is absent."""
    device = tmp_path / 'card0' / 'device'
    hw = device / 'hwmon' / 'hwmon0'
    hw.mkdir(parents=True)
    (hw / 'name').write_text('amdgpu')
    # temp1_input intentionally absent
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    assert r.temp() == 0.0


def test_temp_value_is_float(tmp_path):
    """temp() return type is float, not int."""
    root = _make_device(tmp_path, temp_millideg=70000)
    r = AmdGpuReader('card0', sysfs_root=str(root))
    assert isinstance(r.temp(), float)


# ---------------------------------------------------------------------------
# Boundary / precision
# ---------------------------------------------------------------------------

def test_temp_millideg_precision(tmp_path):
    """temp() converts millidegrees with correct decimal: 1500 → 1.5."""
    root = _make_device(tmp_path, temp_millideg=1500)
    r = AmdGpuReader('card0', sysfs_root=str(root))
    assert pytest.approx(r.temp(), abs=0.001) == 1.5
