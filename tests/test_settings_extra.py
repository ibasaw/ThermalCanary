"""Extra coverage tests for thermalcanary.settings — dialog methods and edge paths."""
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication, QDialog

try:
    from thermalcanary.settings import SettingsSidebar
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

pytestmark = pytest.mark.skipif(not _HAS_SETTINGS, reason="settings module unavailable")


def _make_mock_screen(mocker, name='DP-1', mfg='Acme', model='X', serial='S', w=527.0, h=296.0):
    from PyQt6.QtCore import QSizeF
    s = mocker.MagicMock()
    s.name.return_value = name
    s.manufacturer.return_value = mfg
    s.model.return_value = model
    s.serialNumber.return_value = serial
    s.physicalSize.return_value = QSizeF(w, h)
    s.availableGeometry.return_value = QRect(0, 0, 1920, 1080)
    return s


def _make_sidebar(qtbot, tmp_config, mocker):
    sb = SettingsSidebar(tmp_config, worker=MagicMock())
    qtbot.addWidget(sb)
    return sb


# ---------------------------------------------------------------------------
# push_reading
# ---------------------------------------------------------------------------

def test_push_reading_when_session_panel_none(qtbot, tmp_config, mocker):
    """push_reading must silently no-op when _session_panel is None (free tier)."""
    sb = _make_sidebar(qtbot, tmp_config, mocker)
    assert sb._session_panel is None  # free build
    # Must not raise
    sb.push_reading(60.0, 55.0, 30.0, 40.0, 10.0)


def test_push_reading_when_session_panel_set(qtbot, tmp_config, mocker):
    """push_reading delegates to session panel when one is injected."""
    sb = _make_sidebar(qtbot, tmp_config, mocker)
    panel_mock = MagicMock()
    sb._session_panel = panel_mock
    sb.push_reading(60.0, 55.0, 30.0, 40.0, 10.0)
    panel_mock.push.assert_called_once_with(60.0, 55.0, 30.0, 40.0, 10.0)


# ---------------------------------------------------------------------------
# _refresh_combo_items — exception paths
# ---------------------------------------------------------------------------

def test_refresh_combo_items_swallows_disconnect_error(qtbot, tmp_config, mocker):
    """If a screen signal disconnect raises TypeError/RuntimeError (stale screen
    object after DPMS), _refresh_combo_items must swallow it and continue."""
    sb = _make_sidebar(qtbot, tmp_config, mocker)

    broken_signal = MagicMock()
    broken_signal.disconnect.side_effect = RuntimeError('wrapped C++ object deleted')
    # Inject a stale connection
    screen_mock = _make_mock_screen(mocker)
    sb._screen_signal_conns = [(screen_mock, broken_signal, lambda: None)]

    live_screen = _make_mock_screen(mocker, name='DP-2')
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [live_screen]))

    # Must not raise despite the broken disconnect
    sb._refresh_combo_items()


def test_refresh_combo_items_empty_screen_name_uses_manufacturer(qtbot, tmp_config, mocker):
    """When QScreen.name() returns empty string, combo item must use mfg+model."""
    sb = _make_sidebar(qtbot, tmp_config, mocker)

    nameless = _make_mock_screen(mocker, name='', mfg='Acme', model='UW34')
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [nameless]))

    sb._refresh_combo_items()

    combo_text = sb._screen_combo.itemText(0)
    assert 'Acme' in combo_text or 'UW34' in combo_text


def test_refresh_combo_items_empty_geometry_shows_unknown_size(qtbot, tmp_config, mocker):
    """When availableGeometry() is empty (DPMS-off transient), combo shows '?×?'."""
    from PyQt6.QtCore import QRect as _QRect
    sb = _make_sidebar(qtbot, tmp_config, mocker)

    s = _make_mock_screen(mocker)
    s.availableGeometry.return_value = _QRect()  # isEmpty() == True

    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [s]))

    sb._refresh_combo_items()

    combo_text = sb._screen_combo.itemText(0)
    assert '?' in combo_text


# ---------------------------------------------------------------------------
# _save_default_monitor
# ---------------------------------------------------------------------------

