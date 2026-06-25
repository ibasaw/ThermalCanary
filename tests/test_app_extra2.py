"""Second batch of app.py coverage tests — widget lifecycle methods."""
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QEvent, QRect, QTimer
from PyQt6.QtWidgets import QApplication, QDialog, QWidget

try:
    from thermalcanary.app import GaugeArea, ThermalCanary, AboutDialog, QuitDialog
    _HAS_APP = True
except ImportError:
    _HAS_APP = False

pytestmark = pytest.mark.skipif(not _HAS_APP, reason="thermalcanary.app not in sandbox")


def _bare_tc():
    return ThermalCanary.__new__(ThermalCanary)


# ---------------------------------------------------------------------------
# GaugeArea.paintEvent — via QPainter mock so no real display needed
# ---------------------------------------------------------------------------

def test_gauge_area_paint_event_via_mock(mocker, tmp_config, qtbot):
    area = GaugeArea(tmp_config)
    qtbot.addWidget(area)
    area.resize(800, 300)
    painter_mock = MagicMock()
    mocker.patch('thermalcanary.app.QPainter', return_value=painter_mock)
    area.paintEvent(MagicMock())
    painter_mock.fillRect.assert_called()
    painter_mock.end.assert_called_once()


def test_gauge_area_paint_event_draws_two_labels(mocker, tmp_config, qtbot):
    """paintEvent draws exactly two row labels: CPU and GPU."""
    area = GaugeArea(tmp_config)
    qtbot.addWidget(area)
    area.resize(800, 300)
    painter_mock = MagicMock()
    mocker.patch('thermalcanary.app.QPainter', return_value=painter_mock)
    area.paintEvent(MagicMock())
    draw_text_calls = painter_mock.drawText.call_args_list
    texts = [str(c) for c in draw_text_calls]
    labels = [c for t in texts for c in ('CPU', 'GPU') if c in t]
    assert len(labels) == 2


# ---------------------------------------------------------------------------
# ThermalCanary.paintEvent
# ---------------------------------------------------------------------------

def test_thermalcanary_paint_event_fills_rect(mocker, tmp_config):
    tc = _bare_tc()
    tc._config = tmp_config
    painter_mock = MagicMock()
    mocker.patch('thermalcanary.app.QPainter', return_value=painter_mock)
    mocker.patch.object(tc, 'rect', return_value=MagicMock())
    tc.paintEvent(MagicMock())
    painter_mock.fillRect.assert_called_once()
    painter_mock.end.assert_called_once()


# ---------------------------------------------------------------------------
# _on_screens_changed — starts the settle timer (line 337)
# ---------------------------------------------------------------------------

def test_on_screens_changed_starts_settle_timer():
    tc = _bare_tc()
    timer = QTimer()
    timer.setSingleShot(True)
    tc._screens_settle_timer = timer

    assert not timer.isActive()
    tc._on_screens_changed()
    assert timer.isActive()
    timer.stop()


# ---------------------------------------------------------------------------
# _show_about (lines 400-403)
# ---------------------------------------------------------------------------

def test_show_about_creates_and_executes_dialog(mocker):
    tc = _bare_tc()
    about_cls = mocker.patch('thermalcanary.app.AboutDialog')
    about_inst = about_cls.return_value
    about_inst.rect.return_value = MagicMock(center=MagicMock(return_value=MagicMock()))
    mocker.patch.object(tc, 'geometry', return_value=MagicMock(center=MagicMock(return_value=MagicMock())))

    tc._show_about()

    about_cls.assert_called_once_with(tc)
    about_inst.adjustSize.assert_called_once()
    about_inst.exec.assert_called_once()


# ---------------------------------------------------------------------------
# _confirm_quit (lines 406-416)
# ---------------------------------------------------------------------------

def test_confirm_quit_reject_does_not_quit(mocker):
    tc = _bare_tc()
    quit_cls = mocker.patch('thermalcanary.app.QuitDialog')
    quit_inst = quit_cls.return_value
    quit_inst.exec.return_value = QDialog.DialogCode.Rejected
    quit_inst.rect.return_value = MagicMock(center=MagicMock(return_value=MagicMock()))
    mocker.patch.object(tc, 'geometry', return_value=MagicMock(center=MagicMock(return_value=MagicMock())))
    app_quit = mocker.patch.object(QApplication.instance(), 'quit')

    tc._confirm_quit()

    app_quit.assert_not_called()


