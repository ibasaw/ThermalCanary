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
