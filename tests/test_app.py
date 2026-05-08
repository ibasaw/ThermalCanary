import pytest
try:
    from thermalcanary.app import AboutDialog
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
