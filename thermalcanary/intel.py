from thermalcanary._gpu_sysfs import _SysfsGpuReader


class IntelGpuReader(_SysfsGpuReader):
    # xe = Arc discrete (kernel 6.2+), i915 = integrated + older Arc
    _HWMON_NAMES = ('xe', 'i915')
    _SYSFS_ENV   = 'THERMALCANARY_SYSFS_ROOT'

    def __init__(self, card: str = 'card0', sysfs_root: str | None = None):
        super().__init__(card, sysfs_root)
    # vram_percent returns 0.0 from base — xe/i915 don't expose VRAM via sysfs
