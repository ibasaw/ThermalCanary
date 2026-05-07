import math
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from sysgauge.config import Config

ANIM_FPS = 60


class Gauge(QWidget):
    _START  = 225
    _SPAN   = 270
    _TRACK  = 13
    _ARC    = 13
    _GLOW   = 28
    _NTICKS = 8

    def __init__(self, title: str, unit: str, lo: float, hi: float,
                 color: str, config: Config, warn: float | None = None,
                 crit: float | None = None, decimals: int = 1):
        super().__init__()
        self.title    = title
        self.unit     = unit
        self.lo       = lo
        self.hi       = hi
        self._base    = QColor(color)
        self._config  = config
        self.warn     = warn
        self.crit     = crit
        self.decimals = decimals
        self._target  = float(lo)
        self._cur     = float(lo)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        cfg = self._config
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h  = self.width(), self.height()

        pad   = self._ARC / 2 + 2
        diam  = min(w, h) - pad * 2
        if diam <= 0:
            return
        r     = diam / 2
        cx    = w / 2
        cy    = h / 2
        rect  = QRectF(cx - r, cy - r, diam, diam)
        ratio = max(0.0, min(1.0, (self._cur - self.lo) / (self.hi - self.lo)))
        col   = self._color()

        p.setPen(QPen(QColor(cfg.get('track_color')), self._TRACK,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, int(self._START * 16), int(-self._SPAN * 16))

        self._draw_ticks(p, cx, cy, r)

        if ratio > 0.01:
            gc = QColor(col)
            gc.setAlpha(40)
            p.setPen(QPen(gc, self._GLOW, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, int(self._START * 16), int(-ratio * self._SPAN * 16))

        if ratio > 0.01:
            p.setPen(QPen(col, self._ARC, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, int(self._START * 16), int(-ratio * self._SPAN * 16))

        ir    = r - self._ARC - 8
        irect = QRectF(cx - ir, cy - ir, ir * 2, ir * 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(cfg.get('inner_color')))
        p.drawEllipse(irect)

        vfont = QFont('Roboto Mono', max(12, int(ir * 0.40)), QFont.Weight.Bold)
        p.setFont(vfont)
        p.setPen(QColor('#eeeeff'))
        p.drawText(QRectF(cx - ir, cy - ir * 0.62, ir * 2, ir * 0.58),
                   Qt.AlignmentFlag.AlignCenter,
                   f"{self._cur:.{self.decimals}f}")

        ufont = QFont('Inter', max(8, int(ir * 0.18)))
        ufont.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        p.setFont(ufont)
        uc = QColor(col)
        uc.setAlpha(220)
        p.setPen(uc)
        p.drawText(QRectF(cx - ir, cy + ir * 0.06, ir * 2, ir * 0.32),
                   Qt.AlignmentFlag.AlignCenter, self.unit)

        tfont = QFont('Inter', max(8, int(ir * 0.16)), QFont.Weight.Bold)
        tfont.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        p.setFont(tfont)
        p.setPen(QColor('#ffffff'))
        p.drawText(QRectF(cx - ir, cy + ir * 0.40, ir * 2, ir * 0.40),
                   Qt.AlignmentFlag.AlignCenter, self.title.upper())

        p.end()

    def _draw_ticks(self, p: QPainter, cx: float, cy: float, r: float):
        outer = r - 2
        inner = r - 11
        p.setPen(QPen(QColor(self._config.get('tick_color')), 1.5))
        for i in range(self._NTICKS + 1):
            frac = i / self._NTICKS
            deg  = self._START - frac * self._SPAN
            rad  = math.radians(deg)
            ca, sa = math.cos(rad), math.sin(rad)
            p.drawLine(
                QPointF(cx + outer * ca, cy - outer * sa),
                QPointF(cx + inner * ca, cy - inner * sa),
            )
