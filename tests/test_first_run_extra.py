"""Extra coverage for first_run._detect_gpus — NVML and sysfs paths."""
import pytest

try:
    from thermalcanary.first_run import _detect_gpus
    _HAS = True
except ImportError:
    _HAS = False

pytestmark = pytest.mark.skipif(not _HAS, reason="first_run unavailable")


def test_detect_gpus_nvidia_path(mocker):
    """NVML is available and returns one GPU — covers lines 14-19."""
    import types
    nvml = types.SimpleNamespace(
        nvmlInit=lambda: None,
        nvmlDeviceGetCount=lambda: 1,
        nvmlDeviceGetHandleByIndex=lambda i: f'handle{i}',
        nvmlDeviceGetName=lambda h: 'NVIDIA RTX 4070',
    )
    mocker.patch('thermalcanary.first_run.glob.glob', return_value=[])
    mocker.patch.dict('sys.modules', {'pynvml': nvml})

    result = _detect_gpus()

    assert any(g['backend'] == 'nvml' for g in result)
    assert result[0]['name'] == 'NVIDIA RTX 4070'


def test_detect_gpus_nvidia_multiple(mocker):
    """Multiple NVML GPUs all get indexed."""
    import types
    names = ['NVIDIA RTX 4070', 'NVIDIA GTX 1060']
    nvml = types.SimpleNamespace(
        nvmlInit=lambda: None,
        nvmlDeviceGetCount=lambda: 2,
        nvmlDeviceGetHandleByIndex=lambda i: i,
        nvmlDeviceGetName=lambda h: names[h],
    )
    mocker.patch('thermalcanary.first_run.glob.glob', return_value=[])
    mocker.patch.dict('sys.modules', {'pynvml': nvml})

    result = _detect_gpus()

    assert len(result) == 2
    assert result[0]['index'] == 0
    assert result[1]['index'] == 1


def test_detect_gpus_amd_sysfs(mocker, tmp_path):
    """amdgpu hwmon name triggers AMD GPU detection — covers sysfs loop lines."""
    name_file = tmp_path / 'name'
    name_file.write_text('amdgpu\n')

    mocker.patch(
        'thermalcanary.first_run.glob.glob',
        return_value=[str(name_file)],
    )
    mocker.patch('pynvml.nvmlInit', side_effect=Exception('no nvml'))

    # Patch open() so card = path.split('/')[4] → need a path with card0 at index 4
    fake_path = '/sys/class/drm/card0/device/hwmon/hwmon0/name'
    mocker.patch(
        'thermalcanary.first_run.glob.glob',
        return_value=[fake_path],
    )
    mocker.patch('builtins.open', mocker.mock_open(read_data='amdgpu\n'))

    result = _detect_gpus()

    assert any(g['backend'] == 'amdgpu' for g in result)


def test_detect_gpus_intel_sysfs(mocker):
    """xe hwmon name triggers Intel GPU detection."""
    fake_path = '/sys/class/drm/card0/device/hwmon/hwmon0/name'
    mocker.patch('thermalcanary.first_run.glob.glob', return_value=[fake_path])
    mocker.patch('pynvml.nvmlInit', side_effect=Exception('no nvml'))
    mocker.patch('builtins.open', mocker.mock_open(read_data='xe\n'))

    result = _detect_gpus()

    assert any(g['backend'] == 'intel' for g in result)


def test_detect_gpus_unknown_hwmon_skipped(mocker):
    """Unknown hwmon names (e.g. 'k10temp') are ignored."""
    fake_path = '/sys/class/drm/card0/device/hwmon/hwmon0/name'
    mocker.patch('thermalcanary.first_run.glob.glob', return_value=[fake_path])
    mocker.patch('pynvml.nvmlInit', side_effect=Exception('no nvml'))
    mocker.patch('builtins.open', mocker.mock_open(read_data='k10temp\n'))

    result = _detect_gpus()

    assert result == []


def test_detect_gpus_duplicate_card_skipped(mocker):
    """Two hwmon entries for the same card only produce one GPU entry."""
    paths = [
        '/sys/class/drm/card0/device/hwmon/hwmon0/name',
        '/sys/class/drm/card0/device/hwmon/hwmon1/name',
    ]
    mocker.patch('thermalcanary.first_run.glob.glob', return_value=paths)
    mocker.patch('pynvml.nvmlInit', side_effect=Exception('no nvml'))
    mocker.patch('builtins.open', mocker.mock_open(read_data='amdgpu\n'))

    result = _detect_gpus()

    amd = [g for g in result if g['backend'] == 'amdgpu']
    assert len(amd) == 1


def test_detect_gpus_oserror_skipped(mocker):
    """OSError while reading a hwmon name file is silently skipped."""
    fake_path = '/sys/class/drm/card0/device/hwmon/hwmon0/name'
    mocker.patch('thermalcanary.first_run.glob.glob', return_value=[fake_path])
    mocker.patch('pynvml.nvmlInit', side_effect=Exception('no nvml'))
    mocker.patch('builtins.open', side_effect=OSError('permission denied'))

    result = _detect_gpus()

    assert result == []
