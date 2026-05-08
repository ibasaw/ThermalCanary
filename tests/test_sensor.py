import pytest
from collections import namedtuple
from types import SimpleNamespace

from thermalcanary.sensor import SensorWorker

STemp = namedtuple("shwtemp", ["label", "current", "high", "critical"])


def test_cpu_temp_auto_prefers_package_id(tmp_config, mock_psutil_temps):
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 62.0


def test_cpu_temp_auto_fallback_k10temp(tmp_config, mocker):
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={"k10temp": [STemp("Tctl", 55.5, 100.0, 105.0)]},
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 55.5


def test_cpu_temp_explicit_chip_label(tmp_config, mocker):
    tmp_config.set("cpu_temp_source", "coretemp/Core 0")
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={"coretemp": [
            STemp("Package id 0", 62.0, 100.0, 105.0),
            STemp("Core 0",       51.0, 100.0, 105.0),
        ]},
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 51.0


def test_cpu_temp_explicit_chip_only(tmp_config, mocker):
    tmp_config.set("cpu_temp_source", "coretemp")
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={"coretemp": [STemp("", 48.0, 100.0, 105.0)]},
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 48.0


def test_cpu_temp_exception_returns_zero(tmp_config, mocker):
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        side_effect=OSError("no sensors"),
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 0.0


def test_gpu_stats_returns_nvml_values(tmp_config, mock_pynvml):
    worker = SensorWorker(tmp_config)
    worker.start()
    temp, fan, vram = worker._gpu_stats()
    assert temp == 68.0
    assert fan == 42.0
    assert pytest.approx(vram, abs=0.1) == 25.0


def test_poll_emits_reading_signal(tmp_config, mock_psutil_temps, mock_pynvml, mocker, qtbot):
    mocker.patch("thermalcanary.sensor.psutil.cpu_percent", return_value=45.0)
    mocker.patch(
        "thermalcanary.sensor.psutil.virtual_memory",
        return_value=SimpleNamespace(percent=60.0),
    )
    worker = SensorWorker(tmp_config)
    worker.start()

    with qtbot.waitSignal(worker.reading, timeout=500) as blocker:
        worker._poll()

    cpu_t, gpu_t, gpu_f, cpu_u, mem, gpu_vram = blocker.args
    assert pytest.approx(cpu_t, abs=1.0) == 62.0
    assert gpu_t == 68.0
    assert gpu_f == 42.0
    assert cpu_u == 45.0
    assert mem == 60.0
    assert pytest.approx(gpu_vram, abs=0.1) == 25.0
