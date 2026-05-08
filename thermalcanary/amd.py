from thermalcanary._gpu_sysfs import _SysfsGpuReader


class AmdGpuReader(_SysfsGpuReader):
    _HWMON_NAMES = ('amdgpu',)
    _SYSFS_ENV   = 'THERMALCANARY_SYSFS_ROOT'

    def __init__(self, card: str = 'card0', sysfs_root: str | None = None):
        super().__init__(card, sysfs_root)

    def gpu_busy(self) -> float:
        v = self._read_int(self._device / 'gpu_busy_percent')
        return float(v) if v is not None else 0.0

    def vram_percent(self) -> float:
        used  = self._read_int(self._device / 'mem_info_vram_used')
        total = self._read_int(self._device / 'mem_info_vram_total')
        if not total or used is None:
            return 0.0
        return used / total * 100.0

    def stats(self) -> tuple[float, float, float]:
        fan = self.fan_percent() if self.has_fan else self.gpu_busy()
        return self.temp(), fan, self.vram_percent()
