import pytest
from collections import namedtuple
from types import SimpleNamespace

from thermalcanary.config import Config

STemp = namedtuple("shwtemp", ["label", "current", "high", "critical"])


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return Config()


@pytest.fixture
def mock_psutil_temps(mocker):
    data = {
        "coretemp": [
            STemp("Package id 0", 62.0, 100.0, 105.0),
            STemp("Core 0",       55.0, 100.0, 105.0),
        ]
    }
    return mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value=data,
    )


@pytest.fixture
def mock_pynvml(mocker):
    mem = SimpleNamespace(used=2 * 1024 ** 3, total=8 * 1024 ** 3)
    nvml = mocker.MagicMock()
    nvml.NVMLError = Exception
    nvml.nvmlDeviceGetHandleByIndex.return_value = object()
    nvml.nvmlDeviceGetTemperature.return_value = 68
    nvml.nvmlDeviceGetFanSpeed.return_value = 42
    nvml.nvmlDeviceGetMemoryInfo.return_value = mem
    nvml.NVML_TEMPERATURE_GPU = 0
    mocker.patch("thermalcanary.sensor.pynvml", nvml)
    return nvml


@pytest.fixture
def make_qscreen(mocker):
    from PyQt6.QtCore import QSizeF

    def _make(name="DP-1", mfg="", model="", serial="", w=527.0, h=296.0):
        s = mocker.MagicMock()
        s.name.return_value = name
        s.manufacturer.return_value = mfg
        s.model.return_value = model
        s.serialNumber.return_value = serial
        s.physicalSize.return_value = QSizeF(w, h)
        return s

    return _make
