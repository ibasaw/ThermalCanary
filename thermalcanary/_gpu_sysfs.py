import glob
import os
from pathlib import Path


class _SysfsGpuReader:
    _HWMON_NAMES: tuple[str, ...] = ()
    _SYSFS_ENV: str = ''

    def __init__(self, card: str, sysfs_root: str | None):
        root = sysfs_root or os.environ.get(self._SYSFS_ENV, '/sys/class/drm')
        self._device = Path(root) / card / 'device'
        self._hwmon = self._find_hwmon()

    def _find_hwmon(self) -> Path | None:
        matches = sorted(glob.glob(str(self._device / 'hwmon' / 'hwmon*')))
        for p in matches:
            try:
                if (Path(p) / 'name').read_text().strip() in self._HWMON_NAMES:
                    return Path(p)
            except OSError:
                pass
        return Path(matches[0]) if matches else None

    @staticmethod
    def _read_int(path: Path) -> int | None:
        try:
            return int(path.read_text().strip())
        except (OSError, ValueError):
            return None

    def temp(self) -> float:
        if not self._hwmon:
            return 0.0
        v = self._read_int(self._hwmon / 'temp1_input')
        return v / 1000.0 if v is not None else 0.0

    @property
    def has_fan(self) -> bool:
        if not self._hwmon:
            return False
        v = self._read_int(self._hwmon / 'fan1_max')
        return v is not None and v > 0

    def fan_percent(self) -> float:
        if not self._hwmon:
            return 0.0
        cur = self._read_int(self._hwmon / 'fan1_input')
        mx  = self._read_int(self._hwmon / 'fan1_max')
        if cur is None or not mx:
            return 0.0
        return min(100.0, cur / mx * 100.0)

    def vram_percent(self) -> float:
        return 0.0

    def stats(self) -> tuple[float, float, float]:
        return self.temp(), self.fan_percent(), self.vram_percent()

    def shutdown(self) -> None:
        pass
