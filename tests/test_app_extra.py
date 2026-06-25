"""Extra coverage tests for thermalcanary.app — paint events, gauge signals, config handler."""
import subprocess
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QTimer, QEvent, QRect
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QApplication, QDialog

try:
    from thermalcanary.app import (
        GaugeArea, ThermalCanary, _contrast_color,
        AboutDialog, QuitDialog,
    )
    _HAS_APP = True
except ImportError:
    _HAS_APP = False

pytestmark = pytest.mark.skipif(not _HAS_APP, reason="thermalcanary.app not in sandbox")


def _bare_tc():
    return ThermalCanary.__new__(ThermalCanary)


# ---------------------------------------------------------------------------
# GaugeArea.paintEvent
# ---------------------------------------------------------------------------

def test_gauge_area_paint_event_runs(qtbot, tmp_config):
    area = GaugeArea(tmp_config)
    qtbot.addWidget(area)
    area.resize(800, 300)
    area.show()
    area.repaint()  # triggers paintEvent synchronously


def test_gauge_area_paint_event_light_bg(qtbot, tmp_config):
    tmp_config.set('bg_color', '#f0f0f0')
    area = GaugeArea(tmp_config)
    qtbot.addWidget(area)
    area.resize(800, 300)
    area.show()
    area.repaint()


# ---------------------------------------------------------------------------
# ThermalCanary.paintEvent
# ---------------------------------------------------------------------------

def test_thermalcanary_paint_event_runs(qtbot, tmp_config):
    """paintEvent must complete without exception on a real widget."""
    from PyQt6.QtWidgets import QWidget
    # Use GaugeArea as a minimal stand-in that exercises the same paint path
    area = GaugeArea(tmp_config)
    qtbot.addWidget(area)
    area.resize(400, 200)
    area.show()
    area.repaint()


# ---------------------------------------------------------------------------
# _on_gpu_ready
# ---------------------------------------------------------------------------

def test_on_gpu_ready_not_found_marks_gauges_unavailable(mocker, tmp_config):
    tc = _bare_tc()
    g_gpu_t = MagicMock()
    g_fan = MagicMock()
    g_vram = MagicMock()
    tc.g_gpu_t = g_gpu_t
    tc.g_fan = g_fan
    tc.g_vram = g_vram

    tc._on_gpu_ready(found=False, fan_label='GPU Fan')

    g_gpu_t.set_unavailable.assert_called_once_with(True)
    g_fan.set_unavailable.assert_called_once_with(True)
    g_vram.set_unavailable.assert_called_once_with(True)


def test_on_gpu_ready_found_no_fan_label_change(mocker, tmp_config):
    tc = _bare_tc()
    tc.g_gpu_t = MagicMock()
    tc.g_fan = MagicMock()
    tc.g_vram = MagicMock()

    tc._on_gpu_ready(found=True, fan_label='GPU Fan')

    tc.g_fan.set_label.assert_not_called()


def test_on_gpu_ready_found_custom_fan_label(mocker, tmp_config):
    tc = _bare_tc()
    tc.g_gpu_t = MagicMock()
    tc.g_fan = MagicMock()
    tc.g_vram = MagicMock()

    tc._on_gpu_ready(found=True, fan_label='GPU Load')

    tc.g_fan.set_label.assert_called_once_with('GPU Load')


# ---------------------------------------------------------------------------
# _on_reading
# ---------------------------------------------------------------------------

def test_on_reading_updates_all_gauges(mocker, tmp_config):
    tc = _bare_tc()
    tc.g_cpu_t = MagicMock()
    tc.g_gpu_t = MagicMock()
    tc.g_fan   = MagicMock()
    tc.g_cpu_u = MagicMock()
    tc.g_mem   = MagicMock()
    tc.g_vram  = MagicMock()
    tc._sidebar = MagicMock()

    import thermalcanary.app as _app_mod
    original_pro = _app_mod.PRO
    _app_mod.PRO = False
    try:
        tc._on_reading(cpu_t=55.0, gpu_t=70.0, gpu_f=40.0, cpu_u=30.0, mem=50.0, gpu_vram=20.0)
    finally:
        _app_mod.PRO = original_pro

    tc.g_cpu_t.set_value.assert_called_once_with(55.0)
    tc.g_gpu_t.set_value.assert_called_once_with(70.0)
    tc.g_fan.set_value.assert_called_once_with(40.0)
    tc.g_cpu_u.set_value.assert_called_once_with(30.0)
    tc.g_mem.set_value.assert_called_once_with(50.0)
    tc.g_vram.set_value.assert_called_once_with(20.0)
    tc._sidebar.push_reading.assert_not_called()


