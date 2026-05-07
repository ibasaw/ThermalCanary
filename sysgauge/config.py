import os
import sys
import yaml
from pathlib import Path
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

DEFAULTS = {
    'screen_index': 2,
    'poll_ms':      1000,
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
            self._data.update({k: v for k, v in loaded.items() if k in DEFAULTS})
        except FileNotFoundError:
            print(f'[SysGauge] No config at {self._path} — using defaults', file=sys.stderr)
        except yaml.YAMLError as e:
            print(f'[SysGauge] Config parse error: {e} — using defaults', file=sys.stderr)

    def _write(self):
        try:
            tmp = self._path.with_suffix('.yaml.tmp')
            tmp.write_text(yaml.safe_dump(self._data, default_flow_style=False))
            tmp.replace(self._path)
        except Exception as e:
            print(f'[SysGauge] Config save error: {e}', file=sys.stderr)