def test_confirm_quit_accept_saves_and_quits(mocker, tmp_config):
    tc = _bare_tc()
    tc._config = tmp_config
    tc._worker = MagicMock()
    tc._thread = MagicMock()
    tc._thread.isRunning.return_value = False

    quit_cls = mocker.patch('thermalcanary.app.QuitDialog')
    quit_inst = quit_cls.return_value
    quit_inst.exec.return_value = QDialog.DialogCode.Accepted
    quit_inst.rect.return_value = MagicMock(center=MagicMock(return_value=MagicMock()))
    mocker.patch.object(tc, 'geometry', return_value=MagicMock(center=MagicMock(return_value=MagicMock())))
    mocker.patch('thermalcanary.app.QMetaObject.invokeMethod')
    app_quit = mocker.patch.object(QApplication.instance(), 'quit')
    save_spy = mocker.patch.object(tmp_config, 'save_now')

    tc._confirm_quit()

    save_spy.assert_called_once()
    app_quit.assert_called_once()


# ---------------------------------------------------------------------------
# resizeEvent (lines 419-425)
# ---------------------------------------------------------------------------

def test_resize_event_moves_buttons(mocker):
    tc = _bare_tc()
    tc._gear_btn = MagicMock()
    tc._close_btn = MagicMock()
    tc._sidebar = MagicMock()
    tc._sidebar_open = False
    mocker.patch.object(tc, 'width', return_value=1920)
    mocker.patch.object(tc, 'height', return_value=1080)
    mocker.patch.object(QWidget, 'resizeEvent')

    tc.resizeEvent(MagicMock())

    tc._gear_btn.move.assert_called_once_with(1920 - 84, 8)
    tc._close_btn.move.assert_called_once_with(1920 - 44, 8)


def test_resize_event_updates_sidebar_geometry_when_open(mocker):
    from thermalcanary.app import SIDEBAR_W
    tc = _bare_tc()
    tc._gear_btn = MagicMock()
    tc._close_btn = MagicMock()
    tc._sidebar = MagicMock()
    tc._sidebar_open = True
    mocker.patch.object(tc, 'width', return_value=1920)
    mocker.patch.object(tc, 'height', return_value=1080)
    mocker.patch.object(QWidget, 'resizeEvent')

    tc.resizeEvent(MagicMock())

    tc._sidebar.setGeometry.assert_called_once_with(1920 - SIDEBAR_W, 0, SIDEBAR_W, 1080)


def test_resize_event_collapses_sidebar_when_closed(mocker):
    tc = _bare_tc()
    tc._gear_btn = MagicMock()
    tc._close_btn = MagicMock()
    tc._sidebar = MagicMock()
    tc._sidebar_open = False
    mocker.patch.object(tc, 'width', return_value=1920)
    mocker.patch.object(tc, 'height', return_value=1080)
    mocker.patch.object(QWidget, 'resizeEvent')

    tc.resizeEvent(MagicMock())

    tc._sidebar.setGeometry.assert_called_once_with(1920, 0, 0, 1080)


# ---------------------------------------------------------------------------
# _move_to_screen (lines 483-503)
# ---------------------------------------------------------------------------

def test_move_to_screen_no_screens_early_return(mocker):
    tc = _bare_tc()
    tc._pending_target_screen = None
    tc._pending_target_geo = None
    tc._move_generation = 0
    mocker.patch('thermalcanary.app.QApplication.instance',
                 return_value=MagicMock(screens=lambda: []))
    apply_spy = mocker.patch.object(tc, '_apply_pending_move')

    tc._move_to_screen(0)

    apply_spy.assert_not_called()


