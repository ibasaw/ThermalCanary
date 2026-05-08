import uuid

from thermalcanary.screens import screen_uuid, find_index_by_uuid

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "thermal-canary")


def test_uuid_edid_path(make_qscreen):
    s = make_qscreen(mfg="DEL", model="U2722D", serial="XYZ123")
    result = screen_uuid(s)
    expected = str(uuid.uuid5(_NAMESPACE, "thermal-canary|edid|DEL|U2722D|XYZ123"))
    assert result == expected


def test_uuid_fallback_path(make_qscreen):
    s = make_qscreen(name="HDMI-1", mfg="", model="", serial="", w=527.0, h=296.0)
    result = screen_uuid(s)
    expected = str(uuid.uuid5(_NAMESPACE, "thermal-canary|fallback|HDMI-1|527.0x296.0"))
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
