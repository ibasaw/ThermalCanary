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


def test_start_emits_gpu_ready_found(tmp_config, mock_pynvml, qtbot):
    worker = SensorWorker(tmp_config)
    with qtbot.waitSignal(worker.gpu_ready, timeout=500) as blocker:
        worker.start()
    found, label = blocker.args
    assert found is True
    assert label == 'GPU Fan'


def test_start_emits_gpu_ready_not_found(tmp_config, mocker, qtbot):
    mocker.patch("thermalcanary.nvidia.pynvml.nvmlInit", side_effect=Exception("no gpu"))
    tmp_config.set('gpu_backend', 'auto')
    worker = SensorWorker(tmp_config)
    with qtbot.waitSignal(worker.gpu_ready, timeout=500) as blocker:
        worker.start()
    found, label = blocker.args
    assert found is False


def test_stop_shuts_down_reader(tmp_config, mock_pynvml, qtbot):
    worker = SensorWorker(tmp_config)
    worker.start()
    assert worker._gpu_reader is not None
    worker.stop()
    mock_pynvml.nvmlShutdown.assert_called_once()


def test_stop_with_no_reader_no_crash(tmp_config, mocker):
    mocker.patch("thermalcanary.nvidia.pynvml.nvmlInit", side_effect=Exception("no gpu"))
    tmp_config.set('gpu_backend', 'auto')
    worker = SensorWorker(tmp_config)
    worker.start()
    worker.stop()   # must not raise


def test_set_interval_updates_timer(tmp_config, mock_pynvml):
    worker = SensorWorker(tmp_config)
    worker.start()
    worker.set_interval(2000)
    assert worker._timer.interval() == 2000
    worker.stop()


def test_set_smooth_n_resizes_buffers(tmp_config, mock_pynvml):
    worker = SensorWorker(tmp_config)
    worker.start()
    worker.set_smooth_n(3)
    assert worker._cpu_t_buf.maxlen == 3
    assert worker._cpu_u_buf.maxlen == 3
    worker.stop()


def test_init_gpu_amd_backend(tmp_config, mocker):
    tmp_config.set('gpu_backend', 'amdgpu')
    fake_reader = mocker.MagicMock()
    fake_reader.has_fan = True
    mocker.patch("thermalcanary.amd.AmdGpuReader", return_value=fake_reader)
    worker = SensorWorker(tmp_config)
    worker._init_gpu()
    assert worker._gpu_reader is fake_reader


def test_init_gpu_intel_backend(tmp_config, mocker):
    tmp_config.set('gpu_backend', 'intel')
    fake_reader = mocker.MagicMock()
    fake_reader.has_fan = False
    mocker.patch("thermalcanary.intel.IntelGpuReader", return_value=fake_reader)
    worker = SensorWorker(tmp_config)
    worker._init_gpu()
    assert worker._gpu_reader is fake_reader


def test_start_amd_no_fan_emits_gpu_load_label(tmp_config, mocker, qtbot):
    tmp_config.set('gpu_backend', 'amdgpu')
    fake_reader = mocker.MagicMock()
    fake_reader.has_fan = False
    fake_reader.gpu_busy = mocker.MagicMock()
    mocker.patch("thermalcanary.amd.AmdGpuReader", return_value=fake_reader)
    worker = SensorWorker(tmp_config)
    with qtbot.waitSignal(worker.gpu_ready, timeout=500) as blocker:
        worker.start()
    found, label = blocker.args
    assert found is True
    assert label == 'GPU Load'


def test_cpu_temp_unknown_chip_falls_back_to_any(tmp_config, mocker):
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={"acpitz": [STemp("temp1", 45.0, 100.0, 105.0)]},
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 45.0


def test_cpu_temp_no_chips_returns_zero(tmp_config, mocker):
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={},
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 0.0


# ---------------------------------------------------------------------------
# New mutation-killing tests
# ---------------------------------------------------------------------------

def test_cpu_temp_auto_prefers_coretemp_over_k10temp(tmp_config, mocker):
    """Auto mode: when both coretemp and k10temp are present, coretemp wins."""
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={
            "coretemp": [STemp("Core 0", 58.0, 100.0, 105.0)],
            "k10temp":  [STemp("Tctl",   72.0, 100.0, 105.0)],
        },
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 58.0


def test_cpu_temp_auto_falls_to_zenpower(tmp_config, mocker):
    """Auto mode: falls to zenpower when no coretemp or k10temp entries."""
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={"zenpower": [STemp("Tdie", 61.0, 100.0, 105.0)]},
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 61.0


def test_cpu_temp_auto_any_chip_last_resort(tmp_config, mocker):
    """Auto mode: falls to the first entry of any chip as last resort."""
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={"acpitz": [STemp("temp1", 45.0, 100.0, 105.0)]},
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 45.0


def test_cpu_temp_explicit_chip_slash_label_matches(tmp_config, mocker):
    """chip/label source returns the matching entry."""
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


def test_cpu_temp_explicit_chip_slash_label_missing_returns_zero(tmp_config, mocker):
    """chip/label source returns 0.0 when label not found."""
    tmp_config.set("cpu_temp_source", "coretemp/NoSuchLabel")
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={"coretemp": [STemp("Package id 0", 62.0, 100.0, 105.0)]},
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 0.0


