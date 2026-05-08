import psutil
import pynvml
from collections import deque
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
from thermalcanary.config import Config


class SensorWorker(QObject):
    reading = pyqtSignal(float, float, float, float, float, float)

    def __init__(self, config: Config):
        super().__init__()
        self._config = config
        self._timer: QTimer | None = None
        self._gpu = None
        n = config.get('smooth_n')
        self._cpu_t_buf: deque[float] = deque(maxlen=n)
        self._cpu_u_buf: deque[float] = deque(maxlen=n)

    def start(self):
        try:
            pynvml.nvmlInit()
            self._gpu = pynvml.nvmlDeviceGetHandleByIndex(0)
        except pynvml.NVMLError:
            self._gpu = None

        psutil.cpu_percent(interval=None)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(self._config.get('poll_ms'))
        QTimer.singleShot(400, self._poll)

    @pyqtSlot()
    def stop(self):
        if self._timer:
            self._timer.stop()
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass

    @pyqtSlot(int)
    def set_interval(self, ms: int):
        if self._timer:
            self._timer.setInterval(ms)

    @pyqtSlot(int)
    def set_smooth_n(self, n: int):
        self._cpu_t_buf = deque(list(self._cpu_t_buf)[-n:], maxlen=n)
        self._cpu_u_buf = deque(list(self._cpu_u_buf)[-n:], maxlen=n)

    def _poll(self):
        cpu_t_raw = self._cpu_temp()
        cpu_u_raw = psutil.cpu_percent(interval=None)
        self._cpu_t_buf.append(cpu_t_raw)
        self._cpu_u_buf.append(cpu_u_raw)
        cpu_t = sum(self._cpu_t_buf) / len(self._cpu_t_buf)
        cpu_u = sum(self._cpu_u_buf) / len(self._cpu_u_buf)
        gpu_t, gpu_f, gpu_vram = self._gpu_stats()
        mem = psutil.virtual_memory().percent
        self.reading.emit(cpu_t, gpu_t, gpu_f, cpu_u, mem, gpu_vram)

    def _cpu_temp(self) -> float:
        try:
            entries = psutil.sensors_temperatures().get('coretemp', [])
            pkg = next((e for e in entries if e.label == 'Package id 0'), None)
            return pkg.current if pkg else (entries[0].current if entries else 0.0)
        except Exception:
            return 0.0

    def _gpu_stats(self) -> tuple[float, float, float]:
        if self._gpu is None:
            return 0.0, 0.0, 0.0
        try:
            temp = float(pynvml.nvmlDeviceGetTemperature(
                self._gpu, pynvml.NVML_TEMPERATURE_GPU))
            fan  = float(pynvml.nvmlDeviceGetFanSpeed(self._gpu))
            mem  = pynvml.nvmlDeviceGetMemoryInfo(self._gpu)
            vram = mem.used / mem.total * 100.0
            return temp, fan, vram
        except pynvml.NVMLError:
            return 0.0, 0.0, 0.0
