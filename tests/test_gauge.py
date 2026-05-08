import pytest
from PyQt6.QtGui import QColor

from thermalcanary.gauge import Gauge


def _gauge(tmp_config, warn=None, crit=None):
    return Gauge("Test", "°C", 0, 100, "#ff4060", tmp_config, warn=warn, crit=crit)


def test_set_value_clamps_to_hi(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g.set_value(150)
    assert g._target == 100.0


def test_set_value_clamps_to_lo(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g.set_value(-10)
    assert g._target == 0.0


def test_color_for_zero_is_blue(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    color = g._color_for(0.0)
    assert color.name() == QColor("#00aaff").name()


def test_color_for_midpoint_interpolates(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    blue = QColor("#00aaff")
    green = QColor("#39ff14")
    mid = g._color_for(0.125)
    assert mid.name() != blue.name()
    assert mid.name() != green.name()


def test_build_stops_warn_crit_ratios(tmp_config, qtbot):
    g = _gauge(tmp_config, warn=60, crit=80)
    qtbot.addWidget(g)
    stops = g._gradient_stops
    assert len(stops) == 5
    assert pytest.approx(stops[2][0]) == 0.6   # warn ratio
    assert pytest.approx(stops[4][0]) == 0.8   # crit ratio
    assert pytest.approx(stops[3][0]) == 0.7   # mid ratio