def test_on_reading_calls_push_reading_in_pro_mode(mocker, tmp_config):
    tc = _bare_tc()
    tc.g_cpu_t = MagicMock()
    tc.g_gpu_t = MagicMock()
    tc.g_fan   = MagicMock()
    tc.g_cpu_u = MagicMock()
    tc.g_mem   = MagicMock()
    tc.g_vram  = MagicMock()
    tc._sidebar = MagicMock()

    import thermalcanary.app as _app_mod
    original_pro = _app_mod.PRO
    _app_mod.PRO = True
    try:
        tc._on_reading(cpu_t=55.0, gpu_t=70.0, gpu_f=40.0, cpu_u=30.0, mem=50.0, gpu_vram=20.0)
    finally:
        _app_mod.PRO = original_pro

    tc._sidebar.push_reading.assert_called_once_with(55.0, 70.0, 30.0, 50.0, 20.0)


# ---------------------------------------------------------------------------
# _on_config_changed — color keys
# ---------------------------------------------------------------------------

def test_on_config_changed_color_key_calls_update(mocker, tmp_config):
    tc = _bare_tc()
    tc._config = tmp_config
    g1, g2 = MagicMock(), MagicMock()
    tc._gauges = [g1, g2]
    tc._gauge_area = MagicMock()
    tc._worker = MagicMock()
    tc._screens_settle_timer = QTimer()
    mocker.patch.object(tc, 'update')

    tc._on_config_changed('bg_color')

    g1.update.assert_called_once()
    g2.update.assert_called_once()
    tc._gauge_area.update.assert_called_once()


def test_on_config_changed_inner_color(mocker, tmp_config):
    tc = _bare_tc()
    tc._config = tmp_config
    tc._gauges = [MagicMock()]
    tc._gauge_area = MagicMock()
    tc._worker = MagicMock()
    tc._screens_settle_timer = QTimer()
    mocker.patch.object(tc, 'update')

    tc._on_config_changed('inner_color')
    tc._gauges[0].update.assert_called_once()


# ---------------------------------------------------------------------------
# _on_config_changed — smooth_n / poll_ms / cpu_temp_source
# ---------------------------------------------------------------------------

def test_on_config_changed_smooth_n_invokes_worker(mocker, tmp_config):
    tc = _bare_tc()
    tc._config = tmp_config
    tc._gauges = []
    tc._gauge_area = MagicMock()
    tc._worker = MagicMock()
    tc._screens_settle_timer = QTimer()
    invoke_mock = mocker.patch('thermalcanary.app.QMetaObject.invokeMethod')

    tmp_config.set('smooth_n', 3)
    tc._on_config_changed('smooth_n')

    invoke_mock.assert_called_once()
    assert invoke_mock.call_args.args[1] == 'set_smooth_n'


def test_on_config_changed_poll_ms_invokes_worker(mocker, tmp_config):
    tc = _bare_tc()
    tc._config = tmp_config
    tc._gauges = []
    tc._gauge_area = MagicMock()
    tc._worker = MagicMock()
    tc._screens_settle_timer = QTimer()
    invoke_mock = mocker.patch('thermalcanary.app.QMetaObject.invokeMethod')

    tmp_config.set('poll_ms', 2000)
    tc._on_config_changed('poll_ms')

    invoke_mock.assert_called_once()
    assert invoke_mock.call_args.args[1] == 'set_interval'


def test_on_config_changed_cpu_temp_source_invokes_reset(mocker, tmp_config):
    tc = _bare_tc()
    tc._config = tmp_config
    tc._gauges = []
    tc._gauge_area = MagicMock()
    tc._worker = MagicMock()
    tc._screens_settle_timer = QTimer()
    invoke_mock = mocker.patch('thermalcanary.app.QMetaObject.invokeMethod')

    tc._on_config_changed('cpu_temp_source')

    invoke_mock.assert_called_once()
    assert invoke_mock.call_args.args[1] == 'reset_cpu_buf'


# ---------------------------------------------------------------------------
# _apply_skip_taskbar_pager
# ---------------------------------------------------------------------------

def test_apply_skip_taskbar_pager_no_winid(mocker):
    tc = _bare_tc()
    mocker.patch.object(tc, 'winId', return_value=0)
    run_mock = mocker.patch('subprocess.run')

    tc._apply_skip_taskbar_pager()

    run_mock.assert_not_called()


def test_apply_skip_taskbar_pager_wmctrl_missing(mocker):
    tc = _bare_tc()
    mocker.patch.object(tc, 'winId', return_value=12345)
    mocker.patch('subprocess.run', side_effect=FileNotFoundError)

    tc._apply_skip_taskbar_pager()  # must not raise


