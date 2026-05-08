import pynvml


class NvidiaGpuReader:
    has_fan = True  # discrete NVIDIA cards always expose fan speed via NVML

    def __init__(self, gpu_index: int = 0):
        pynvml.nvmlInit()
        self._handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)

    def stats(self) -> tuple[float, float, float]:
        try:
            temp = float(pynvml.nvmlDeviceGetTemperature(
                self._handle, pynvml.NVML_TEMPERATURE_GPU))
            fan  = float(pynvml.nvmlDeviceGetFanSpeed(self._handle))
            mem  = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
            vram = mem.used / mem.total * 100.0
            return temp, fan, vram
        except pynvml.NVMLError:
            return 0.0, 0.0, 0.0

    def shutdown(self) -> None:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
