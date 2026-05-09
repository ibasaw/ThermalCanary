import pytest
from pathlib import Path
from thermalcanary.amd import AmdGpuReader


def _make_card(tmp_path, *, hwmon_name='amdgpu', temp=None, fan=None,
               fan_max=None, vram_used=None, vram_total=None) -> Path:
    device = tmp_path / 'card0' / 'device'
    device.mkdir(parents=True)
    hw = device / 'hwmon' / 'hwmon3'
    hw.mkdir(parents=True)
    (hw / 'name').write_text(hwmon_name)
    if temp     is not None: (hw / 'temp1_input').write_text(str(temp))
    if fan      is not None: (hw / 'fan1_input').write_text(str(fan))
    if fan_max  is not None: (hw / 'fan1_max').write_text(str(fan_max))
    if vram_used  is not None: (device / 'mem_info_vram_used').write_text(str(vram_used))
    if vram_total is not None: (device / 'mem_info_vram_total').write_text(str(vram_total))
    return tmp_path


def test_reads_temp_fan_vram(tmp_path):
    root = _make_card(tmp_path, temp=65000, fan=1500, fan_max=3000,
                      vram_used=2 * 1024 ** 3, vram_total=8 * 1024 ** 3)
    r = AmdGpuReader('card0', sysfs_root=str(root))
    t, f, v = r.stats()
    assert t == 65.0
    assert f == 50.0
    assert pytest.approx(v, abs=0.1) == 25.0


def test_missing_fan_max_returns_zero(tmp_path):
    root = _make_card(tmp_path, temp=70000, fan=2000)
    r = AmdGpuReader('card0', sysfs_root=str(root))
    _, f, _ = r.stats()
    assert f == 0.0


def test_missing_hwmon_returns_zero_temp_fan(tmp_path):
    device = tmp_path / 'card0' / 'device'
    device.mkdir(parents=True)
    (device / 'mem_info_vram_used').write_text('1073741824')
    (device / 'mem_info_vram_total').write_text('4294967296')
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    t, f, v = r.stats()
    assert t == 0.0
    assert f == 0.0
    assert pytest.approx(v, abs=0.1) == 25.0


def test_missing_card_directory_all_zero(tmp_path):
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    assert r.stats() == (0.0, 0.0, 0.0)


def test_picks_amdgpu_hwmon_over_other(tmp_path):
    device = tmp_path / 'card0' / 'device'
    hw0 = device / 'hwmon' / 'hwmon0'
    hw1 = device / 'hwmon' / 'hwmon1'
    hw0.mkdir(parents=True)
    hw1.mkdir(parents=True)
    (hw0 / 'name').write_text('k10temp')
    (hw0 / 'temp1_input').write_text('99000')
    (hw1 / 'name').write_text('amdgpu')
    (hw1 / 'temp1_input').write_text('40000')
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    assert r.temp() == 40.0


def test_fan_clamped_to_100(tmp_path):
    root = _make_card(tmp_path, fan=4000, fan_max=3000)
    r = AmdGpuReader('card0', sysfs_root=str(root))
    assert r.fan_percent() == 100.0


def test_shutdown_is_noop(tmp_path):
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    r.shutdown()  # must not raise


def test_gpu_busy_used_when_no_fan(tmp_path):
    root = _make_card(tmp_path, temp=55000, vram_used=1024**3, vram_total=4*1024**3)
    (tmp_path / 'card0' / 'device' / 'gpu_busy_percent').write_text('42')
    r = AmdGpuReader('card0', sysfs_root=str(root))
    assert not r.has_fan
    _, f, _ = r.stats()
    assert f == 42.0


def test_has_fan_true_when_fan_max_present(tmp_path):
    root = _make_card(tmp_path, fan=1500, fan_max=3000)
    r = AmdGpuReader('card0', sysfs_root=str(root))
    assert r.has_fan
    _, f, _ = r.stats()
    assert f == 50.0  # fan_percent used, not gpu_busy


# ---------------------------------------------------------------------------
# New mutation-killing tests
# ---------------------------------------------------------------------------

def test_vram_percent_zero_when_total_is_zero(tmp_path):
    """vram_percent() returns 0.0 when total is 0 (guard against ZeroDivisionError)."""
    _make_card(tmp_path, vram_used=1024**3, vram_total=0)
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    assert r.vram_percent() == 0.0


def test_vram_percent_zero_when_used_missing(tmp_path):
    """vram_percent() returns 0.0 when used file is absent."""
    device = tmp_path / 'card0' / 'device'
    device.mkdir(parents=True)
    (device / 'mem_info_vram_total').write_text('4294967296')
    # mem_info_vram_used intentionally absent
    r = AmdGpuReader('card0', sysfs_root=str(tmp_path))
    assert r.vram_percent() == 0.0


def test_vram_percent_correct_calculation(tmp_path):
    """vram_percent() = used/total*100 (512 MB / 4096 MB = 12.5)."""
    root = _make_card(tmp_path, vram_used=512 * 1024**2, vram_total=4096 * 1024**2)
    r = AmdGpuReader('card0', sysfs_root=str(root))
    assert pytest.approx(r.vram_percent(), abs=0.001) == 12.5


def test_vram_percent_full(tmp_path):
    """vram_percent() = 100.0 when used == total."""
    root = _make_card(tmp_path, vram_used=4 * 1024**3, vram_total=4 * 1024**3)
    r = AmdGpuReader('card0', sysfs_root=str(root))
    assert pytest.approx(r.vram_percent(), abs=0.001) == 100.0
