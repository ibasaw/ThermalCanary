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


# ---------------------------------------------------------------------------
# Mutation-killing tests — _lerp_hsv
# ---------------------------------------------------------------------------

from thermalcanary.gauge import _lerp_hsv


def test_lerp_hsv_t0_returns_c1():
    c1 = QColor('#00aaff')
    c2 = QColor('#ff2020')
    result = _lerp_hsv(c1, c2, 0.0)
    assert result.hsvHueF() == pytest.approx(c1.hsvHueF(), abs=0.01)
    assert result.hsvSaturationF() == pytest.approx(c1.hsvSaturationF(), abs=0.01)
    assert result.valueF() == pytest.approx(c1.valueF(), abs=0.01)


def test_lerp_hsv_t1_returns_c2():
    c1 = QColor('#00aaff')
    c2 = QColor('#ff2020')
    result = _lerp_hsv(c1, c2, 1.0)
    assert result.hsvHueF() == pytest.approx(c2.hsvHueF(), abs=0.01)
    assert result.hsvSaturationF() == pytest.approx(c2.hsvSaturationF(), abs=0.01)
    assert result.valueF() == pytest.approx(c2.valueF(), abs=0.01)


def test_lerp_hsv_midpoint_saturation_is_avg():
    c1 = QColor.fromHsvF(0.5, 0.8, 1.0)
    c2 = QColor.fromHsvF(0.5, 0.2, 0.4)
    result = _lerp_hsv(c1, c2, 0.5)
    assert result.hsvSaturationF() == pytest.approx(0.5, abs=0.01)
    assert result.valueF() == pytest.approx(0.7, abs=0.01)


def test_lerp_hsv_achromatic_c1_inherits_c2_hue():
    # h1 < 0 → h1 = h2 — the achromatic branch
    c1 = QColor('#808080')   # grey: hsvHueF() == -1
    c2 = QColor('#00aaff')   # blue
    assert c1.hsvHueF() < 0
    result = _lerp_hsv(c1, c2, 1.0)
    assert result.hsvHueF() == pytest.approx(c2.hsvHueF(), abs=0.01)


def test_lerp_hsv_achromatic_c2_inherits_c1_hue():
    # h2 < 0 → h2 = h1
    c1 = QColor('#ff2020')
    c2 = QColor('#808080')   # grey: hsvHueF() == -1
    result = _lerp_hsv(c1, c2, 0.0)
    assert result.hsvHueF() == pytest.approx(c1.hsvHueF(), abs=0.01)


def test_lerp_hsv_both_achromatic_hue_is_zero():
    # both h < 0 → h1 = h2 = 0.0
    c1 = QColor('#000000')
    c2 = QColor('#ffffff')
    result = _lerp_hsv(c1, c2, 0.5)
    assert result.hsvHueF() == pytest.approx(0.0, abs=0.01)


def test_lerp_hsv_red_h0_not_treated_as_achromatic():
    # h1 = 0.0 (red) must NOT be overwritten by h2 (< branch, not <=)
    c1 = QColor('#ff0000')   # pure red: hsvHueF() == 0.0
    c2 = QColor('#00ff00')   # green: hsvHueF() == 0.333
    assert c1.hsvHueF() == pytest.approx(0.0, abs=0.001)
    result = _lerp_hsv(c1, c2, 0.5)
    # If h1 were incorrectly replaced, we'd get hue=0.333; correct path gives ~0.167
    assert result.hsvHueF() < 0.25


def test_lerp_hsv_wraparound_dh_gt_half():
    # h2 - h1 > 0.5: must subtract 1 to take the short arc
    # red (h=0) → blue (h≈0.667): dh=0.667 > 0.5 → short arc goes ~0.833
    c1 = QColor('#ff0000')
    c2 = QColor('#0000ff')
    result = _lerp_hsv(c1, c2, 0.5)
    h = result.hsvHueF()
    # Short path wraps to magenta side (~0.833); long path would give ~0.333 (green)
    assert h > 0.5


