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


def test_set_unavailable_blocks_set_value(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g.set_value(50)
    assert g._target == 50.0
    g.set_unavailable(True)
    g.set_value(80)
    assert g._target == 50.0  # blocked


def test_set_label_updates_title(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g.set_label('GPU Load')
    assert g.title == 'GPU Load'


def test_step_advances_cur_toward_target(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g._cur = 0.0
    g._target = 100.0
    g._step()
    assert g._cur > 0.0


def test_step_noop_when_unavailable(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g._cur = 0.0
    g._target = 80.0
    g.set_unavailable(True)
    g._step()
    assert g._cur == 0.0


def test_step_stable_when_at_target(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g._cur = 50.0
    g._target = 50.0
    g._step()
    assert g._cur == 50.0


def test_blink_frame_advances_above_threshold(tmp_config, qtbot):
    g = _gauge(tmp_config, warn=60, crit=80)
    qtbot.addWidget(g)
    g.blink_above = 70.0
    g._cur = 75.0
    g._target = 75.0
    before = g._blink_frame
    g._step()
    assert g._blink_frame == (before + 1) % 40


def test_blink_resets_when_below_threshold(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g.blink_above = 70.0
    g._cur = 50.0
    g._target = 50.0
    g._blink_on = False
    g._blink_frame = 10
    g._step()
    assert g._blink_on is True
    assert g._blink_frame == 0


def test_paint_event_normal(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g.resize(200, 200)
    g.show()
    qtbot.waitExposed(g)
    g.set_value(50)
    assert not g.grab().isNull()


def test_paint_event_unavailable(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g.resize(200, 200)
    g.show()
    qtbot.waitExposed(g)
    g.set_unavailable(True)
    assert not g.grab().isNull()


def test_color_for_at_one_returns_last_stop(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    assert g._color_for(1.0).name() == g._gradient_stops[-1][1].name()


def test_color_for_between_warn_and_crit(tmp_config, qtbot):
    g = _gauge(tmp_config, warn=60, crit=80)
    qtbot.addWidget(g)
    c = g._color_for(0.75)
    assert isinstance(c, QColor)
