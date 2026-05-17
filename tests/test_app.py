import pytest
try:
    from thermalcanary.app import AboutDialog, QuitDialog, GaugeArea, _contrast_color, ThermalCanary
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


# ---------------------------------------------------------------------------
# Bug A/B fix: generation counter + settle-timer guards
# ---------------------------------------------------------------------------
# These tests bypass ThermalCanary's heavy __init__ (SensorWorker thread, tray,
# sidebar) and test the new placement guards in isolation. Each test sets only
# the attributes the method under test reads — anything else is a mock.

from unittest.mock import MagicMock
from PyQt6.QtCore import QTimer


def _bare_tc():
    """Build a ThermalCanary without invoking __init__. Set only what each
    test needs. This is the standard isolation pattern for testing methods
    on a heavyweight QObject without paying for its construction."""
    return ThermalCanary.__new__(ThermalCanary)


def test_apply_pending_move_if_any_aborts_on_stale_generation(mocker):
    """Delayed callbacks captured a generation number when scheduled. If the
    topology has since changed (generation bumped), the callback must abort
    instead of dereferencing a now-stale QScreen pointer."""
    tc = _bare_tc()
    tc._move_generation = 5
    tc._pending_target_geo = MagicMock()  # non-None: would normally trigger move
    tc._pending_target_screen = MagicMock()
    apply_spy = mocker.patch.object(tc, '_apply_pending_move')

    # Schedule-time generation was 4; current is 5 → stale → no-op.
    tc._apply_pending_move_if_any(gen=4)
    apply_spy.assert_not_called()


def test_apply_pending_move_if_any_runs_when_generation_current(mocker):
    """Generation matches → the move proceeds normally."""
    tc = _bare_tc()
    tc._move_generation = 5
    tc._pending_target_geo = MagicMock()
    tc._pending_target_screen = MagicMock()
    apply_spy = mocker.patch.object(tc, '_apply_pending_move')

    tc._apply_pending_move_if_any(gen=5)
    apply_spy.assert_called_once()


def test_apply_pending_move_if_any_no_gen_arg_preserves_legacy_path(mocker):
    """Internal callers in _move_to_screen pass no gen — legacy behavior must
    still run when there's a pending target."""
    tc = _bare_tc()
    tc._move_generation = 5
    tc._pending_target_geo = MagicMock()
    tc._pending_target_screen = MagicMock()
    apply_spy = mocker.patch.object(tc, '_apply_pending_move')

    tc._apply_pending_move_if_any()  # no gen
    apply_spy.assert_called_once()


def test_retry_move_aborts_on_stale_generation(mocker):
    """The 50ms windowHandle-retry must abort if a DPMS event bumped the
    generation underneath it."""
    tc = _bare_tc()
    tc._move_generation = 7
    move_spy = mocker.patch.object(tc, '_move_to_screen')

    tc._retry_move(idx=1, gen=6)
    move_spy.assert_not_called()


def test_retry_move_runs_when_generation_current(mocker):
    tc = _bare_tc()
    tc._move_generation = 7
    move_spy = mocker.patch.object(tc, '_move_to_screen')

    tc._retry_move(idx=1, gen=7)
    move_spy.assert_called_once_with(1)


def test_place_on_screen_if_current_aborts_on_stale_generation(mocker):
    """The settle handler's 0ms deferred place must abort if generation moved
    again before Qt drained the event queue."""
    tc = _bare_tc()
    tc._move_generation = 3
    place_spy = mocker.patch.object(tc, 'place_on_screen')

    tc._place_on_screen_if_current(gen=2)
    place_spy.assert_not_called()


def test_place_on_screen_if_current_runs_when_generation_current(mocker):
    tc = _bare_tc()
    tc._move_generation = 3
    place_spy = mocker.patch.object(tc, 'place_on_screen')

    tc._place_on_screen_if_current(gen=3)
    place_spy.assert_called_once()


def test_on_config_changed_skips_screen_move_while_settling(mocker, tmp_config):
    """Bug A regression guard: a screen_uuid write that lands while the settle
    timer is active must NOT trigger an immediate move — the settle handler
    will place the window using the freshly clamped config once the topology
    is stable. Without this skip, the move races the settle handler and may
    target a transient (mid-wake) QScreen."""
    tc = _bare_tc()
    tc._config = tmp_config
    tc._gauges = []
    tc._gauge_area = MagicMock()
    tc._worker = MagicMock()
    tc._screens_settle_timer = QTimer()
    tc._screens_settle_timer.setSingleShot(True)
    tc._screens_settle_timer.start(60_000)  # long: certainly active
    move_spy = mocker.patch.object(tc, '_move_to_screen_by_uuid')

    tc._on_config_changed('screen_uuid')

    move_spy.assert_not_called()
    tc._screens_settle_timer.stop()


def test_on_config_changed_runs_screen_move_when_settled(mocker, tmp_config):
    """Inverse of the above: when the settle timer is idle (the topology has
    stabilized or no DPMS event is in flight), a screen_uuid change from the
    sidebar combo must fire the move immediately."""
    tc = _bare_tc()
    tc._config = tmp_config
    tc._gauges = []
    tc._gauge_area = MagicMock()
    tc._worker = MagicMock()
    tc._screens_settle_timer = QTimer()
    tc._screens_settle_timer.setSingleShot(True)
    # Timer not started → not active.
    move_spy = mocker.patch.object(tc, '_move_to_screen_by_uuid')

    tmp_config.set('screen_uuid', 'thermal-canary-550e8400-e29b-5bcd-a716-446655440000')
    tc._on_config_changed('screen_uuid')

    move_spy.assert_called_once()


def test_handle_screens_settled_bumps_generation_and_clears_pending(mocker, tmp_config):
    """Settle handler must invalidate in-flight moves so a callback scheduled
    against the OLD topology cannot complete. It bumps the generation and
    clears the pending-target latches."""
    tc = _bare_tc()
    tc._config = tmp_config
    tc._move_generation = 10
    tc._pending_target_geo = MagicMock()
    tc._pending_target_screen = MagicMock()
    mocker.patch.object(tmp_config, 'clamp_screen_indices')
    # The deferred QTimer fires under pytest-qt's event loop — patch it so we
    # don't reach place_on_screen() on this bare instance.
    mocker.patch.object(tc, '_place_on_screen_if_current')

    tc._handle_screens_settled()

    assert tc._move_generation == 11
    assert tc._pending_target_geo is None
    assert tc._pending_target_screen is None


def test_handle_screens_settled_no_screens_early_return(mocker, tmp_config):
    """If Qt reports zero screens (transient mid-cycle state), settle handler
    must early-return without bumping generation or touching pending state."""
    tc = _bare_tc()
    tc._config = tmp_config
    tc._move_generation = 10
    tc._pending_target_geo = 'sentinel-geo'
    tc._pending_target_screen = 'sentinel-screen'
    mocker.patch('thermalcanary.app.QApplication.instance', return_value=MagicMock(screens=lambda: []))
    clamp_spy = mocker.patch.object(tmp_config, 'clamp_screen_indices')

    tc._handle_screens_settled()

    assert tc._move_generation == 10
    assert tc._pending_target_geo == 'sentinel-geo'
    assert tc._pending_target_screen == 'sentinel-screen'
    clamp_spy.assert_not_called()