def test_lerp_hsv_wraparound_dh_lt_neg_half():
    # h2 - h1 < -0.5: must add 1 to take the short arc
    # blue (h≈0.667) → red (h=0): dh=-0.667 < -0.5 → short arc also ~0.833
    c1 = QColor('#0000ff')
    c2 = QColor('#ff0000')
    result = _lerp_hsv(c1, c2, 0.5)
    h = result.hsvHueF()
    assert h > 0.5


def test_lerp_hsv_no_wraparound_short_hue_diff():
    # Small hue diff — no wraparound branch taken; result hue is between c1 and c2
    c1 = QColor.fromHsvF(0.1, 1.0, 1.0)
    c2 = QColor.fromHsvF(0.3, 1.0, 1.0)
    result = _lerp_hsv(c1, c2, 0.5)
    assert 0.1 < result.hsvHueF() < 0.3


# ---------------------------------------------------------------------------
# Mutation-killing tests — _build_stops with non-zero lo
# ---------------------------------------------------------------------------

def test_build_stops_nonzero_lo_span_is_hi_minus_lo(tmp_config, qtbot):
    # span = hi - lo (not hi + lo): with lo=10, hi=110, warn=60, crit=90
    g = Gauge("T", "°C", 10, 110, "#ff0000", tmp_config, warn=60, crit=90)
    qtbot.addWidget(g)
    stops = g._gradient_stops
    assert pytest.approx(stops[2][0], abs=0.001) == 0.5   # warn_r = (60-10)/100
    assert pytest.approx(stops[4][0], abs=0.001) == 0.8   # crit_r = (90-10)/100
    assert pytest.approx(stops[3][0], abs=0.001) == 0.65  # mid_r


def test_build_stops_mid_ratio_is_arithmetic_mean(tmp_config, qtbot):
    # mid_r = (warn_r + crit_r) / 2, not (warn_r * crit_r) or (warn_r - crit_r)
    g = Gauge("T", "°C", 0, 100, "#ff0000", tmp_config, warn=40, crit=80)
    qtbot.addWidget(g)
    stops = g._gradient_stops
    warn_r = stops[2][0]
    crit_r = stops[4][0]
    mid_r  = stops[3][0]
    assert pytest.approx(mid_r, abs=0.001) == (warn_r + crit_r) / 2


def test_build_stops_default_gradient_when_no_warn_crit(tmp_config, qtbot):
    g = Gauge("T", "°C", 20, 120, "#ff0000", tmp_config)
    qtbot.addWidget(g)
    from thermalcanary.gauge import _DEFAULT_GRADIENT
    stops = g._gradient_stops
    assert len(stops) == len(_DEFAULT_GRADIENT)
    for (p_actual, _), (p_expected, _) in zip(stops, _DEFAULT_GRADIENT):
        assert pytest.approx(p_actual, abs=0.001) == p_expected


# ---------------------------------------------------------------------------
# Mutation-killing tests — _color_for boundary/interpolation
# ---------------------------------------------------------------------------

