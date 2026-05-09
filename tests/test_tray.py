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
    window.hide()
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
    window.hide()
    tray._toggle()
    window.place_on_screen.assert_called_once()
    assert window.isVisible()
