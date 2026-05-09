from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget

from thermalcanary.tray import TrayController


def test_toggle_hides_visible_window(tmp_config, mocker, qtbot):
    mocker.patch(
        "PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable",
        return_value=True,
    )
    window = QWidget()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    tray = TrayController(window, QIcon(), tmp_config)
    tray._toggle()

    assert not window.isVisible()


def test_no_tray_sets_tray_none(tmp_config, mocker, qtbot):
    mocker.patch(
        "PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable",
        return_value=False,
    )
    tmp_config.set("tray_warning_shown", True)
    window = QWidget()
    qtbot.addWidget(window)

    tray = TrayController(window, QIcon(), tmp_config)

    assert tray.tray is None


def test_update_menu_label_hide_when_visible(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    window.show()
    tray = TrayController(window, QIcon(), tmp_config)
    tray.update_menu_label()
    assert tray._show_action.text() == 'Hide'


def test_update_menu_label_show_when_hidden(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    tray = TrayController(window, QIcon(), tmp_config)
    tray._user_hidden = True
    tray.update_menu_label()
    assert tray._show_action.text() == 'Show'


def test_update_menu_label_noop_when_no_tray(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=False)
    tmp_config.set("tray_warning_shown", True)
    window = QWidget()
    qtbot.addWidget(window)
    tray = TrayController(window, QIcon(), tmp_config)
    tray.update_menu_label()   # must not raise


def test_on_activate_trigger_toggles(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    window.show()
    tray = TrayController(window, QIcon(), tmp_config)
    from PyQt6.QtWidgets import QSystemTrayIcon
    tray._on_activate(QSystemTrayIcon.ActivationReason.Trigger)
    assert not window.isVisible()


def test_on_activate_non_trigger_ignored(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    window.show()
    tray = TrayController(window, QIcon(), tmp_config)
    from PyQt6.QtWidgets import QSystemTrayIcon
    tray._on_activate(QSystemTrayIcon.ActivationReason.DoubleClick)
    assert window.isVisible()


def test_about_callback_stored(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    on_about = lambda: None
    tray = TrayController(window, QIcon(), tmp_config, on_about=on_about)
    assert tray._on_about is on_about


def test_toggle_shows_hidden_window(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    # place_on_screen is the real-window method that calls show(); simulate it
    window.place_on_screen = mocker.MagicMock(side_effect=window.show)
    tray = TrayController(window, QIcon(), tmp_config)
    tray._user_hidden = True
    window.hide()
    tray._toggle()
    window.place_on_screen.assert_called_once()
    assert window.isVisible()


# ---------------------------------------------------------------------------
# Mutation-killing: _show_no_tray_warning and __init__ tray branches
# ---------------------------------------------------------------------------

from PyQt6.QtWidgets import QDialog


def test_show_no_tray_warning_sets_tray_warning_shown(tmp_config, mocker, qtbot):
    # tray_warning_shown starts False → after construction with no tray it must be True
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=False)
    mocker.patch.object(QDialog, "exec", return_value=0)
    window = QWidget()
    qtbot.addWidget(window)
    tmp_config.set("tray_warning_shown", False)
    TrayController(window, QIcon(), tmp_config)
    assert tmp_config.get("tray_warning_shown") is True


def test_show_no_tray_warning_calls_exec_once(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=False)
    exec_mock = mocker.patch.object(QDialog, "exec", return_value=0)
    window = QWidget()
    qtbot.addWidget(window)
    tmp_config.set("tray_warning_shown", False)
    TrayController(window, QIcon(), tmp_config)
    exec_mock.assert_called_once()


def test_show_no_tray_warning_not_called_when_already_shown(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=False)
    exec_mock = mocker.patch.object(QDialog, "exec", return_value=0)
    window = QWidget()
    qtbot.addWidget(window)
    tmp_config.set("tray_warning_shown", True)
    TrayController(window, QIcon(), tmp_config)
    exec_mock.assert_not_called()


def test_tray_config_stored(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    tray = TrayController(window, QIcon(), tmp_config)
    assert tray._config is tmp_config


def test_tray_tooltip_is_thermal_canary(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    tray = TrayController(window, QIcon(), tmp_config)
    assert tray.tray.toolTip() == "Thermal Canary"


def test_tray_quit_callback_stored(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    on_quit = lambda: None
    tray = TrayController(window, QIcon(), tmp_config, on_quit=on_quit)
    assert tray._on_quit is on_quit


def test_tray_no_about_when_none(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    tray = TrayController(window, QIcon(), tmp_config, on_about=None)
    assert tray._on_about is None
    menu_texts = [a.text() for a in tray.tray.contextMenu().actions() if a.text()]
    assert "About" not in menu_texts


def test_tray_menu_has_quit_action(tmp_config, mocker, qtbot):
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=True)
    window = QWidget()
    qtbot.addWidget(window)
    tray = TrayController(window, QIcon(), tmp_config)
    menu_texts = [a.text() for a in tray.tray.contextMenu().actions() if a.text()]
    assert "Quit" in menu_texts


def test_tray_warning_shown_value_set_to_true_not_none(tmp_config, mocker, qtbot):
    # Mutation: config.set('tray_warning_shown', None) instead of True
    mocker.patch("PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable", return_value=False)
    mocker.patch.object(QDialog, "exec", return_value=0)
    window = QWidget()
    qtbot.addWidget(window)
    tmp_config.set("tray_warning_shown", False)
    TrayController(window, QIcon(), tmp_config)
    # must be True (bool), not None or any other truthy value
    assert tmp_config.get("tray_warning_shown") is True
