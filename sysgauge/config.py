import os
import re
import sys
import yaml
from pathlib import Path
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

_HEX = re.compile(r'^#[0-9a-fA-F]{6}$')

def _is_hex(v): return isinstance(v, str) and bool(_HEX.match(v))
def _is_screen(v): return isinstance(v, int) and 0 <= v < 32

_VALIDATORS = {
    'screen_index':         _is_screen,
    'default_screen_index': lambda v: v is None or _is_screen(v),
    'poll_ms':              lambda v: isinstance(v, int) and 100 <= v <= 60000,
    'smooth_n':             lambda v: isinstance(v, int) and 1 <= v <= 100,
    'panel_radius':         lambda v: isinstance(v, int) and 0 <= v <= 100,
    'bg_color':             _is_hex,
    'inner_color':          _is_hex,
    'track_color':          _is_hex,
    'tick_color':           _is_hex,
}

DEFAULTS = {
    'screen_index':         0,
    'default_screen_index': None,
    'poll_ms':              1000,
    'smooth_n':     5,
    'bg_color':     '#252040',
    'inner_color':  '#1e1a35',
    'track_color':  '#332e55',
    'tick_color':   '#3d3860',
    'panel_radius': 18,
}


class Config(QObject):
    changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        cfg_dir = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')).expanduser()
        self._path = cfg_dir / 'sysgauge' / 'config.yaml'
        self._data = dict(DEFAULTS)
        self._load()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._write)

    def clamp_screen_indices(self, screen_count: int) -> None:
        if screen_count < 1:
            return
        dsi = self.get('default_screen_index')
        if dsi is None or not isinstance(dsi, int) or dsi < 0 or dsi >= screen_count:
            dsi = 0
            self.set('default_screen_index', dsi)
        # Always start on the default monitor, ignoring last-session screen_index.
        self.set('screen_index', dsi)

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
                    print(f'[SysGauge] Config: invalid value for {k!r}: {str(v)[:40]!r} — using default',
                          file=sys.stderr)
                    continue
                self._data[k] = v
        except FileNotFoundError:
            print(f'[SysGauge] No config at {self._path} — using defaults', file=sys.stderr)
        except yaml.YAMLError:
            print(f'[SysGauge] Config parse error — using defaults', file=sys.stderr)

    def _write(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix('.yaml.tmp')
            tmp.write_text(yaml.safe_dump(self._data, default_flow_style=False))
            os.chmod(tmp, 0o600)
            tmp.replace(self._path)
        except (OSError, yaml.YAMLError) as e:
            print(f'[SysGauge] Config save error: {e}', file=sys.stderr)
