#!/usr/bin/env python3
"""
IbaSaW IbaSaW SysGauge — Premium Hardware Monitor
GPU via pynvml. CPU temp/usage stabilised with 5-sample rolling average.
"""

import sys
import math
import psutil
import pynvml
from collections import deque

from PyQt6.QtWidgets import QApplication, QWidget, QGridLayout, QSizePolicy
from PyQt6.QtCore import (Qt, QTimer, QRectF, QPointF,
                           QThread, QObject, pyqtSignal)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QLinearGradient

# ── Configuration ───────────────────────────────────────────────────────────────
SCREEN_INDEX   = 2          # 0=monitor1  1=monitor2  2=monitor3
POLL_MS        = 1000       # internal sensor poll — 1s for tight rolling buffer
SMOOTH_N       = 5          # rolling average window (5 samples = 5s)
ANIM_FPS       = 60
BG_COLOR       = '#252040'  # deep purple, lifted for readability on bright screens
INNER_COLOR    = '#1e1a35'  # inner circle
TRACK_COLOR    = '#332e55'  # arc track
TICK_COLOR     = '#3d3860'  # tick marks
PANEL_RADIUS   = 18
# ───────────────────────────────────────────────────────────────────────────────


class SensorWorker(QObject):
    # cpu_temp, gpu_temp, gpu_fan, cpu_usage, memory, gpu_vram
    reading = pyqtSignal(float, float, float, float, float, float)

    def __init__(self):
        super().__init__()
        self._timer: QTimer | None = None
        self._gpu = None
        # Rolling buffers — only for the noisy sensors
        self._cpu_t_buf: deque[float] = deque(maxlen=SMOOTH_N)
        self._cpu_u_buf: deque[float] = deque(maxlen=SMOOTH_N)

    def start(self):
        try:
            pynvml.nvmlInit()
            self._gpu = pynvml.nvmlDeviceGetHandleByIndex(0)
        except pynvml.NVMLError:
            self._gpu = None

        psutil.cpu_percent(interval=None)  # prime

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(POLL_MS)
        QTimer.singleShot(400, self._poll)

    def stop(self):
        if self._timer:
            self._timer.stop()
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass

    def _poll(self):
        # Raw readings
        cpu_t_raw = self._cpu_temp()
        cpu_u_raw = psutil.cpu_percent(interval=None)

        # Push into rolling buffers
        self._cpu_t_buf.append(cpu_t_raw)
        self._cpu_u_buf.append(cpu_u_raw)

        # Stable values = mean of last SMOOTH_N readings
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


