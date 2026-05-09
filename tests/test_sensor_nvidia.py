import pytest
from types import SimpleNamespace
from thermalcanary.nvidia import NvidiaGpuReader


def test_stats_returns_nvml_values(mocker):
    mem = SimpleNamespace(used=2 * 1024 ** 3, total=8 * 1024 ** 3)
    nvml = mocker.MagicMock()
    nvml.NVMLError = Exception
    nvml.nvmlDeviceGetHandleByIndex.return_value = object()
    nvml.nvmlDeviceGetTemperature.return_value = 72
    nvml.nvmlDeviceGetFanSpeed.return_value = 55
    nvml.nvmlDeviceGetMemoryInfo.return_value = mem
    nvml.NVML_TEMPERATURE_GPU = 0
    mocker.patch('thermalcanary.nvidia.pynvml', nvml)

    r = NvidiaGpuReader(0)
    t, f, v = r.stats()
    assert t == 72.0
    assert f == 55.0
    assert pytest.approx(v, abs=0.1) == 25.0


def test_stats_returns_zero_on_nvml_error(mocker):
    nvml = mocker.MagicMock()
    nvml.NVMLError = RuntimeError
    nvml.nvmlDeviceGetHandleByIndex.return_value = object()
    nvml.nvmlDeviceGetTemperature.side_effect = RuntimeError('driver gone')
    nvml.NVML_TEMPERATURE_GPU = 0
    mocker.patch('thermalcanary.nvidia.pynvml', nvml)

    r = NvidiaGpuReader(0)
    assert r.stats() == (0.0, 0.0, 0.0)


def test_shutdown_calls_nvml_shutdown(mocker):
    nvml = mocker.MagicMock()
    nvml.NVMLError = Exception
    nvml.nvmlDeviceGetHandleByIndex.return_value = object()
    mocker.patch('thermalcanary.nvidia.pynvml', nvml)

    r = NvidiaGpuReader(0)
    r.shutdown()
    nvml.nvmlShutdown.assert_called_once()


# ---------------------------------------------------------------------------
# New mutation-killing tests
# ---------------------------------------------------------------------------

def _make_nvml(mocker, *, used=1024**3, total=4*1024**3,
               temp=68, fan=42):
    from types import SimpleNamespace
    mem = SimpleNamespace(used=used, total=total)
    nvml = mocker.MagicMock()
    nvml.NVMLError = Exception
    nvml.nvmlDeviceGetHandleByIndex.return_value = object()
    nvml.nvmlDeviceGetTemperature.return_value = temp
    nvml.nvmlDeviceGetFanSpeed.return_value = fan
    nvml.nvmlDeviceGetMemoryInfo.return_value = mem
    nvml.NVML_TEMPERATURE_GPU = 0
    mocker.patch('thermalcanary.nvidia.pynvml', nvml)
    return nvml


def test_init_calls_nvml_init(mocker):
    """__init__ must call nvmlInit()."""
    nvml = _make_nvml(mocker)
    NvidiaGpuReader(0)
    nvml.nvmlInit.assert_called_once()


def test_init_calls_get_handle_by_index_zero(mocker):
    """__init__ with gpu_index=0 passes 0 to nvmlDeviceGetHandleByIndex."""
    nvml = _make_nvml(mocker)
    NvidiaGpuReader(0)
    nvml.nvmlDeviceGetHandleByIndex.assert_called_once_with(0)


def test_init_calls_get_handle_by_index_one(mocker):
    """__init__ with gpu_index=1 passes 1 to nvmlDeviceGetHandleByIndex."""
    nvml = _make_nvml(mocker)
    NvidiaGpuReader(1)
    nvml.nvmlDeviceGetHandleByIndex.assert_called_once_with(1)


def test_stats_returns_float_types(mocker):
    """stats() values are floats, not ints."""
    _make_nvml(mocker, temp=70, fan=55)
    r = NvidiaGpuReader(0)
    t, f, v = r.stats()
    assert isinstance(t, float)
    assert isinstance(f, float)
    assert isinstance(v, float)


def test_stats_vram_division(mocker):
    """stats() computes vram as used/total*100 (1GB used / 4GB total = 25.0)."""
    _make_nvml(mocker, used=1024**3, total=4*1024**3)
    r = NvidiaGpuReader(0)
    _, _, vram = r.stats()
    assert pytest.approx(vram, abs=0.001) == 25.0


def test_stats_vram_division_half(mocker):
    """stats() computes vram correctly for 2GB used / 4GB total = 50.0."""
    _make_nvml(mocker, used=2*1024**3, total=4*1024**3)
    r = NvidiaGpuReader(0)
    _, _, vram = r.stats()
    assert pytest.approx(vram, abs=0.001) == 50.0


def test_stats_nvml_error_from_get_temperature_returns_zeros(mocker):
    """NVMLError raised by GetTemperature → (0.0, 0.0, 0.0)."""
    nvml = _make_nvml(mocker)
    nvml.NVMLError = RuntimeError
    nvml.nvmlDeviceGetTemperature.side_effect = RuntimeError("gone")
    r = NvidiaGpuReader(0)
    assert r.stats() == (0.0, 0.0, 0.0)


def test_stats_nvml_error_from_get_fan_speed_returns_zeros(mocker):
    """NVMLError raised by GetFanSpeed → (0.0, 0.0, 0.0)."""
    nvml = _make_nvml(mocker)
    nvml.NVMLError = RuntimeError
    nvml.nvmlDeviceGetFanSpeed.side_effect = RuntimeError("no fan")
    r = NvidiaGpuReader(0)
    assert r.stats() == (0.0, 0.0, 0.0)


def test_stats_nvml_error_from_get_memory_info_returns_zeros(mocker):
    """NVMLError raised by GetMemoryInfo → (0.0, 0.0, 0.0)."""
    nvml = _make_nvml(mocker)
    nvml.NVMLError = RuntimeError
    nvml.nvmlDeviceGetMemoryInfo.side_effect = RuntimeError("no mem")
    r = NvidiaGpuReader(0)
    assert r.stats() == (0.0, 0.0, 0.0)
