"""Headless regression tests for the sidebar's reactive screen handling.

These guard the Bug B fix: SettingsSidebar must NEVER cache the QApplication
screens list. Pre-fix, after a DPMS power-cycle the cache held wrapped-deleted
QScreen pointers and the next combo-pick crashed with
`RuntimeError: wrapped C/C++ object of type QScreen has been deleted`.

The full DPMS round-trip is exercised live in `/tmp/test_bug_b.py` via xrandr.
Here we drive the same code paths with mocked screens so CI catches a
regression without a desktop session.
"""
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

try:
    from thermalcanary.settings import SettingsSidebar
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

pytestmark = pytest.mark.skipif(not _HAS_SETTINGS, reason="settings module unavailable")


def _make_mock_screen(mocker, name, mfg="Acme", model="X", serial="S", w=527.0, h=296.0):
    from PyQt6.QtCore import QSizeF, QRect
    s = mocker.MagicMock()
    s.name.return_value = name
    s.manufacturer.return_value = mfg
    s.model.return_value = model
    s.serialNumber.return_value = serial
    s.physicalSize.return_value = QSizeF(w, h)
    s.availableGeometry.return_value = QRect(0, 0, 1920, 1080)
    return s


def test_sidebar_does_not_cache_screens_attr(qtbot, tmp_config):
    """Smoke regression: the cached `_screens` attribute must not exist —
    every screen lookup goes through the live `_current_screens()` helper.
    A reintroduced cache would silently hold dangling pointers post-DPMS."""
    sb = SettingsSidebar(tmp_config, worker=MagicMock())
    qtbot.addWidget(sb)
    assert not hasattr(sb, '_screens'), \
        "Sidebar must not cache QApplication.screens() — see Bug B."


def test_current_screens_returns_live_list(qtbot, tmp_config, mocker):
    """`_current_screens()` must call into QApplication every time, so its
    result reflects the topology at call-time, not at sidebar construction."""
    sb = SettingsSidebar(tmp_config, worker=MagicMock())
    qtbot.addWidget(sb)
    # Construction-time list:
    before = sb._current_screens()
    # Patch QApplication.instance().screens() to a sentinel:
    sentinel = [_make_mock_screen(mocker, 'PHANTOM')]
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: sentinel))
    after = sb._current_screens()
    assert after == sentinel
    assert after != before


def test_combo_pick_uses_live_screens_not_construction_snapshot(qtbot, tmp_config, mocker):
    """Bug B core regression: when the user changes the combo selection AFTER
    a DPMS event swapped out the screens, the on-change handler must derive
    the uuid from the LIVE QScreen, not a stale snapshot taken in __init__."""
    from thermalcanary.screens import screen_uuid

    sb = SettingsSidebar(tmp_config, worker=MagicMock())
    qtbot.addWidget(sb)

    # Simulate Mutter destroying + recreating QScreens — new pointers, new uuids.
    new_a = _make_mock_screen(mocker, 'DP-99', 'NewVendor', 'A', 'FIRST')
    new_b = _make_mock_screen(mocker, 'DP-98', 'NewVendor', 'B', 'SECOND')
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [new_a, new_b]))

    # Rebuild combo from the live (swapped) list, then pick index 1 (must
    # differ from the construction-time selection so the changed signal fires).
    # `_on_screens_changed` debounces via QTimer.singleShot(50, ...) to coalesce
    # Mutter's 3-5x burst during DPMS recovery — pump the event loop until the
    # pending flag clears so the rebuild has actually run.
    sb._on_screens_changed()
    qtbot.waitUntil(lambda: not sb._screen_refresh_pending, timeout=500)
    sb._screen_combo.setCurrentIndex(1)

    # The uuid written into config must match the LIVE screen, not whatever
    # was captured at construction time.
    expected = screen_uuid(new_b)
    assert tmp_config.get('screen_uuid') == expected


