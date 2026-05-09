"""Stable per-monitor UUID resolution.

Each monitor gets a prefixed UUID: "thermal-canary-{uuid5}".
The key concatenates ALL stable identifiers (EDID + connector + physical size)
so even identical-model monitors with different serials are distinct.
No fallback branches — all fields always included, empty or not.

Format: thermal-canary-{uuid5 of "tc|v2|{mfg}|{model}|{serial}|{name}|{phys}"}

DO NOT change this format — it invalidates all persisted UUIDs.
"""
from __future__ import annotations
import uuid
from PyQt6.QtGui import QScreen

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "thermal-canary")
_PREFIX = "thermal-canary-"


def screen_uuid(screen: QScreen) -> str:
    """Return a prefixed stable UUID string for a QScreen.

    Example: "thermal-canary-ac1b7377-15e0-533a-bce6-d1682b037a0f"

    All stable fields are concatenated — mfg, model, serial (EDID),
    connector name, and physical size — so any differing field produces
    a different UUID.
    """
    mfg    = (screen.manufacturer()  or "").strip()
    model  = (screen.model()         or "").strip()
    serial = (screen.serialNumber()  or "").strip()
    name   = (screen.name()          or "").strip()
    size   = screen.physicalSize()
    phys   = f"{size.width():.1f}x{size.height():.1f}"

    key = f"tc|v2|{mfg}|{model}|{serial}|{name}|{phys}"
    return _PREFIX + str(uuid.uuid5(_NAMESPACE, key))


def find_index_by_uuid(screens: list[QScreen], target: str) -> int | None:
    """Return the Qt list index of the screen whose UUID matches target, or None."""
    if not target:
        return None
    for i, s in enumerate(screens):
        if screen_uuid(s) == target:
            return i
    return None
