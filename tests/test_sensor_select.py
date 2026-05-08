from collections import namedtuple

from thermalcanary.sensor_select import detect_available_sensors, SensorSelectWidget

STemp = namedtuple("shwtemp", ["label", "current", "high", "critical"])


def test_filters_hidden_chips(mocker):
    mocker.patch(
        "thermalcanary.sensor_select.psutil.sensors_temperatures",
        return_value={
            "nvme":     [STemp("Composite", 38.0, 75.0, 80.0)],
            "coretemp": [STemp("Package id 0", 62.0, 100.0, 105.0)],
            "pch_cometlake": [STemp("", 45.0, 75.0, 80.0)],
        },
    )
    sources = detect_available_sensors()
    keys = [k for _, k in sources["cpu_temp"]]
    assert any("coretemp" in k for k in keys)
    assert not any("nvme" in k for k in keys)
    assert not any("pch" in k for k in keys)


def test_always_includes_auto(mocker):
    mocker.patch(
        "thermalcanary.sensor_select.psutil.sensors_temperatures",
        return_value={},
    )
    sources = detect_available_sensors()
    assert sources["cpu_temp"][0] == ("auto", "auto")


def test_combo_reflects_saved_source(tmp_config, mocker, qtbot):
    tmp_config.set("cpu_temp_source", "coretemp/Core 0")
    mocker.patch(
        "thermalcanary.sensor_select.psutil.sensors_temperatures",
        return_value={"coretemp": [STemp("Core 0", 55.0, 100.0, 105.0)]},
    )
    widget = SensorSelectWidget(tmp_config)
    qtbot.addWidget(widget)
    cb = widget._combos["cpu_temp"]
    assert cb.currentData() == "coretemp/Core 0"
