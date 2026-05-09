import pytest
try:
    from thermalcanary.app import AboutDialog, QuitDialog, GaugeArea, _contrast_color
    _HAS_APP = True
except ImportError:
    _HAS_APP = False

pytestmark = pytest.mark.skipif(not _HAS_APP, reason="thermalcanary.app not in mutmut sandbox")


def test_about_dialog_creates(qtbot):
    dlg = AboutDialog()
    qtbot.addWidget(dlg)
    assert dlg is not None


def test_about_dialog_shows_version(qtbot):
    from thermalcanary import __version__
    from PyQt6.QtWidgets import QLabel
    dlg = AboutDialog()
    qtbot.addWidget(dlg)
    labels = dlg.findChildren(QLabel)
    texts = [l.text() for l in labels]
    assert any(f'v{__version__}' in t for t in texts)


def test_about_dialog_close_button_accepts(qtbot):
    from PyQt6.QtWidgets import QPushButton
    dlg = AboutDialog()
    qtbot.addWidget(dlg)
    buttons = dlg.findChildren(QPushButton)
    close_btn = next(b for b in buttons if b.text() == 'Close')
    with qtbot.waitSignal(dlg.accepted, timeout=500):
        close_btn.click()


def test_quit_dialog_creates(qtbot):
    dlg = QuitDialog()
    qtbot.addWidget(dlg)
    assert dlg is not None


def test_quit_dialog_cancel_rejects(qtbot):
    from PyQt6.QtWidgets import QPushButton
    dlg = QuitDialog()
    qtbot.addWidget(dlg)
    cancel = next(b for b in dlg.findChildren(QPushButton) if b.text() == 'Cancel')
    with qtbot.waitSignal(dlg.rejected, timeout=500):
        cancel.click()


def test_quit_dialog_quit_accepts(qtbot):
    from PyQt6.QtWidgets import QPushButton
    dlg = QuitDialog()
    qtbot.addWidget(dlg)
    quit_btn = next(b for b in dlg.findChildren(QPushButton) if b.text() == 'Quit')
    with qtbot.waitSignal(dlg.accepted, timeout=500):
        quit_btn.click()


def test_contrast_color_dark_background():
    c = _contrast_color('#252040')
    assert c.name() == '#ffffff'


def test_contrast_color_light_background():
    c = _contrast_color('#f0f0f0')
    assert c.name() == '#1a1a1a'


def test_gauge_area_creates(qtbot, tmp_config):
    area = GaugeArea(tmp_config)
    qtbot.addWidget(area)
    assert area is not None
