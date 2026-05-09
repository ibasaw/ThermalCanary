import uuid

from thermalcanary.screens import screen_uuid, find_index_by_uuid

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "thermal-canary")
_PREFIX = "thermal-canary-"


def test_uuid_all_fields_path(make_qscreen):
    # mfg/model/serial present; name and phys use fixture defaults (DP-1, 527x296)
    s = make_qscreen(mfg="DEL", model="U2722D", serial="XYZ123")
    result = screen_uuid(s)
    key = "tc|v2|DEL|U2722D|XYZ123|DP-1|527.0x296.0"
    expected = _PREFIX + str(uuid.uuid5(_NAMESPACE, key))
    assert result == expected


def test_uuid_empty_edid_fields(make_qscreen):
    # empty mfg/model/serial — all fields still concatenated, no separate fallback branch
    s = make_qscreen(name="HDMI-1", mfg="", model="", serial="", w=527.0, h=296.0)
    result = screen_uuid(s)
    key = "tc|v2||||HDMI-1|527.0x296.0"
    expected = _PREFIX + str(uuid.uuid5(_NAMESPACE, key))
    assert result == expected
    assert screen_uuid(s) == result  # stable across calls


def test_find_index_by_uuid_correct(make_qscreen):
    screens = [
        make_qscreen(name="DP-1", mfg="A", model="M1", serial="S1"),
        make_qscreen(name="DP-2", mfg="B", model="M2", serial="S2"),
        make_qscreen(name="DP-3", mfg="C", model="M3", serial="S3"),
    ]
    for i, s in enumerate(screens):
        assert find_index_by_uuid(screens, screen_uuid(s)) == i


def test_find_index_by_uuid_none_cases(make_qscreen):
    screens = [make_qscreen(name="DP-1", mfg="A", model="M1", serial="S1")]
    assert find_index_by_uuid(screens, "00000000-0000-5000-0000-000000000000") is None
    assert find_index_by_uuid(screens, None) is None
    assert find_index_by_uuid([], screen_uuid(screens[0])) is None


# ---------------------------------------------------------------------------
# New mutation-killing tests
# ---------------------------------------------------------------------------

def test_screen_uuid_starts_with_prefix(make_qscreen):
    """screen_uuid() must return a string starting with 'thermal-canary-'."""
    s = make_qscreen()
    result = screen_uuid(s)
    assert result.startswith("thermal-canary-")


def test_screen_uuid_is_deterministic(make_qscreen):
    """screen_uuid() is deterministic — same screen produces same UUID."""
    s = make_qscreen(name="DP-1", mfg="Dell", model="U2722D", serial="SN123")
    assert screen_uuid(s) == screen_uuid(s)


def test_screen_uuid_uses_uuid5_not_uuid4(make_qscreen):
    """UUID portion must be a v5 UUID (version nibble = 5)."""
    s = make_qscreen(name="DP-1", mfg="Dell", model="U2722D", serial="SN999")
    result = screen_uuid(s)
    uid_part = result[len("thermal-canary-"):]
    parsed = uuid.UUID(uid_part)
    assert parsed.version == 5


def test_screen_uuid_different_for_different_serials(make_qscreen):
    """Two otherwise identical screens with different serials must get different UUIDs."""
    s1 = make_qscreen(name="DP-1", mfg="Dell", model="U2722D", serial="SN001")
    s2 = make_qscreen(name="DP-1", mfg="Dell", model="U2722D", serial="SN002")
    assert screen_uuid(s1) != screen_uuid(s2)


def test_screen_uuid_physical_size_with_one_decimal(make_qscreen):
    """Key must format physical size with exactly 1 decimal place."""
    import re
    s = make_qscreen(w=600.0, h=340.0)
    result = screen_uuid(s)
    # Reconstruct key and verify it contains correctly formatted size
    key = f"tc|v2||||DP-1|600.0x340.0"
    expected = _PREFIX + str(uuid.uuid5(_NAMESPACE, key))
    assert result == expected


def test_screen_uuid_pipe_separator_format(make_qscreen):
    """Key uses '|' separators and starts with 'tc|v2|'."""
    s = make_qscreen(name="HDMI-1", mfg="LG", model="27GL83A", serial="XY42")
    result = screen_uuid(s)
    expected_key = "tc|v2|LG|27GL83A|XY42|HDMI-1|527.0x296.0"
    expected = _PREFIX + str(uuid.uuid5(_NAMESPACE, expected_key))
    assert result == expected


def test_screen_uuid_uses_correct_namespace(make_qscreen):
    """The namespace must be uuid5(NAMESPACE_DNS, 'thermal-canary'), not uuid4."""
    s = make_qscreen(name="DP-2", mfg="A", model="B", serial="C", w=600.0, h=340.0)
    result = screen_uuid(s)
    key = "tc|v2|A|B|C|DP-2|600.0x340.0"
    # Verify with wrong namespace gives a different result
    wrong_ns = uuid.uuid5(uuid.NAMESPACE_DNS, "wrong-canary")
    wrong = _PREFIX + str(uuid.uuid5(wrong_ns, key))
    assert result != wrong