def test_save_default_monitor_valid_index(qtbot, tmp_config, mocker):
    sb = _make_sidebar(qtbot, tmp_config, mocker)
    live = _make_mock_screen(mocker, name='DP-1', mfg='X', model='Y', serial='1')
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [live]))
    # Rebuild combo with one real entry
    sb._refresh_combo_items()
    sb._screen_combo.setCurrentIndex(0)

    set_spy = mocker.patch.object(tmp_config, 'set')
    mocker.patch('thermalcanary.settings.SettingsSidebar._refresh_combo_items')

    sb._save_default_monitor()

    keys_set = [c.args[0] for c in set_spy.call_args_list]
    assert 'default_screen_index' in keys_set
    assert 'default_screen_uuid' in keys_set


def test_save_default_monitor_invalid_index(qtbot, tmp_config, mocker):
    """When combo index is out of bounds for the live screen list, must not crash."""
    sb = _make_sidebar(qtbot, tmp_config, mocker)
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: []))  # no screens
    mocker.patch('thermalcanary.settings.SettingsSidebar._refresh_combo_items')

    sb._save_default_monitor()  # should not raise


# ---------------------------------------------------------------------------
# _premium_dialog
# ---------------------------------------------------------------------------

def test_premium_dialog_returns_dlg_wrap_title(qtbot, tmp_config, mocker):
    sb = _make_sidebar(qtbot, tmp_config, mocker)
    dlg, wrap, title = sb._premium_dialog('Test Title')
    qtbot.addWidget(dlg)
    assert title.text() == 'Test Title'
    assert dlg.isModal()


# ---------------------------------------------------------------------------
# _show_about
# ---------------------------------------------------------------------------

def test_show_about_opens_about_dialog(qtbot, tmp_config, mocker):
    sb = _make_sidebar(qtbot, tmp_config, mocker)
    mocker.patch('thermalcanary.app.AboutDialog.exec', return_value=QDialog.DialogCode.Accepted)
    mocker.patch('thermalcanary.app.AboutDialog.adjustSize')
    mocker.patch('thermalcanary.app.AboutDialog.move')
    # Must not raise
    sb._show_about()


# ---------------------------------------------------------------------------
# _reset — cancel path
# ---------------------------------------------------------------------------

def test_reset_cancel_does_not_change_config(qtbot, tmp_config, mocker):
    sb = _make_sidebar(qtbot, tmp_config, mocker)
    mocker.patch('PyQt6.QtWidgets.QDialog.exec',
                 return_value=QDialog.DialogCode.Rejected)
    set_spy = mocker.patch.object(tmp_config, 'set')

    sb._reset()

    set_spy.assert_not_called()


# ---------------------------------------------------------------------------
# _reset — accept path
# ---------------------------------------------------------------------------

def test_reset_accept_restores_defaults(qtbot, tmp_config, mocker):
    from thermalcanary.config import DEFAULTS
    sb = _make_sidebar(qtbot, tmp_config, mocker)

    # Set some non-default values so we can verify reset
    tmp_config.set('poll_ms', 5000)
    tmp_config.set('smooth_n', 10)
    # _reset reads default_screen_index to preserve it; must be a valid int
    tmp_config.set('default_screen_index', 0)

    mocker.patch('PyQt6.QtWidgets.QDialog.exec',
                 return_value=QDialog.DialogCode.Accepted)
    mocker.patch('PyQt6.QtWidgets.QDialog.adjustSize')
    mocker.patch('PyQt6.QtWidgets.QDialog.move')

    sb._reset()

    assert tmp_config.get('poll_ms') == DEFAULTS['poll_ms']
    assert tmp_config.get('smooth_n') == DEFAULTS['smooth_n']


# ---------------------------------------------------------------------------
# _reset_gpu_detection — no GPU branch
# ---------------------------------------------------------------------------

def test_reset_gpu_detection_no_gpu(qtbot, tmp_config, mocker):
    sb = _make_sidebar(qtbot, tmp_config, mocker)

    mocker.patch('thermalcanary.first_run._detect_gpus', return_value=[])
    mocker.patch('PyQt6.QtWidgets.QDialog.exec',
                 return_value=QDialog.DialogCode.Accepted)
    mocker.patch('PyQt6.QtWidgets.QDialog.adjustSize')
    mocker.patch('PyQt6.QtWidgets.QDialog.move')

    # With no GPU, config should NOT be updated
    set_spy = mocker.patch.object(tmp_config, 'set')
    sb._reset_gpu_detection()
    keys_set = [c.args[0] for c in set_spy.call_args_list]
    assert 'gpu_backend' not in keys_set


