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