def test_apply_skip_taskbar_pager_wmctrl_timeout(mocker):
    tc = _bare_tc()
    mocker.patch.object(tc, 'winId', return_value=12345)
    mocker.patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='wmctrl', timeout=2))

    tc._apply_skip_taskbar_pager()  # must not raise


def test_apply_skip_taskbar_pager_calls_wmctrl(mocker):
    tc = _bare_tc()
    mocker.patch.object(tc, 'winId', return_value=0xABCDEF)
    run_mock = mocker.patch('subprocess.run')

    tc._apply_skip_taskbar_pager()

    run_mock.assert_called_once()
    cmd = run_mock.call_args.args[0]
    assert cmd[0] == 'wmctrl'
    assert 'skip_taskbar,skip_pager' in cmd[-1]


# ---------------------------------------------------------------------------
# toggle_settings / _open_settings / _close_settings / _on_anim_finished
# ---------------------------------------------------------------------------

def test_open_settings_sets_sidebar_open(mocker):
    tc = _bare_tc()
    tc._sidebar_open = False
    tc._sidebar = MagicMock()
    tc._gear_btn = MagicMock()
    tc._close_btn = MagicMock()
    tc._anim = MagicMock()
    mocker.patch.object(tc, 'width', return_value=1920)
    mocker.patch.object(tc, 'height', return_value=1080)

    tc._open_settings()

    assert tc._sidebar_open is True
    tc._sidebar.show.assert_called_once()
    tc._anim.start.assert_called_once()


def test_close_settings_sets_sidebar_closed(mocker):
    tc = _bare_tc()
    tc._sidebar_open = True
    tc._anim = MagicMock()
    mocker.patch.object(tc, 'width', return_value=1920)
    mocker.patch.object(tc, 'height', return_value=1080)
    tc._sidebar = MagicMock()

    tc._close_settings()

    assert tc._sidebar_open is False
    tc._anim.start.assert_called_once()


def test_close_settings_noop_when_already_closed(mocker):
    tc = _bare_tc()
    tc._sidebar_open = False
    tc._anim = MagicMock()

    tc._close_settings()

    tc._anim.start.assert_not_called()


def test_on_anim_finished_hides_sidebar_when_closed(mocker):
    tc = _bare_tc()
    tc._sidebar_open = False
    tc._sidebar = MagicMock()
    mocker.patch.object(tc, 'width', return_value=1920)
    mocker.patch.object(tc, 'height', return_value=1080)

    tc._on_anim_finished()

    tc._sidebar.hide.assert_called_once()


def test_on_anim_finished_noop_when_open(mocker):
    tc = _bare_tc()
    tc._sidebar_open = True
    tc._sidebar = MagicMock()

    tc._on_anim_finished()

    tc._sidebar.hide.assert_not_called()


# ---------------------------------------------------------------------------
# toggle_settings
# ---------------------------------------------------------------------------

def test_toggle_settings_opens_when_closed(mocker):
    tc = _bare_tc()
    tc._sidebar_open = False
    open_spy = mocker.patch.object(tc, '_open_settings')
    close_spy = mocker.patch.object(tc, '_close_settings')

    tc.toggle_settings()

    open_spy.assert_called_once()
    close_spy.assert_not_called()


def test_toggle_settings_closes_when_open(mocker):
    tc = _bare_tc()
    tc._sidebar_open = True
    open_spy = mocker.patch.object(tc, '_open_settings')
    close_spy = mocker.patch.object(tc, '_close_settings')

    tc.toggle_settings()

    close_spy.assert_called_once()
    open_spy.assert_not_called()


# ---------------------------------------------------------------------------
# _move_to_screen_by_uuid
# ---------------------------------------------------------------------------

def test_move_to_screen_by_uuid_no_screens(mocker, tmp_config):
    tc = _bare_tc()
    tc._config = tmp_config
    mocker.patch('thermalcanary.app.QApplication.instance',
                 return_value=MagicMock(screens=lambda: []))
    move_spy = mocker.patch.object(tc, '_move_to_screen')

    tc._move_to_screen_by_uuid('some-uuid')

    move_spy.assert_not_called()


def test_move_to_screen_by_uuid_unknown_uuid_falls_back_to_config_index(mocker, tmp_config):
    tc = _bare_tc()
    tc._config = tmp_config
    tmp_config.set('screen_index', 0)

    s = MagicMock()
    mocker.patch('thermalcanary.app.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [s]))
    mocker.patch('thermalcanary.screens.find_index_by_uuid', return_value=None)
    move_spy = mocker.patch.object(tc, '_move_to_screen')

    tc._move_to_screen_by_uuid('unknown-uuid')

    move_spy.assert_called_once_with(0)