class Gauge(QWidget):
    _START  = 225
    _SPAN   = 270
    _TRACK  = 13
    _ARC    = 13
    _GLOW   = 28
    _NTICKS = 8

    def __init__(self, title: str, unit: str, lo: float, hi: float,
                 color: str, warn: float | None = None,
                 crit: float | None = None, decimals: int = 1):
        super().__init__()
        self.title    = title
        self.unit     = unit
        self.lo       = lo
        self.hi       = hi
        self._base    = QColor(color)
        self.warn     = warn
        self.crit     = crit
        self.decimals = decimals
        self._target  = float(lo)
        self._cur     = float(lo)

        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setMinimumSize(140, 140)

        anim = QTimer(self)
        anim.timeout.connect(self._step)
        anim.start(1000 // ANIM_FPS)

    def set_value(self, v: float):
        self._target = max(self.lo, min(self.hi, float(v)))

    def _step(self):
        d = self._target - self._cur
        if abs(d) > 0.02:
            self._cur += d * 0.14
            self.update()

    def _color(self) -> QColor:
        if self.crit is not None and self._cur >= self.crit:
            return QColor('#ff2020')
        if self.warn is not None and self._cur >= self.warn:
            return QColor('#ff8800')
        return self._base

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h  = self.width(), self.height()
        pad   = 2
        diam  = min(w, h) - pad * 2
        r     = diam / 2
        cx    = w / 2
        cy    = h / 2
        rect  = QRectF(cx - r, cy - r, diam, diam)
        ratio = max(0.0, min(1.0, (self._cur - self.lo) / (self.hi - self.lo)))
        col   = self._color()

        # Track arc
        p.setPen(QPen(QColor(TRACK_COLOR), self._TRACK,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, int(self._START * 16), int(-self._SPAN * 16))

        # Tick marks
        self._draw_ticks(p, cx, cy, r)

        # Glow
        if ratio > 0.01:
            gc = QColor(col)
            gc.setAlpha(40)
            p.setPen(QPen(gc, self._GLOW,
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, int(self._START * 16),
                      int(-ratio * self._SPAN * 16))

        # Value arc
        if ratio > 0.01:
            p.setPen(QPen(col, self._ARC,
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, int(self._START * 16),
                      int(-ratio * self._SPAN * 16))

        # Inner circle
        ir    = r - self._ARC - 8
        irect = QRectF(cx - ir, cy - ir, ir * 2, ir * 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(INNER_COLOR))
        p.drawEllipse(irect)

        # Value
        vfont = QFont('Roboto Mono', max(12, int(ir * 0.40)), QFont.Weight.Bold)
        p.setFont(vfont)
        p.setPen(QColor('#eeeeff'))
        p.drawText(QRectF(cx - ir, cy - ir * 0.62, ir * 2, ir * 0.58),
                   Qt.AlignmentFlag.AlignCenter,
                   f"{self._cur:.{self.decimals}f}")

        # Unit
        ufont = QFont('Inter', max(8, int(ir * 0.18)))
        ufont.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        p.setFont(ufont)
        uc = QColor(col)
        uc.setAlpha(220)
        p.setPen(uc)
        p.drawText(QRectF(cx - ir, cy + ir * 0.06, ir * 2, ir * 0.32),
                   Qt.AlignmentFlag.AlignCenter, self.unit)

        # Title
        tfont = QFont('Inter', max(9, int(ir * 0.20)), QFont.Weight.Bold)
        tfont.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        p.setFont(tfont)
        p.setPen(QColor('#ffffff'))
        p.drawText(QRectF(cx - ir, cy + ir * 0.40, ir * 2, ir * 0.40),
                   Qt.AlignmentFlag.AlignCenter, self.title.upper())

        p.end()

    def _draw_ticks(self, p: QPainter, cx: float, cy: float, r: float):
        outer = r - 2
        inner = r - 11
        p.setPen(QPen(QColor(TICK_COLOR), 1.5))
        for i in range(self._NTICKS + 1):
            frac = i / self._NTICKS
            deg  = self._START - frac * self._SPAN
            rad  = math.radians(deg)
            ca, sa = math.cos(rad), math.sin(rad)
            p.drawLine(
                QPointF(cx + outer * ca, cy - outer * sa),
                QPointF(cx + inner * ca, cy - inner * sa),
            )


class SysGauge(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SysGauge')
        self.setWindowFlags(Qt.WindowType.Window)
        self._drag_pos = None

        grid = QGridLayout(self)
        grid.setSpacing(2)
        grid.setContentsMargins(4, 16, 4, 4)
        for c in range(3):
            grid.setColumnStretch(c, 1)
        for r in range(2):
            grid.setRowStretch(r, 1)

        self.g_cpu_t = Gauge('CPU Temp',  '°C', 0, 100, '#ff4060', warn=70, crit=85)
        self.g_gpu_t = Gauge('GPU Temp',  '°C', 0, 100, '#ff7020', warn=75, crit=90)
        self.g_fan   = Gauge('GPU Fan',    '%',  0, 100, '#00c8ff', decimals=0)
        self.g_cpu_u = Gauge('CPU Usage',  '%',  0, 100, '#39ff14', warn=85, crit=95)
        self.g_mem   = Gauge('RAM Usage',  '%',  0, 100, '#a855f7', warn=80, crit=92)
        self.g_vram  = Gauge('GPU VRAM',   '%',  0, 100, '#00e5cc', warn=80, crit=95)

        # Row 0 — CPU
        grid.addWidget(self.g_cpu_t, 0, 0)
        grid.addWidget(self.g_cpu_u, 0, 1)
        grid.addWidget(self.g_mem,   0, 2)
        # Row 1 — GPU
        grid.addWidget(self.g_gpu_t, 1, 0)
        grid.addWidget(self.g_fan,   1, 1)
        grid.addWidget(self.g_vram,  1, 2)

        self._thread = QThread(self)
        self._worker = SensorWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._worker.reading.connect(self._on_reading)
        self._thread.start()

    def _on_reading(self, cpu_t, gpu_t, gpu_f, cpu_u, mem, gpu_vram):
        self.g_cpu_t.set_value(cpu_t)
        self.g_gpu_t.set_value(gpu_t)
        self.g_fan.set_value(gpu_f)
        self.g_cpu_u.set_value(cpu_u)
        self.g_mem.set_value(mem)
        self.g_vram.set_value(gpu_vram)

    def closeEvent(self, event):
        self._worker.stop()
        self._thread.quit()
        self._thread.wait()
        super().closeEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(BG_COLOR))

        w, h  = self.width(), self.height()
        mid   = h // 2
        PAD   = 16   # horizontal inset for line + label

        lf = QFont('Inter', 15, QFont.Weight.Black)
        lf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
        p.setFont(lf)

        # ── CPU label + accent line ──────────────────────────────────
        cpu_col = QColor('#ff4060')

        # Glowing accent bar left of label
        glow = QColor('#ffffff')
        glow.setAlpha(40)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawRoundedRect(QRectF(PAD, 10, 4, 28), 2, 2)

        p.setPen(QPen(QColor('#ffffff'), 4, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawLine(PAD, 10, PAD, 38)

        p.setPen(QColor('#ffffff'))
        p.drawText(QRectF(PAD + 14, 8, 120, 32),
                   Qt.AlignmentFlag.AlignVCenter, 'CPU')

        # ── GPU label + accent line ──────────────────────────────────
        gpu_col = QColor('#ff7020')

        glow2 = QColor('#ffffff')
        glow2.setAlpha(40)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow2)
        p.drawRoundedRect(QRectF(PAD, mid + 10, 4, 28), 2, 2)

        p.setPen(QPen(QColor('#ffffff'), 4, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawLine(PAD, mid + 10, PAD, mid + 38)

        p.setPen(QColor('#ffffff'))
        p.drawText(QRectF(PAD + 14, mid + 8, 120, 32),
                   Qt.AlignmentFlag.AlignVCenter, 'GPU')

        p.end()

    def place_on_screen(self):
        screens = QApplication.instance().screens()
        idx = min(SCREEN_INDEX, len(screens) - 1)
        geo = screens[idx].availableGeometry()
        self.move(geo.x(), geo.y())
        self.show()
        QTimer.singleShot(100, self.showMaximized)


def main():
    app = QApplication(sys.argv)
    win = SysGauge()
    win.place_on_screen()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
