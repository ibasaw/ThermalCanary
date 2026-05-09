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