def test_color_for_above_1_clamps_to_last_stop(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    assert g._color_for(1.5).name() == g._color_for(1.0).name()


def test_color_for_below_0_clamps_to_first_stop(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    assert g._color_for(-0.5).name() == g._color_for(0.0).name()


def test_color_for_interpolation_uses_ratio_minus_p0(tmp_config, qtbot):
    # t = (ratio - p0) / (p1 - p0) — not (ratio + p0)
    # Between stops[1]=(0.25, green) and stops[2]=(0.65, yellow): ratio=0.45
    # t = (0.45 - 0.25) / (0.65 - 0.25) = 0.2 / 0.4 = 0.5
    # mutation (ratio + p0) → t = (0.45 + 0.25) / 0.4 = 1.75 → very different interpolation
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    c_low  = g._color_for(0.25)   # green stop
    c_high = g._color_for(0.65)   # yellow stop
    c_mid  = g._color_for(0.45)   # midpoint
    assert c_mid.name() != c_low.name()
    assert c_mid.name() != c_high.name()
    # t=0.5 means result should be closer to neither extreme
    assert c_mid.hsvHueF() != pytest.approx(c_low.hsvHueF(), abs=0.01)


def test_color_for_exact_first_stop_ratio(tmp_config, qtbot):
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    first_stop_ratio = g._gradient_stops[0][0]  # 0.0
    assert g._color_for(first_stop_ratio).name() == g._gradient_stops[0][1].name()


# ---------------------------------------------------------------------------
# Mutation-killing tests — _step exact boundary and blink logic
# ---------------------------------------------------------------------------

def test_step_d_exactly_threshold_does_not_move(tmp_config, qtbot):
    # abs(d) == 0.02 is NOT > 0.02, so _cur must NOT change
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g._cur = 0.0
    g._target = 0.02
    g._step()
    assert g._cur == pytest.approx(0.0, abs=1e-9)


def test_step_just_above_threshold_moves(tmp_config, qtbot):
    # abs(d) = 0.03 > 0.02 → _cur must change
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g._cur = 0.0
    g._target = 0.03
    g._step()
    assert g._cur > 0.0


def test_step_advance_coefficient_is_014(tmp_config, qtbot):
    # _cur += d * 0.14 — not d/0.14 or d+0.14
    g = _gauge(tmp_config)
    qtbot.addWidget(g)
    g._cur = 0.0
    g._target = 10.0
    g._step()
    assert pytest.approx(g._cur, abs=0.01) == 10.0 * 0.14


def test_step_blink_frame_wraps_at_40(tmp_config, qtbot):
    g = _gauge(tmp_config, warn=60, crit=80)
    qtbot.addWidget(g)
    g.blink_above = 50.0
    g._cur = 60.0
    g._target = 60.0
    g._blink_frame = 39
    g._step()
    assert g._blink_frame == 0   # (39 + 1) % 40 = 0, not 40


def test_step_new_on_true_at_frame_25(tmp_config, qtbot):
    # new_on = _blink_frame < 26: frame 25 → True
    g = _gauge(tmp_config, warn=60, crit=80)
    qtbot.addWidget(g)
    g.blink_above = 50.0
    g._cur = 60.0
    g._target = 60.0
    g._blink_on = False
    g._blink_frame = 24  # after +1 → 25 < 26 → True
    g._step()
    assert g._blink_on is True


def test_step_blink_off_at_frame_26(tmp_config, qtbot):
    # new_on = _blink_frame < 26: frame 26 → False
    g = _gauge(tmp_config, warn=60, crit=80)
    qtbot.addWidget(g)
    g.blink_above = 50.0
    g._cur = 60.0
    g._target = 60.0
    g._blink_on = True
    g._blink_frame = 25  # after +1 → 26, 26 < 26 → False
    g._step()
    assert g._blink_on is False


# ---------------------------------------------------------------------------
# Mutation-killing tests — __init__ defaults
# ---------------------------------------------------------------------------

def test_gauge_default_decimals_is_zero(tmp_config, qtbot):
    g = Gauge("T", "°C", 0, 100, "#ff0000", tmp_config)
    qtbot.addWidget(g)
    assert g.decimals == 0


def test_gauge_default_blink_above_is_none(tmp_config, qtbot):
    g = Gauge("T", "°C", 0, 100, "#ff0000", tmp_config)
    qtbot.addWidget(g)
    assert g.blink_above is None


def test_gauge_initial_cur_equals_lo(tmp_config, qtbot):
    g = Gauge("T", "°C", 20, 120, "#ff0000", tmp_config)
    qtbot.addWidget(g)
    assert g._cur == pytest.approx(20.0)


def test_gauge_initial_target_equals_lo(tmp_config, qtbot):
    g = Gauge("T", "°C", 20, 120, "#ff0000", tmp_config)
    qtbot.addWidget(g)
    assert g._target == pytest.approx(20.0)


def test_gauge_initial_unavailable_false(tmp_config, qtbot):
    g = Gauge("T", "°C", 0, 100, "#ff0000", tmp_config)
    qtbot.addWidget(g)
    assert g._unavailable is False


def test_gauge_initial_blink_on_true(tmp_config, qtbot):
    g = Gauge("T", "°C", 0, 100, "#ff0000", tmp_config)
    qtbot.addWidget(g)
    assert g._blink_on is True


def test_gauge_initial_blink_frame_zero(tmp_config, qtbot):
    g = Gauge("T", "°C", 0, 100, "#ff0000", tmp_config)
    qtbot.addWidget(g)
    assert g._blink_frame == 0
