import yaml
import pytest

from thermalcanary.config import Config, DEFAULTS


def test_defaults_when_no_file(tmp_config):
    for key, expected in DEFAULTS.items():
        assert tmp_config.get(key) == expected


def test_load_valid_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_file = tmp_path / "thermalcanary" / "config.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(yaml.safe_dump({"poll_ms": 2000, "smooth_n": 10}))
    cfg = Config()
    assert cfg.get("poll_ms") == 2000
    assert cfg.get("smooth_n") == 10


def test_load_invalid_value_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_file = tmp_path / "thermalcanary" / "config.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(yaml.safe_dump({"poll_ms": 50}))  # below minimum 100
    cfg = Config()
    assert cfg.get("poll_ms") == DEFAULTS["poll_ms"]


def test_load_invalid_hex_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_file = tmp_path / "thermalcanary" / "config.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(yaml.safe_dump({"bg_color": "notahex"}))
    cfg = Config()
    assert cfg.get("bg_color") == DEFAULTS["bg_color"]


def test_set_emits_changed_signal(tmp_config, qtbot):
    with qtbot.waitSignal(tmp_config.changed, timeout=500) as blocker:
        tmp_config.set("poll_ms", 2000)
    assert blocker.args == ["poll_ms"]


def test_set_same_value_no_signal(tmp_config, qtbot):
    with qtbot.assertNotEmitted(tmp_config.changed):
        tmp_config.set("poll_ms", DEFAULTS["poll_ms"])


def test_save_now_writes_yaml(tmp_config, tmp_path):
    tmp_config.set("poll_ms", 3000)
    tmp_config.save_now()
    data = yaml.safe_load((tmp_path / "thermalcanary" / "config.yaml").read_text())
    assert data["poll_ms"] == 3000


def test_unknown_yaml_key_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_file = tmp_path / "thermalcanary" / "config.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(yaml.safe_dump({"totally_unknown_key": 42}))
    cfg = Config()  # must not crash
    assert "totally_unknown_key" not in DEFAULTS


def test_clamp_uuid_match(tmp_config, make_qscreen):
    from thermalcanary.screens import screen_uuid
    s0 = make_qscreen("HDMI-1", "Dell", "U2722D", "SN001")
    s1 = make_qscreen("DP-1",   "LG",   "27GL83A", "SN002")
    uuid1 = screen_uuid(s1)
    tmp_config.set('default_screen_uuid', uuid1)
    tmp_config.clamp_screen_indices([s0, s1])
    assert tmp_config.get('screen_index') == 1


def test_clamp_index_fallback(tmp_config, make_qscreen):
    s0 = make_qscreen("HDMI-1")
    s1 = make_qscreen("DP-1")
    tmp_config.set('default_screen_uuid', None)
    tmp_config.set('default_screen_index', 1)
    tmp_config.clamp_screen_indices([s0, s1])
    assert tmp_config.get('screen_index') == 1
    assert tmp_config.get('default_screen_uuid') is not None


def test_clamp_defaults_to_zero(tmp_config, make_qscreen):
    s0 = make_qscreen("HDMI-1")
    tmp_config.set('default_screen_uuid', None)
    tmp_config.set('default_screen_index', None)
    tmp_config.clamp_screen_indices([s0])
    assert tmp_config.get('screen_index') == 0


def test_clamp_empty_screen_list_no_crash(tmp_config):
    tmp_config.clamp_screen_indices([])   # must not raise


def test_save_now_writes_without_debounce(tmp_config, tmp_path):
    tmp_config.set("smooth_n", 7)
    tmp_config.save_now()
    data = yaml.safe_load((tmp_path / "thermalcanary" / "config.yaml").read_text())
    assert data["smooth_n"] == 7


# --- security hardening tests ---

def _cfg_with_yaml(tmp_path, monkeypatch, data: dict) -> "Config":
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_file = tmp_path / "thermalcanary" / "config.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(yaml.safe_dump(data))
    return Config()


@pytest.mark.parametrize("v", ["card0", "card1", "card9", "card10", "card99"])
def test_gpu_card_valid(tmp_path, monkeypatch, v):
    cfg = _cfg_with_yaml(tmp_path, monkeypatch, {"gpu_card": v})
    assert cfg.get("gpu_card") == v


@pytest.mark.parametrize("v", ["card²", "card١", "card४"])
def test_gpu_card_rejects_unicode_digits(tmp_path, monkeypatch, v):
    cfg = _cfg_with_yaml(tmp_path, monkeypatch, {"gpu_card": v})
    assert cfg.get("gpu_card") == DEFAULTS["gpu_card"]


@pytest.mark.parametrize("v", ["card0/../../etc/passwd", "../evil", "card", "card0a", "card100"])
def test_gpu_card_rejects_bad_values(tmp_path, monkeypatch, v):
    cfg = _cfg_with_yaml(tmp_path, monkeypatch, {"gpu_card": v})
    assert cfg.get("gpu_card") == DEFAULTS["gpu_card"]


