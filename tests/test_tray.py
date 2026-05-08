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

    tray = TrayController(window, "", tmp_config)
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

    tray = TrayController(window, "", tmp_config)

    assert tray.tray is None
