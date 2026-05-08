import pytest
from types import SimpleNamespace
from PyQt6.QtCore import Qt, QMetaObject

try:
    from thermalcanary.app import ThermalCanary
    _HAS_APP = True
except ImportError:
    _HAS_APP = False

pytestmark = pytest.mark.skipif(not _HAS_APP, reason="thermalcanary.app not in mutmut sandbox")


@pytest.fixture(autouse=True)
def _no_tray(mocker, tmp_config):
    mocker.patch(
        "PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable",
        return_value=False,
    )
    tmp_config.set("tray_warning_shown", True)


@pytest.fixture(autouse=True)
def _mock_sensors(mocker):
    from collections import namedtuple
    STemp = namedtuple("shwtemp", ["label", "current", "high", "critical"])
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={"coretemp": [STemp("Package id 0", 62.0, 100.0, 105.0)]},
    )
    mocker.patch("thermalcanary.sensor.psutil.cpu_percent", return_value=30.0)
    mocker.patch(
        "thermalcanary.sensor.psutil.virtual_memory",
        return_value=SimpleNamespace(percent=50.0),
    )
    mem = SimpleNamespace(used=2 * 1024 ** 3, total=8 * 1024 ** 3)
    nvml = mocker.MagicMock()
    nvml.NVMLError = Exception
    nvml.nvmlDeviceGetHandleByIndex.return_value = object()
    nvml.nvmlDeviceGetTemperature.return_value = 68
    nvml.nvmlDeviceGetFanSpeed.return_value = 42
    nvml.nvmlDeviceGetMemoryInfo.return_value = mem
    nvml.NVML_TEMPERATURE_GPU = 0
    mocker.patch("thermalcanary.nvidia.pynvml", nvml)


def test_sensor_reading_flows_to_gauge_targets(tmp_config, qtbot):
    main = ThermalCanary(tmp_config)
    qtbot.addWidget(main)

    qtbot.waitSignal(main._worker.reading, timeout=2000)
    # _on_reading runs via QueuedConnection in main thread — poll until gauge updates
    qtbot.waitUntil(lambda: main.g_cpu_t._target > 0, timeout=2000)

    assert main.g_cpu_t._target == pytest.approx(62.0, abs=1.0)
    assert main.g_gpu_t._target == 68.0
    assert main.g_fan._target == 42.0

    QMetaObject.invokeMethod(
        main._worker, "stop",
        Qt.ConnectionType.BlockingQueuedConnection,
    )
    main._thread.quit()
    main._thread.wait(2000)