def test_move_to_screen_no_window_handle_schedules_retry(mocker):
    tc = _bare_tc()
    tc._pending_target_screen = None
    tc._pending_target_geo = None
    tc._move_generation = 0
    s = MagicMock()
    s.geometry.return_value = QRect(0, 0, 1920, 1080)
    mocker.patch('thermalcanary.app.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [s]))
    mocker.patch.object(tc, 'windowHandle', return_value=None)
    mocker.patch.object(tc, 'setMinimumSize')
    # Prevent the 50ms retry timer from firing after the test (bare TC has no C++ wrapper)
    mocker.patch('thermalcanary.app.QTimer.singleShot')

    tc._move_to_screen(0)

    # Pending targets must be set even when window handle is absent
    assert tc._pending_target_screen is s
    assert tc._pending_target_geo == QRect(0, 0, 1920, 1080)


def test_move_to_screen_not_fullscreen_applies_directly(mocker):
    tc = _bare_tc()
    tc._pending_target_screen = None
    tc._pending_target_geo = None
    tc._move_generation = 0
    s = MagicMock()
    s.geometry.return_value = QRect(0, 0, 1920, 1080)
    mocker.patch('thermalcanary.app.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [s]))
    mocker.patch.object(tc, 'windowHandle', return_value=MagicMock())
    mocker.patch.object(tc, 'isFullScreen', return_value=False)
    mocker.patch.object(tc, 'setMinimumSize')
    apply_spy = mocker.patch.object(tc, '_apply_pending_move')

    tc._move_to_screen(0)

    apply_spy.assert_called_once()


def test_move_to_screen_fullscreen_shows_normal_first(mocker):
    tc = _bare_tc()
    tc._pending_target_screen = None
    tc._pending_target_geo = None
    tc._move_generation = 0
    s = MagicMock()
    s.geometry.return_value = QRect(0, 0, 1920, 1080)
    mocker.patch('thermalcanary.app.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [s]))
    mocker.patch.object(tc, 'windowHandle', return_value=MagicMock())
    mocker.patch.object(tc, 'isFullScreen', return_value=True)
    mocker.patch.object(tc, 'setMinimumSize')
    show_normal_spy = mocker.patch.object(tc, 'showNormal')
    # Prevent the 400ms deferred callback from firing after test teardown
    mocker.patch('thermalcanary.app.QTimer.singleShot')

    tc._move_to_screen(0)

    show_normal_spy.assert_called_once()


# ---------------------------------------------------------------------------
# _apply_pending_move (lines 517-546)
# ---------------------------------------------------------------------------

def test_apply_pending_move_no_pending_is_noop(mocker):
    tc = _bare_tc()
    tc._pending_target_geo = None
    tc._pending_target_screen = None
    wh_spy = mocker.patch.object(tc, 'windowHandle')

    tc._apply_pending_move()

    wh_spy.assert_not_called()


def test_apply_pending_move_stale_screen_aborts(mocker):
    tc = _bare_tc()
    tc._move_generation = 0
    stale_screen = MagicMock()
    tc._pending_target_geo = QRect(0, 0, 1920, 1080)
    tc._pending_target_screen = stale_screen
    # Screen not in current list → stale
    mocker.patch('thermalcanary.app.QApplication.instance',
                 return_value=MagicMock(screens=lambda: []))
    wh_spy = mocker.patch.object(tc, 'windowHandle')

    tc._apply_pending_move()

    wh_spy.assert_not_called()


def test_apply_pending_move_no_window_handle_aborts(mocker):
    tc = _bare_tc()
    tc._move_generation = 0
    screen = MagicMock()
    tc._pending_target_geo = QRect(0, 0, 1920, 1080)
    tc._pending_target_screen = screen
    mocker.patch('thermalcanary.app.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [screen]))
    mocker.patch.object(tc, 'windowHandle', return_value=None)

    tc._apply_pending_move()  # must not crash

    assert tc._pending_target_geo is None  # cleared before the wh check


def test_apply_pending_move_sets_screen_and_geometry(mocker):
    tc = _bare_tc()
    tc._move_generation = 0
    tc._sidebar = MagicMock()
    tc._gear_btn = MagicMock()
    tc._close_btn = MagicMock()
    screen = MagicMock()
    geo = QRect(0, 0, 1920, 1080)
    tc._pending_target_geo = geo
    tc._pending_target_screen = screen
    mocker.patch('thermalcanary.app.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [screen]))
    wh = MagicMock()
    mocker.patch.object(tc, 'windowHandle', return_value=wh)
    mocker.patch.object(tc, 'setGeometry')
    # Prevent the 50ms _refullscreen timer from firing after test teardown
    mocker.patch('thermalcanary.app.QTimer.singleShot')

    tc._apply_pending_move()

    wh.setScreen.assert_called_once_with(screen)
    tc.setGeometry.assert_called_once_with(geo)


# ---------------------------------------------------------------------------
# changeEvent (lines 552-553)
# ---------------------------------------------------------------------------

def test_change_event_window_state_with_pending_applies_move(mocker):
    tc = _bare_tc()
    tc._pending_target_geo = MagicMock()
    apply_spy = mocker.patch.object(tc, '_apply_pending_move')
    mocker.patch.object(tc, 'isFullScreen', return_value=False)
    mocker.patch.object(QWidget, 'changeEvent')

    event = MagicMock()
    event.type.return_value = QEvent.Type.WindowStateChange
    tc.changeEvent(event)

    apply_spy.assert_called_once()


def test_change_event_non_state_event_ignored(mocker):
    tc = _bare_tc()
    tc._pending_target_geo = MagicMock()
    apply_spy = mocker.patch.object(tc, '_apply_pending_move')
    mocker.patch.object(QWidget, 'changeEvent')

    event = MagicMock()
    event.type.return_value = QEvent.Type.Move  # not WindowStateChange
    tc.changeEvent(event)

    apply_spy.assert_not_called()


def test_change_event_still_fullscreen_no_move(mocker):
    """changeEvent must not apply move if the window is still fullscreen."""
    tc = _bare_tc()
    tc._pending_target_geo = MagicMock()
    apply_spy = mocker.patch.object(tc, '_apply_pending_move')
    mocker.patch.object(tc, 'isFullScreen', return_value=True)  # still FS
    mocker.patch.object(QWidget, 'changeEvent')

    event = MagicMock()
    event.type.return_value = QEvent.Type.WindowStateChange
    tc.changeEvent(event)

    apply_spy.assert_not_called()


# ---------------------------------------------------------------------------
# closeEvent (lines 555-571)
# ---------------------------------------------------------------------------

def test_close_event_tray_minimize_ignores_event(mocker, tmp_config):
    tc = _bare_tc()
    tc._tray = MagicMock()
    tc._tray.tray = MagicMock()  # tray icon present
    tc._config = tmp_config
    tmp_config.set('tray_minimize_to_tray', True)
    hide_spy = mocker.patch.object(tc, 'hide')
    mocker.patch.object(QWidget, 'closeEvent')

    event = MagicMock()
    tc.closeEvent(event)

    event.ignore.assert_called_once()
    hide_spy.assert_called_once()
    tc._tray.update_menu_label.assert_called_once()


def test_close_event_no_tray_saves_config(mocker, tmp_config):
    tc = _bare_tc()
    tc._tray = MagicMock()
    tc._tray.tray = None  # no tray icon
    tc._config = tmp_config
    tc._thread = MagicMock()
    tc._thread.isRunning.return_value = False
    tc._worker = MagicMock()
    save_spy = mocker.patch.object(tmp_config, 'save_now')
    mocker.patch.object(QWidget, 'closeEvent')

    tc.closeEvent(MagicMock())

    save_spy.assert_called_once()
    tc._thread.quit.assert_not_called()  # thread not running → skip


def test_close_event_running_thread_is_stopped(mocker, tmp_config):
    tc = _bare_tc()
    tc._tray = MagicMock()
    tc._tray.tray = None
    tc._config = tmp_config
    tc._thread = MagicMock()
    tc._thread.isRunning.return_value = True
    tc._worker = MagicMock()
    mocker.patch.object(tmp_config, 'save_now')
    mocker.patch('thermalcanary.app.QMetaObject.invokeMethod')
    mocker.patch.object(QWidget, 'closeEvent')

    tc.closeEvent(MagicMock())

    tc._thread.quit.assert_called_once()
    tc._thread.wait.assert_called_once()


# ---------------------------------------------------------------------------
# place_on_screen (lines 582-592)
# ---------------------------------------------------------------------------

def test_place_on_screen_shows_window_and_defers(mocker, tmp_config):
    tc = _bare_tc()
    tc._move_generation = 0
    tc._config = tmp_config
    tmp_config.set('screen_uuid', None)
    show_spy = mocker.patch.object(tc, 'show')
    mocker.patch.object(tc, '_move_to_screen_by_uuid')
    mocker.patch.object(tc, '_apply_skip_taskbar_pager')
    # Prevent the 300ms and 500ms timers from firing after test teardown
    mocker.patch('thermalcanary.app.QTimer.singleShot')

    tc.place_on_screen()

    show_spy.assert_called_once()
