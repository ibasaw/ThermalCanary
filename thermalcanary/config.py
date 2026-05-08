import os
import re
import sys
import yaml
from pathlib import Path
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

_HEX = re.compile(r'^#[0-9a-fA-F]{6}$')

def _is_hex(v): return isinstance(v, str) and bool(_HEX.match(v))
def _is_screen(v): return isinstance(v, int) and 0 <= v < 32

_UUID5_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$')
def _is_uuid5(v): return v is None or (isinstance(v, str) and bool(_UUID5_RE.match(v)))

_VALIDATORS = {
    'screen_index':         _is_screen,
    'default_screen_index': lambda v: v is None or _is_screen(v),
    'screen_uuid':          _is_uuid5,
    'default_screen_uuid':  _is_uuid5,
    'poll_ms':              lambda v: isinstance(v, int) and 100 <= v <= 60000,
    'smooth_n':             lambda v: isinstance(v, int) and 1 <= v <= 100,
    'panel_radius':         lambda v: isinstance(v, int) and 0 <= v <= 100,
    'bg_color':             _is_hex,
    'inner_color':          _is_hex,
    'track_color':          _is_hex,
    'tick_color':           _is_hex,
    'tray_minimize_to_tray': lambda v: isinstance(v, bool),
    'tray_warning_shown':    lambda v: isinstance(v, bool),
    'first_run_done':        lambda v: isinstance(v, bool),
    'gpu_index':             lambda v: isinstance(v, int) and 0 <= v < 32,
    'gpu_backend':           lambda v: isinstance(v, str) and v in ('auto', 'nvml', 'amdgpu'),
    'cpu_temp_source':       lambda v: isinstance(v, str),
}

DEFAULTS = {
    'screen_index':         0,
    'default_screen_index': None,
    'screen_uuid':          None,
    'default_screen_uuid':  None,
    'poll_ms':              1000,
    'smooth_n':     5,
    'bg_color':     '#252040',
    'inner_color':  '#1e1a35',
    'track_color':  '#332e55',
    'tick_color':   '#3d3860',
    'panel_radius': 18,
    'tray_minimize_to_tray': True,
    'tray_warning_shown':    False,
    'first_run_done':        False,
    'gpu_index':             0,
    'gpu_backend':           'auto',
    'cpu_temp_source':       'auto',
}


class Config(QObject):
    changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        cfg_dir = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')).expanduser()
        self._path = cfg_dir / 'thermalcanary' / 'config.yaml'
        self._data = dict(DEFAULTS)
        self._load()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._write)

    def clamp_screen_indices(self, screens: list) -> None:
        from thermalcanary.screens import screen_uuid, find_index_by_uuid
        n = len(screens)
        if n < 1:
            return

        # UUID wins; index is the auto-migration fallback.
        resolved = find_index_by_uuid(screens, self.get('default_screen_uuid'))
        if resolved is None:
            dsi = self.get('default_screen_index')
            if isinstance(dsi, int) and 0 <= dsi < n:
                resolved = dsi
                self.set('default_screen_uuid', screen_uuid(screens[resolved]))
        if resolved is None:
            resolved = 0
            self.set('default_screen_uuid', screen_uuid(screens[0]))
            self.set('default_screen_index', 0)

        # Always open on the default monitor; refresh stored index in case Qt reordered.
        self.set('screen_index', resolved)
        self.set('screen_uuid', screen_uuid(screens[resolved]))
        if self.get('default_screen_index') != resolved:
            self.set('default_screen_index', resolved)

    def get(self, key):
        return self._data.get(key, DEFAULTS[key])

    def set(self, key, value):
        if self._data.get(key) == value:
            return
        self._data[key] = value
        self.changed.emit(key)
        self._save_timer.start()

    def save_now(self):
        self._save_timer.stop()
        self._write()

    def _load(self):
        try:
            with open(self._path) as f:
                loaded = yaml.safe_load(f) or {}
            for k, v in loaded.items():
                if k not in DEFAULTS:
                    continue
                validator = _VALIDATORS.get(k)
                if validator and not validator(v):
                    print(f'[Thermal Canary] Config: invalid value for {k!r}: {str(v)[:40]!r} — using default',
                          file=sys.stderr)
                    continue
                self._data[k] = v
        except FileNotFoundError:
            print(f'[Thermal Canary] No config at {self._path} — using defaults', file=sys.stderr)
        except yaml.YAMLError:
            print(f'[Thermal Canary] Config parse error — using defaults', file=sys.stderr)

    def _write(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix('.yaml.tmp')
            tmp.write_text(yaml.safe_dump(self._data, default_flow_style=False))
            os.chmod(tmp, 0o600)
            tmp.replace(self._path)
        except (OSError, yaml.YAMLError) as e:
            print(f'[Thermal Canary] Config save error: {e}', file=sys.stderr)
