import math
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from thermalcanary.config import Config

ANIM_FPS = 60

# Thermal alert thresholds — Spec: docs/specs/core-monitoring.md#thermal-alerts
TEMP_WARM = 60   # °C — orange
TEMP_HOT  = 80   # °C — red
TEMP_CRIT = 90   # °C — bright red + blink


def thermal_color(temp: float) -> str:
    if temp >= TEMP_HOT:
        return '#e03e3e'
    if temp >= TEMP_WARM:
        return '#f5a623'
    return '#3ee060'


_DEFAULT_GRADIENT = [
    (0.00, QColor('#00aaff')),
    (0.25, QColor('#39ff14')),
    (0.65, QColor('#ffd000')),
    (0.85, QColor('#ff8800')),
    (1.00, QColor('#ff2020')),
]


def _lerp_hsv(c1: QColor, c2: QColor, t: float) -> QColor:
    h1, s1, v1, a1 = c1.hsvHueF(), c1.hsvSaturationF(), c1.valueF(), c1.alphaF()
    h2, s2, v2, a2 = c2.hsvHueF(), c2.hsvSaturationF(), c2.valueF(), c2.alphaF()
    if h1 < 0: h1 = h2
    if h2 < 0: h2 = h1
    if h1 < 0: h1 = h2 = 0.0
    dh = h2 - h1
    if dh > 0.5:  dh -= 1.0
    if dh < -0.5: dh += 1.0
    h = (h1 + dh * t) % 1.0
    result = QColor()
    result.setHsvF(h, s1 + (s2 - s1) * t, v1 + (v2 - v1) * t, a1 + (a2 - a1) * t)
    return result


class Gauge(QWidget):
    _START  = 225
    _SPAN   = 270
    _TRACK  = 13
    _ARC    = 13
    _GLOW   = 28
    _NTICKS = 8

    def __init__(self, title: str, unit: str, lo: float, hi: float,
                 color: str, config: Config, warn: float | None = None,
                 crit: float | None = None, decimals: int = 0,
                 blink_above: float | None = None):
        super().__init__()
        self.title       = title
        self.unit        = unit
        self.lo          = lo
        self.hi          = hi
        self._base       = QColor(color)  # kept for API compat; dynamic color overrides
        self._config     = config
        self.warn        = warn
        self.crit        = crit
        self.decimals    = decimals
        self.blink_above = blink_above
        self._target     = float(lo)
        self._cur        = float(lo)
        self._blink_on   = True
        self._blink_frame = 0
        self._gradient_stops = self._build_stops()

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(140, 140)

        anim = QTimer(self)
        anim.timeout.connect(self._step)
        anim.start(1000 // ANIM_FPS)

    def _build_stops(self) -> list[tuple[float, QColor]]:
        span = (self.hi - self.lo) or 1.0
        if self.warn is not None and self.crit is not None:
            warn_r = max(0.0, min(1.0, (self.warn - self.lo) / span))
            crit_r = max(0.0, min(1.0, (self.crit - self.lo) / span))
            mid_r  = (warn_r + crit_r) / 2
            return [
                (0.00,   QColor('#00aaff')),
                (0.25,   QColor('#39ff14')),
                (warn_r, QColor('#ffd000')),
                (mid_r,  QColor('#ff8800')),
                (crit_r, QColor('#ff2020')),
            ]
        return list(_DEFAULT_GRADIENT)

    def _color_for(self, ratio: float) -> QColor:
        ratio = max(0.0, min(1.0, ratio))
        stops = self._gradient_stops
        if ratio <= stops[0][0]:
            return stops[0][1]
        if ratio >= stops[-1][0]:
            return stops[-1][1]
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= ratio <= p1:
                t = (ratio - p0) / (p1 - p0) if p1 > p0 else 0.0
                return _lerp_hsv(c0, c1, t)
        return stops[-1][1]

    def set_value(self, v: float):
        self._target = max(self.lo, min(self.hi, float(v)))

    def _step(self):
        d = self._target - self._cur
        if abs(d) > 0.02:
            self._cur += d * 0.14
            self.update()
        if self.blink_above is not None and self._cur >= self.blink_above:
            self._blink_frame = (self._blink_frame + 1) % 40
            new_on = self._blink_frame < 26
            if new_on != self._blink_on:
                self._blink_on = new_on
                self.update()
        elif not self._blink_on:
            self._blink_on = True
            self._blink_frame = 0
            self.update()

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
        span  = (self.hi - self.lo) or 1.0
        ratio = max(0.0, min(1.0, (self._cur - self.lo) / span))
        col   = self._color_for(ratio)

        p.setPen(QPen(QColor(cfg.get('track_color')), self._TRACK,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, int(self._START * 16), int(-self._SPAN * 16))

        self._draw_ticks(p, cx, cy, r)

        if ratio > 0.01 and self._blink_on:
            gc = QColor(col)
            gc.setAlpha(40)
            p.setPen(QPen(gc, self._GLOW, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, int(self._START * 16), int(-ratio * self._SPAN * 16))

        if ratio > 0.01 and self._blink_on:
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