def test_screens_changed_preserves_selection_by_uuid(qtbot, tmp_config, mocker):
    """When the topology changes but the previously-selected monitor is still
    present, the combo must re-select it by UUID — not snap to index 0."""
    from thermalcanary.screens import screen_uuid

    s0 = _make_mock_screen(mocker, 'eDP-1',  'LG',   'lap', 'L')
    s1 = _make_mock_screen(mocker, 'HDMI-1', 'Dell', 'ext', 'E')

    # Sidebar is built with both screens visible.
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [s0, s1]))
    sb = SettingsSidebar(tmp_config, worker=MagicMock())
    qtbot.addWidget(sb)

    # User had picked the external monitor (idx 1).
    tmp_config.set('screen_uuid', screen_uuid(s1))

    # Now Qt reorders — same screens, different indices.
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [s1, s0]))
    sb._on_screens_changed()
    qtbot.waitUntil(lambda: not sb._screen_refresh_pending, timeout=500)

    # External monitor is now at idx 0 — the combo must reflect that, not
    # cling to the stale numeric index.
    assert sb._screen_combo.currentIndex() == 0


def test_refresh_combo_items_after_dpms_no_dangling_pointer(qtbot, tmp_config, mocker):
    """The combo rebuild path must call `_suuid(s)` / `s.name()` / etc on
    LIVE screens. Pre-fix it iterated `self._screens` and crashed with
    `wrapped C/C++ object of type QScreen has been deleted` once Mutter
    invalidated those pointers."""
    s_before = _make_mock_screen(mocker, 'DP-1')
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [s_before]))
    sb = SettingsSidebar(tmp_config, worker=MagicMock())
    qtbot.addWidget(sb)

    # Simulate Mutter destroying the QScreen: make any access to the old
    # mock raise the same RuntimeError PyQt raises on deleted C++ objects.
    s_before.name.side_effect = RuntimeError(
        "wrapped C/C++ object of type QScreen has been deleted")
    s_before.manufacturer.side_effect = s_before.name.side_effect
    s_before.availableGeometry.side_effect = s_before.name.side_effect

    s_after = _make_mock_screen(mocker, 'DP-1-new')
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [s_after]))

    # If the sidebar still touched the old cached screen, this raises.
    sb._refresh_combo_items()
    assert sb._screen_combo.count() == 1


def test_save_default_monitor_uses_live_screens(qtbot, tmp_config, mocker):
    """`_save_default_monitor` must write the uuid of the LIVE selected
    screen — not whatever was at that index at construction time."""
    from thermalcanary.screens import screen_uuid

    sb = SettingsSidebar(tmp_config, worker=MagicMock())
    qtbot.addWidget(sb)

    swapped = _make_mock_screen(mocker, 'DP-7', 'Vendor', 'M', 'NEW')
    mocker.patch('thermalcanary.settings.QApplication.instance',
                 return_value=MagicMock(screens=lambda: [swapped]))
    sb._on_screens_changed()
    qtbot.waitUntil(lambda: not sb._screen_refresh_pending, timeout=500)
    sb._screen_combo.setCurrentIndex(0)
    sb._save_default_monitor()

    assert tmp_config.get('default_screen_uuid') == screen_uuid(swapped)
    assert tmp_config.get('default_screen_index') == 0


def test_dpms_burst_is_coalesced_into_single_rebuild(qtbot, tmp_config, mocker):
    """Mutter fires geometryChanged 3-5x within <100ms during DPMS power-on.
    The 50ms debounce in `_on_screens_changed` must coalesce that burst into
    exactly ONE call to `_do_screens_changed` — otherwise the combo flickers
    and blockSignals races can drop the user's selection."""
    sb = SettingsSidebar(tmp_config, worker=MagicMock())
    qtbot.addWidget(sb)

    # Spy AFTER construction so we only count post-construction rebuilds.
    spy = mocker.spy(sb, '_do_screens_changed')

    # Simulate Mutter's burst: 5 rapid calls in the same event-loop tick.
    for _ in range(5):
        sb._on_screens_changed()

    # All 5 calls land before the 50ms timer fires, so only the first sets
    # the pending flag — the other 4 short-circuit.
    assert sb._screen_refresh_pending is True
    assert spy.call_count == 0  # nothing has rebuilt yet

    # Drain the debounce timer.
    qtbot.waitUntil(lambda: not sb._screen_refresh_pending, timeout=500)

    # Exactly one rebuild from the burst, despite 5 trigger calls.
    assert spy.call_count == 1
