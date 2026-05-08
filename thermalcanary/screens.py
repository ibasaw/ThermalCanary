"""Stable per-monitor UUID resolution.

Identifies monitors by EDID properties (manufacturer/model/serial) when
available, falling back to connector name + physical size. Survives reboots,
cable swaps, and Qt screen re-ordering.
"""
from __future__ import annotations
import uuid
from PyQt6.QtGui import QScreen

# Derived from the project slug — self-documenting and reproducible.
# Do not change: altering this invalidates all persisted screen UUIDs.
_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "thermal-canary")


def screen_uuid(screen: QScreen) -> str:
    """Return a stable uuid5 string for a QScreen."""
    mfg    = (screen.manufacturer()   or "").strip()
    model  = (screen.model()          or "").strip()
    serial = (screen.serialNumber()   or "").strip()

    if mfg and model and serial:
        key = f"thermal-canary|edid|{mfg}|{model}|{serial}"
    else:
        size = screen.physicalSize()
        key  = f"thermal-canary|fallback|{screen.name()}|{size.width():.1f}x{size.height():.1f}"

    return str(uuid.uuid5(_NAMESPACE, key))


def find_index_by_uuid(screens: list[QScreen], target: str) -> int | None:
    """Return the current list index of the screen matching target, or None."""
    if not target:
        return None
    for i, s in enumerate(screens):
        if screen_uuid(s) == target:
            return i
    return None
