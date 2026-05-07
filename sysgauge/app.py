import os
import sys
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QWidget, QGridLayout, QHBoxLayout, QSizePolicy, QToolButton
from PyQt6.QtCore import (Qt, QTimer, QThread, QPropertyAnimation, QEasingCurve,
                           QMetaObject, Q_ARG, QRectF)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QIcon, QShortcut, QKeySequence, QGuiApplication

from sysgauge.config import Config
from sysgauge.sensor import SensorWorker
from sysgauge.gauge import Gauge
from sysgauge.settings import SettingsSidebar, SIDEBAR_W


def _contrast_color(hex_bg: str) -> QColor:
    c = QColor(hex_bg)
    lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
    return QColor('#1a1a1a') if lum > 140 else QColor('#ffffff')


class GaugeArea(QWidget):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config = config

    def paintEvent(self, _event):
        cfg = self._config
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(cfg.get('bg_color')))

        h   = self.height()
        mid = h // 2
        PAD = 16

        lf = QFont('Inter', 15, QFont.Weight.Black)
        lf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
        p.setFont(lf)

        label_col = _contrast_color(cfg.get('bg_color'))
        accent = QColor(label_col)
        accent.setAlpha(40)

        for y, label in ((10, 'CPU'), (mid + 10, 'GPU')):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent)
            p.drawRoundedRect(QRectF(PAD, y, 4, 28), 2, 2)
            p.setPen(QPen(label_col, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(PAD, y, PAD, y + 28)
            p.setPen(label_col)
            p.drawText(QRectF(PAD + 14, y - 2, 120, 32),
                       Qt.AlignmentFlag.AlignVCenter, label)
        p.end()


class SysGauge(QWidget):
    def __init__(self, config: Config):
        super().__init__()
        self._config = config
        self.setWindowTitle('IbaSaW SysGauge')
        self.setWindowFlags(Qt.WindowType.Window)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._gauge_area = GaugeArea(config)
        gauge_area = self._gauge_area
        grid = QGridLayout(gauge_area)
        grid.setSpacing(8)
        grid.setContentsMargins(16, 16, 16, 16)
        for c in range(3): grid.setColumnStretch(c, 1)
        for r in range(2): grid.setRowStretch(r, 1)

        self.g_cpu_t = Gauge('CPU Temp',  '°C', 0, 100, '#ff4060', config, warn=70, crit=85)
        self.g_cpu_u = Gauge('CPU Usage',  '%',  0, 100, '#39ff14', config, warn=85, crit=95)
        self.g_mem   = Gauge('RAM Usage',  '%',  0, 100, '#a855f7', config, warn=80, crit=92)
        self.g_gpu_t = Gauge('GPU Temp',  '°C', 0, 100, '#ff7020', config, warn=75, crit=90)
        self.g_fan   = Gauge('GPU Fan',    '%',  0, 100, '#00c8ff', config, decimals=0)
        self.g_vram  = Gauge('GPU VRAM',   '%',  0, 100, '#00e5cc', config, warn=80, crit=95)
        self._gauges = [self.g_cpu_t, self.g_cpu_u, self.g_mem,
                        self.g_gpu_t, self.g_fan,   self.g_vram]

        grid.addWidget(self.g_cpu_t, 0, 0)
        grid.addWidget(self.g_cpu_u, 0, 1)
        grid.addWidget(self.g_mem,   0, 2)
        grid.addWidget(self.g_gpu_t, 1, 0)
        grid.addWidget(self.g_fan,   1, 1)
        grid.addWidget(self.g_vram,  1, 2)

        outer.addWidget(gauge_area, stretch=1)

        self._thread = QThread(self)
        self._worker = SensorWorker(config)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._worker.reading.connect(self._on_reading)
        self._thread.start()

        self._sidebar = SettingsSidebar(config, self._worker)
        self._sidebar.setMinimumWidth(0)
        self._sidebar.setMaximumWidth(0)
        self._sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        outer.addWidget(self._sidebar)

        self._gear_btn = QToolButton(self)
        self._gear_btn.setText('⚙')
        self._gear_btn.setFixedSize(32, 32)
        self._gear_btn.setStyleSheet(
            'QToolButton { background:rgba(255,255,255,20); border:none; '
            'border-radius:16px; color:#888; font-size:16px; }'
            'QToolButton:hover { background:rgba(255,255,255,55); color:#fff; }')
        self._gear_btn.clicked.connect(self.toggle_settings)
        self._gear_btn.raise_()

        QShortcut(QKeySequence('Ctrl+,'), self, self.toggle_settings)
        QShortcut(QKeySequence('Escape'), self, self._close_settings)

        self._anim = QPropertyAnimation(self._sidebar, b'maximumWidth')
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._sidebar_open = False

        config.changed.connect(self._on_config_changed)

    def toggle_settings(self):
        if self._sidebar_open:
            self._close_settings()
        else:
            self._open_settings()

    def _open_settings(self):
        self._sidebar_open = True
        self._anim.stop()
        self._anim.setStartValue(self._sidebar.maximumWidth())
        self._anim.setEndValue(SIDEBAR_W)
        self._anim.start()

    def _close_settings(self):
        self._sidebar_open = False
        self._anim.stop()
        self._anim.setStartValue(self._sidebar.maximumWidth())
        self._anim.setEndValue(0)
        self._anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._gear_btn.move(self.width() - 44, 8)

    def _on_reading(self, cpu_t, gpu_t, gpu_f, cpu_u, mem, gpu_vram):
        self.g_cpu_t.set_value(cpu_t)
        self.g_gpu_t.set_value(gpu_t)
        self.g_fan.set_value(gpu_f)
        self.g_cpu_u.set_value(cpu_u)
        self.g_mem.set_value(mem)
        self.g_vram.set_value(gpu_vram)

    def _on_config_changed(self, key: str):
        if key in ('bg_color', 'inner_color', 'track_color', 'tick_color'):
            for g in self._gauges:
                g.update()
            self._gauge_area.update()
            self.update()
        elif key == 'smooth_n':
            QMetaObject.invokeMethod(
                self._worker, 'set_smooth_n',
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, self._config.get('smooth_n')))
        elif key == 'poll_ms':
            QMetaObject.invokeMethod(
                self._worker, 'set_interval',
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, self._config.get('poll_ms')))
        elif key == 'screen_index':
            self._move_to_screen(self._config.get('screen_index'))

    def _move_to_screen(self, idx: int):
        screens = QApplication.instance().screens()
        if not screens:
            return
        screen = screens[min(max(idx, 0), len(screens) - 1)]
        geo = screen.availableGeometry()  # orientation-aware

        win_id = hex(int(self.winId()))

        # Centered rect sized to 60% of the target screen — works for any
        # orientation (landscape or portrait) and avoids Mutter's
        # "fills screen → strip decorations" heuristic.
        w = max(640, min(1200, int(geo.width()  * 0.6)))
        h = max(480, min(900,  int(geo.height() * 0.6)))
        x = geo.x() + (geo.width()  - w) // 2
        y = geo.y() + (geo.height() - h) // 2

        def _run(args):
            return subprocess.run(
                args, check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ).returncode

        # Stage 1: clear maximized state
        self.showNormal()
        _run(['wmctrl', '-i', '-r', win_id,
              '-b', 'remove,maximized_vert,maximized_horz'])

        def _move():
            # Stage 2: move via wmctrl -e (crosses monitor boundaries reliably)
            rc = _run(['wmctrl', '-i', '-r', win_id, '-e', f'0,{x},{y},{w},{h}'])
            if rc != 0:
                self.setGeometry(x, y, w, h)

            def _maximize():
                rc2 = _run(['wmctrl', '-i', '-r', win_id,
                            '-b', 'add,maximized_vert,maximized_horz'])
                if rc2 != 0:
                    self.showMaximized()

            # Stage 3: maximize after Mutter re-associates window with new monitor
            QTimer.singleShot(400, _maximize)

        # Let unmaximize settle before moving
        QTimer.singleShot(200, _move)

    def closeEvent(self, event):
        self._config.save_now()
        self._worker.stop()
        self._thread.quit()
        self._thread.wait()
        super().closeEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self._config.get('bg_color')))
        p.end()

    def place_on_screen(self):
        screens = QApplication.instance().screens()
        screen = screens[min(int(self._config.get('screen_index')), len(screens) - 1)]
        geo = screen.availableGeometry()

        # Place on correct screen before show
        self.setGeometry(geo)
        self.show()

        # Qt's showMaximized/setWindowState are silently dropped by Mutter
        # for unfocused windows on secondary monitors. Use wmctrl to send
        # the _NET_WM_STATE_MAXIMIZED ClientMessage from a proper X client.
        def _wmctrl_maximize():
            win_id = hex(int(self.winId()))
            result = subprocess.run(
                ['wmctrl', '-i', '-r', win_id, '-b', 'add,maximized_vert,maximized_horz'],
                check=False)
            if result.returncode != 0:
                # wmctrl not available — fall back to Qt (may crop by title bar height)
                self.showMaximized()

        QTimer.singleShot(300, _wmctrl_maximize)


def main():
    import fcntl
    lock_path = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / 'sysgauge.lock'
    lock_file = open(lock_path, 'w')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print('[SysGauge] Already running — exiting.', file=sys.stderr)
        sys.exit(0)

    QGuiApplication.setDesktopFileName('sysgauge')

    app = QApplication(sys.argv)
    app.setApplicationName('sysgauge')
    app.setApplicationDisplayName('IbaSaW SysGauge')

    icon_path = (Path(os.environ.get('XDG_DATA_HOME', '~/.local/share')).expanduser()
                 / 'sysgauge' / 'assets' / 'sysgauge.png')
    app.setWindowIcon(QIcon.fromTheme('sysgauge', QIcon(str(icon_path))))

    config = Config()
    win = SysGauge(config)
    win.place_on_screen()
    sys.exit(app.exec())