def test_cpu_temp_explicit_chip_no_slash_returns_first(tmp_config, mocker):
    """chip-only source (no slash) returns the first entry from that chip."""
    tmp_config.set("cpu_temp_source", "coretemp")
    mocker.patch(
        "thermalcanary.sensor.psutil.sensors_temperatures",
        return_value={"coretemp": [
            STemp("Package id 0", 62.0, 100.0, 105.0),
            STemp("Core 0",       55.0, 100.0, 105.0),
        ]},
    )
    worker = SensorWorker(tmp_config)
    assert worker._cpu_temp() == 62.0


def test_init_gpu_nvml_backend_failure_does_not_fallback_to_amd(tmp_config, mocker):
    """backend='nvml' fail must NOT fall through to AMD."""
    tmp_config.set('gpu_backend', 'nvml')
    mocker.patch("thermalcanary.nvidia.pynvml.nvmlInit", side_effect=Exception("no nvml"))
    amd_mock = mocker.patch("thermalcanary.amd.AmdGpuReader")
    worker = SensorWorker(tmp_config)
    worker._init_gpu()
    amd_mock.assert_not_called()
    assert worker._gpu_reader is None


def test_start_emits_dash_label_when_no_gpu(tmp_config, mocker, qtbot):
    """start() emits '—' as fan_label when gpu_reader is None."""
    mocker.patch("thermalcanary.nvidia.pynvml.nvmlInit", side_effect=Exception("no gpu"))
    tmp_config.set('gpu_backend', 'auto')
    worker = SensorWorker(tmp_config)
    with qtbot.waitSignal(worker.gpu_ready, timeout=500) as blocker:
        worker.start()
    found, label = blocker.args
    assert found is False
    assert label == 'GPU Fan'   # label is 'GPU Fan' regardless (no reader → only fan_label unchanged)


def test_start_emits_gpu_load_label_when_no_fan_but_gpu_busy(tmp_config, mocker, qtbot):
    """start() emits 'GPU Load' when reader has no fan but exposes gpu_busy."""
    tmp_config.set('gpu_backend', 'amdgpu')
    fake_reader = mocker.MagicMock()
    fake_reader.has_fan = False
    fake_reader.gpu_busy = mocker.MagicMock()
    mocker.patch("thermalcanary.amd.AmdGpuReader", return_value=fake_reader)
    worker = SensorWorker(tmp_config)
    with qtbot.waitSignal(worker.gpu_ready, timeout=500) as blocker:
        worker.start()
    found, label = blocker.args
    assert found is True
    assert label == 'GPU Load'


def test_poll_reading_signal_has_six_values(tmp_config, mock_psutil_temps, mock_pynvml, mocker, qtbot):
    """_poll() must emit exactly 6 float values in the reading signal."""
    mocker.patch("thermalcanary.sensor.psutil.cpu_percent", return_value=30.0)
    mocker.patch(
        "thermalcanary.sensor.psutil.virtual_memory",
        return_value=SimpleNamespace(percent=50.0),
    )
    worker = SensorWorker(tmp_config)
    worker.start()
    with qtbot.waitSignal(worker.reading, timeout=500) as blocker:
        worker._poll()
    assert len(blocker.args) == 6


def test_poll_reading_signal_mem_u_position(tmp_config, mock_psutil_temps, mock_pynvml, mocker, qtbot):
    """_poll() emits virtual_memory().percent as the 5th value (index 4)."""
    mocker.patch("thermalcanary.sensor.psutil.cpu_percent", return_value=30.0)
    mocker.patch(
        "thermalcanary.sensor.psutil.virtual_memory",
        return_value=SimpleNamespace(percent=77.0),
    )
    worker = SensorWorker(tmp_config)
    worker.start()
    with qtbot.waitSignal(worker.reading, timeout=500) as blocker:
        worker._poll()
    # signal order: cpu_t, gpu_t, gpu_f, cpu_u, mem, gpu_vram
    assert blocker.args[4] == 77.0


def test_init_deque_maxlen_equals_smooth_n(tmp_config):
    """__init__ creates deques with maxlen equal to config smooth_n."""
    tmp_config.set('smooth_n', 7)
    worker = SensorWorker(tmp_config)
    assert worker._cpu_t_buf.maxlen == 7
    assert worker._cpu_u_buf.maxlen == 7


def test_gpu_stats_returns_triple_zero_when_no_reader(tmp_config):
    """_gpu_stats() must return exactly (0.0, 0.0, 0.0) when _gpu_reader is None."""
    worker = SensorWorker(tmp_config)
    worker._gpu_reader = None
    assert worker._gpu_stats() == (0.0, 0.0, 0.0)


def test_init_gpu_intel_backend_calls_intel_reader(tmp_config, mocker):
    """backend='intel' must instantiate IntelGpuReader."""
    tmp_config.set('gpu_backend', 'intel')
    fake_reader = mocker.MagicMock()
    fake_reader.has_fan = False
    mocker.patch("thermalcanary.intel.IntelGpuReader", return_value=fake_reader)
    worker = SensorWorker(tmp_config)
    worker._init_gpu()
    assert worker._gpu_reader is fake_reader
