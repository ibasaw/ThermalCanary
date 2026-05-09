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
        return_value={"coretemp": [STemp("Core 0", 55.0, 100.0, 95.0)]},
    )
    widget = SensorSelectWidget(tmp_config)
    qtbot.addWidget(widget)
    cb = widget._combos["cpu_temp"]
    assert cb.currentData() == "coretemp/Core 0"


# ---------------------------------------------------------------------------
# Mutation-killing: detect_available_sensors and SensorSelectWidget
# ---------------------------------------------------------------------------

def test_duplicate_sensor_key_not_added_twice(mocker):
    # Same chip/label pair from two entries → only one appears (continue, not break)
    mocker.patch(
        "thermalcanary.sensor_select.psutil.sensors_temperatures",
        return_value={
            "coretemp": [
                STemp("Core 0", 50.0, 100.0, 105.0),
                STemp("Core 0", 51.0, 100.0, 105.0),  # duplicate key
                STemp("Core 1", 52.0, 100.0, 105.0),  # distinct
            ],
        },
    )
    sources = detect_available_sensors()
    keys = [k for _, k in sources["cpu_temp"]]
    assert keys.count("coretemp/Core 0") == 1
    # Core 1 must still be included (continue not break)
    assert any("Core 1" in k for k in keys)


def test_label_format_uses_chip_slash_label(mocker):
    mocker.patch(
        "thermalcanary.sensor_select.psutil.sensors_temperatures",
        return_value={"coretemp": [STemp("Core 0", 55.0, 100.0, 105.0)]},
    )
    sources = detect_available_sensors()
    labels = [lbl for lbl, _ in sources["cpu_temp"]]
    assert "coretemp/Core 0" in labels


def test_label_without_entry_uses_chip_name(mocker):
    # chip with empty label → label in result is just the chip name (not None)
    mocker.patch(
        "thermalcanary.sensor_select.psutil.sensors_temperatures",
        return_value={"coretemp": [STemp("", 40.0, 75.0, 80.0)]},
    )
    sources = detect_available_sensors()
    labels = [lbl for lbl, _ in sources["cpu_temp"]]
    assert "coretemp" in labels


def test_label_is_string_not_none(mocker):
    # Mutation: label = None instead of f'{chip}/{e.label}'
    mocker.patch(
        "thermalcanary.sensor_select.psutil.sensors_temperatures",
        return_value={"coretemp": [STemp("Core 0", 55.0, 100.0, 105.0)]},
    )
    sources = detect_available_sensors()
    for lbl, _ in sources["cpu_temp"]:
        assert lbl is not None


def test_sensor_select_widget_layout_margins(tmp_config, mocker, qtbot):
    mocker.patch(
        "thermalcanary.sensor_select.psutil.sensors_temperatures",
        return_value={},
    )
    widget = SensorSelectWidget(tmp_config)
    qtbot.addWidget(widget)
    m = widget.layout().contentsMargins()
    assert m.left() == 0
    assert m.top() == 8
    assert m.right() == 0
    assert m.bottom() == 0


def test_sensor_select_widget_layout_spacing(tmp_config, mocker, qtbot):
    mocker.patch(
        "thermalcanary.sensor_select.psutil.sensors_temperatures",
        return_value={},
    )
    widget = SensorSelectWidget(tmp_config)
    qtbot.addWidget(widget)
    assert widget.layout().spacing() == 6
