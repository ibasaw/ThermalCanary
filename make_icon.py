#!/usr/bin/env python3
"""
Generate sysgauge.png — 512x512 app icon using the real Gauge widget.
Run from the project folder with the venv active:
  ~/.local/share/sysgauge/venv/bin/python3 make_icon.py
"""

import sys
import math
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPainter, QColor, QImage, QRadialGradient
from PyQt6.QtCore import Qt, QRectF

# Import the real Gauge class from the app
sys.path.insert(0, '.')
from sysgauge import Gauge

SIZE   = 512
CORNER = 96   # rounded rect corner radius for the icon background


def make_icon():
    app = QApplication(sys.argv)

    from PyQt6.QtCore import QPoint

    # Single large gauge — CPU Temp as hero
    gauge = Gauge('CPU', '°C', 0, 100, '#ff4060', warn=70, crit=85)
    gauge.set_value(72)
    gauge._cur = 72.0   # skip animation

    PAD  = 24           # inset from icon edges
    cell = SIZE - PAD * 2

    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # ── Rounded dark background ────────────────────────────────────
    p.setPen(Qt.PenStyle.NoPen)
    grad = QRadialGradient(SIZE / 2, SIZE * 0.4, SIZE * 0.65)
    grad.setColorAt(0.0, QColor('#2d2850'))
    grad.setColorAt(1.0, QColor('#1e1a35'))
    p.setBrush(grad)
    p.drawRoundedRect(QRectF(0, 0, SIZE, SIZE), CORNER, CORNER)

    # ── Render gauge ───────────────────────────────────────────────
    gauge.resize(cell, cell)
    gauge.render(p, targetOffset=QPoint(PAD, PAD))

    p.end()

    out = 'sysgauge.png'
    img.save(out)
    print(f'Saved {out}  ({SIZE}x{SIZE})')


if __name__ == '__main__':
    make_icon()