def test_reset_gpu_detection_single_gpu_writes_config(qtbot, tmp_config, mocker):
    sb = _make_sidebar(qtbot, tmp_config, mocker)

    gpus = [{'name': 'AMD RX 7800 XT', 'index': 0, 'backend': 'amdgpu'}]
    mocker.patch('thermalcanary.first_run._detect_gpus', return_value=gpus)
    mocker.patch('PyQt6.QtWidgets.QDialog.exec',
                 return_value=QDialog.DialogCode.Accepted)
    mocker.patch('PyQt6.QtWidgets.QDialog.adjustSize')
    mocker.patch('PyQt6.QtWidgets.QDialog.move')

    sb._reset_gpu_detection()

    assert tmp_config.get('gpu_backend') == 'amdgpu'
    assert tmp_config.get('gpu_index') == 0


def test_reset_gpu_detection_multi_gpu(qtbot, tmp_config, mocker):
    sb = _make_sidebar(qtbot, tmp_config, mocker)

    gpus = [
        {'name': 'AMD RX 7800 XT', 'index': 0, 'backend': 'amdgpu'},
        {'name': 'NVIDIA RTX 4070', 'index': 0, 'backend': 'nvml'},
    ]
    mocker.patch('thermalcanary.first_run._detect_gpus', return_value=gpus)
    mocker.patch('PyQt6.QtWidgets.QDialog.exec',
                 return_value=QDialog.DialogCode.Accepted)
    mocker.patch('PyQt6.QtWidgets.QDialog.adjustSize')
    mocker.patch('PyQt6.QtWidgets.QDialog.move')

    # Multi-GPU: first_run_done set to False so the picker is shown next launch
    sb._reset_gpu_detection()
    assert tmp_config.get('first_run_done') is False


# ---------------------------------------------------------------------------
# _open_sensor_select (lines 375-397)
# ---------------------------------------------------------------------------

def test_open_sensor_select_creates_dialog(qtbot, tmp_config, mocker):
    sb = _make_sidebar(qtbot, tmp_config, mocker)
    mocker.patch('PyQt6.QtWidgets.QDialog.exec',
                 return_value=QDialog.DialogCode.Accepted)
    mocker.patch('PyQt6.QtWidgets.QDialog.adjustSize')
    mocker.patch('PyQt6.QtWidgets.QDialog.move')

    # Must not raise — exercises the full dialog build path
    sb._open_sensor_select()


# ---------------------------------------------------------------------------
# ColorButton._pick (lines 27-30)
# ---------------------------------------------------------------------------

def test_color_button_pick_valid_color(qtbot, mocker):
    from PyQt6.QtGui import QColor
    from thermalcanary.settings import ColorButton
    btn = ColorButton('#252040')
    qtbot.addWidget(btn)

    new_color = QColor('#7c6ef5')
    new_color_valid = MagicMock()
    new_color_valid.isValid.return_value = True
    new_color_valid.name.return_value = '#7c6ef5'
    mocker.patch('thermalcanary.settings.QColorDialog.getColor',
                 return_value=new_color_valid)

    colors_emitted = []
    btn.color_changed.connect(colors_emitted.append)
    btn._pick()

    assert colors_emitted == ['#7c6ef5']
    assert btn._hex == '#7c6ef5'


def test_color_button_pick_cancelled(qtbot, mocker):
    from thermalcanary.settings import ColorButton
    btn = ColorButton('#252040')
    qtbot.addWidget(btn)

    invalid = MagicMock()
    invalid.isValid.return_value = False
    mocker.patch('thermalcanary.settings.QColorDialog.getColor', return_value=invalid)

    colors_emitted = []
    btn.color_changed.connect(colors_emitted.append)
    btn._pick()

    assert colors_emitted == []  # cancelled → no signal
    assert btn._hex == '#252040'  # unchanged