def test_cpu_temp_source_rejects_oversized(tmp_path, monkeypatch):
    cfg = _cfg_with_yaml(tmp_path, monkeypatch, {"cpu_temp_source": "x" * 128})
    assert cfg.get("cpu_temp_source") == DEFAULTS["cpu_temp_source"]


def test_cpu_temp_source_accepts_normal(tmp_path, monkeypatch):
    cfg = _cfg_with_yaml(tmp_path, monkeypatch, {"cpu_temp_source": "coretemp/Package id 0"})
    assert cfg.get("cpu_temp_source") == "coretemp/Package id 0"


def test_malformed_yaml_falls_back_to_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_file = tmp_path / "thermalcanary" / "config.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(": broken: yaml: {{{{")
    cfg = Config()
    for key, expected in DEFAULTS.items():
        assert cfg.get(key) == expected


def test_sysfs_env_ignored_without_test_flag(monkeypatch):
    from thermalcanary.amd import AmdGpuReader
    monkeypatch.delenv("THERMALCANARY_TEST", raising=False)
    monkeypatch.setenv("THERMALCANARY_SYSFS_ROOT", "/tmp/evil-path")
    r = AmdGpuReader(card="card0", sysfs_root=None)
    assert str(r._device).startswith("/sys/class/drm")


# ---------------------------------------------------------------------------
# New mutation-killing tests
# ---------------------------------------------------------------------------

def test_clamp_uuid_miss_default_index_in_range(tmp_config, make_qscreen):
    """UUID miss + default_screen_index in range → sets screen_index to that index."""
    s0 = make_qscreen("HDMI-1")
    s1 = make_qscreen("DP-1")
    tmp_config.set('default_screen_uuid', None)
    tmp_config.set('default_screen_index', 1)
    tmp_config.clamp_screen_indices([s0, s1])
    assert tmp_config.get('screen_index') == 1


def test_clamp_uuid_miss_default_index_out_of_range_falls_to_zero(tmp_config, make_qscreen):
    """UUID miss + default_screen_index >= n → falls back to index 0."""
    s0 = make_qscreen("HDMI-1")
    tmp_config.set('default_screen_uuid', None)
    tmp_config.set('default_screen_index', 5)  # out of range for a 1-screen list
    tmp_config.clamp_screen_indices([s0])
    assert tmp_config.get('screen_index') == 0


def test_clamp_uuid_miss_out_of_range_sets_default_index_to_zero(tmp_config, make_qscreen):
    """Fallback to index 0 must also update default_screen_index to 0."""
    s0 = make_qscreen("HDMI-1")
    tmp_config.set('default_screen_uuid', None)
    tmp_config.set('default_screen_index', 99)
    tmp_config.clamp_screen_indices([s0])
    assert tmp_config.get('default_screen_index') == 0


def test_clamp_uuid_miss_out_of_range_sets_default_uuid(tmp_config, make_qscreen):
    """Fallback to index 0 must record screen_uuid for screens[0]."""
    from thermalcanary.screens import screen_uuid
    s0 = make_qscreen("HDMI-1", "Dell", "U2722D", "SN000")
    tmp_config.set('default_screen_uuid', None)
    tmp_config.set('default_screen_index', 99)
    tmp_config.clamp_screen_indices([s0])
    assert tmp_config.get('default_screen_uuid') == screen_uuid(s0)


def test_clamp_empty_list_no_mutation(tmp_config):
    """Empty screen list → returns immediately, screen_index unchanged."""
    tmp_config._data['screen_index'] = 3
    tmp_config.clamp_screen_indices([])
    assert tmp_config.get('screen_index') == 3


def test_clamp_uuid_match_sets_screen_uuid(tmp_config, make_qscreen):
    """UUID match → screen_uuid field is refreshed to the matched screen."""
    from thermalcanary.screens import screen_uuid
    s0 = make_qscreen("HDMI-1", "Dell", "U2722D", "SN001")
    s1 = make_qscreen("DP-1",   "LG",   "27GL83A", "SN002")
    uuid1 = screen_uuid(s1)
    tmp_config.set('default_screen_uuid', uuid1)
    tmp_config.clamp_screen_indices([s0, s1])
    assert tmp_config.get('screen_uuid') == uuid1


def test_write_creates_tmp_then_replaces(tmp_config, tmp_path):
    """_write() must use .yaml.tmp and then rename to final path."""
    tmp_config.set('poll_ms', 4000)
    tmp_config.save_now()
    final = tmp_path / 'thermalcanary' / 'config.yaml'
    tmp_file = final.with_suffix('.yaml.tmp')
    assert final.exists()
    assert not tmp_file.exists()   # tmp was renamed away


def test_write_sets_chmod_600(tmp_config, tmp_path):
    """_write() must chmod the final file to 0o600."""
    import stat
    tmp_config.save_now()
    final = tmp_path / 'thermalcanary' / 'config.yaml'
    mode = stat.S_IMODE(final.stat().st_mode)
    assert mode == 0o600


def test_load_skips_value_failing_validator(tmp_path, monkeypatch):
    """_load() must reject values where validator(v) is False and keep default."""
    import yaml as _yaml
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_file = tmp_path / "thermalcanary" / "config.yaml"
    cfg_file.parent.mkdir(parents=True)
    # poll_ms validator requires 100 <= v <= 60000
    cfg_file.write_text(_yaml.safe_dump({"poll_ms": 99}))
    cfg = Config()
    assert cfg.get("poll_ms") == DEFAULTS["poll_ms"]


def test_load_accepts_value_passing_validator(tmp_path, monkeypatch):
    """_load() must store values where validator(v) is True."""
    import yaml as _yaml
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_file = tmp_path / "thermalcanary" / "config.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(_yaml.safe_dump({"poll_ms": 2500}))
    cfg = Config()
    assert cfg.get("poll_ms") == 2500


def test_save_timer_is_single_shot(tmp_config):
    """__init__ must configure save_timer as single-shot."""
    assert tmp_config._save_timer.isSingleShot()


def test_save_timer_interval_is_500ms(tmp_config):
    """__init__ must set save_timer interval to 500 ms."""
    assert tmp_config._save_timer.interval() == 500


def test_get_known_key_returns_value(tmp_config):
    """get() returns the stored value for a known key."""
    tmp_config._data['poll_ms'] = 3000
    assert tmp_config.get('poll_ms') == 3000


def test_load_skips_key_not_in_defaults(tmp_path, monkeypatch):
    """_load() silently ignores keys absent from DEFAULTS."""
    import yaml as _yaml
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_file = tmp_path / "thermalcanary" / "config.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text(_yaml.safe_dump({"no_such_key": 42}))
    cfg = Config()
    assert 'no_such_key' not in cfg._data


def test_clamp_default_index_equal_to_n_falls_to_zero(tmp_config, make_qscreen):
    """default_screen_index == n (boundary, out-of-range) → falls back to 0."""
    s0 = make_qscreen("HDMI-1")
    tmp_config.set('default_screen_uuid', None)
    tmp_config.set('default_screen_index', 1)  # exactly == n for a 1-screen list
    tmp_config.clamp_screen_indices([s0])
    assert tmp_config.get('screen_index') == 0


# ---------------------------------------------------------------------------
# Mutation-killing: _is_screen, _is_uuid5, _is_hex validators
# ---------------------------------------------------------------------------

from thermalcanary.config import _is_screen, _is_uuid5, _is_hex


@pytest.mark.parametrize("v", [0, 1, 15, 31])
def test_is_screen_valid(v):
    assert _is_screen(v) is True


@pytest.mark.parametrize("v", [32, -1, 33, 100])
def test_is_screen_invalid_out_of_range(v):
    assert _is_screen(v) is False


@pytest.mark.parametrize("v", [1.0, "0", None, [1]])
def test_is_screen_invalid_type(v):
    assert _is_screen(v) is False


def test_is_screen_boundary_zero():
    assert _is_screen(0) is True


def test_is_screen_boundary_31():
    assert _is_screen(31) is True


def test_is_screen_boundary_32_excluded():
    assert _is_screen(32) is False


def test_is_screen_boundary_minus1_excluded():
    assert _is_screen(-1) is False


def test_is_uuid5_none_is_valid():
    assert _is_uuid5(None) is True


def test_is_uuid5_valid_format():
    v = "thermal-canary-550e8400-e29b-5bcd-a716-446655440000"
    assert _is_uuid5(v) is True


def test_is_uuid5_invalid_prefix():
    assert _is_uuid5("something-else-550e8400-e29b-5bcd-a716-446655440000") is False


def test_is_uuid5_version4_rejected():
    # Third group must start with 5 for uuid5
    v = "thermal-canary-550e8400-e29b-4bcd-a716-446655440000"
    assert _is_uuid5(v) is False


def test_is_uuid5_invalid_type():
    assert _is_uuid5(42) is False
    assert _is_uuid5(True) is False


def test_is_uuid5_empty_string():
    assert _is_uuid5("") is False


def test_is_hex_valid_lowercase():
    assert _is_hex("#aabbcc") is True


def test_is_hex_valid_uppercase():
    assert _is_hex("#AABBCC") is True


def test_is_hex_valid_mixed():
    assert _is_hex("#aAbBcC") is True


def test_is_hex_missing_hash():
    assert _is_hex("aabbcc") is False


def test_is_hex_too_short():
    assert _is_hex("#aabbc") is False


def test_is_hex_too_long():
    assert _is_hex("#aabbccd") is False


def test_is_hex_invalid_chars():
    assert _is_hex("#xxyyzz") is False


def test_is_hex_invalid_type():
    assert _is_hex(None) is False
    assert _is_hex(123456) is False
