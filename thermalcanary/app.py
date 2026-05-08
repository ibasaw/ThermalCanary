import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout,
                             QToolButton, QDialog, QLabel, QPushButton, QLayout)
from PyQt6.QtCore import (Qt, QTimer, QThread, QPropertyAnimation, QEasingCurve,
                           QMetaObject, Q_ARG, QRectF, QRect)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QIcon, QShortcut, QKeySequence, QGuiApplication

from thermalcanary.config import Config
from thermalcanary.sensor import SensorWorker
from thermalcanary.gauge import Gauge, TEMP_WARM, TEMP_HOT, TEMP_CRIT
from thermalcanary.settings import SettingsSidebar, SIDEBAR_W
from thermalcanary.tray import TrayController

try:
    import thermalcanary_pro as _pro
    PRO = True
except ImportError:
    _pro = None
    PRO = False


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        from thermalcanary import __version__

        wrap = QWidget(self)
        wrap.setObjectName('wrap')
        wrap.setStyleSheet(
            '#wrap { background:#1a1630; border:1px solid #443e70; border-radius:12px; }')

        title = QLabel('Thermal Canary')
        title.setStyleSheet(
            'color:#ffffff; font-family:Inter; font-size:16px; font-weight:bold;')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel(f'v{__version__}')
        version.setStyleSheet('color:#7c6ef5; font-family:Inter; font-size:12px;')
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc = QLabel(
            'Linux hardware monitor for dedicated display panels.\n'
            'CPU temp · CPU usage · RAM · GPU temp · GPU fan · GPU VRAM')
        desc.setStyleSheet('color:#aaaacc; font-family:Inter; font-size:12px;')
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)

        link = QLabel('<a href="https://github.com/ibasaw/thermalcanary"'
                      ' style="color:#7c6ef5;">github.com/ibasaw/thermalcanary</a>')
        link.setStyleSheet('font-family:Inter; font-size:11px;')
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link.setOpenExternalLinks(True)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet('background:#332e55;')

        mit = QLabel('MIT License — free and open source')
        mit.setStyleSheet('color:#665e88; font-family:Inter; font-size:10px;')
        mit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_close = QPushButton('Close')
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            'QPushButton { background:#252040; border:1px solid #443e70; border-radius:6px;'
            ' color:#aaa; font-family:Inter; font-size:12px; padding:6px 20px; }'
            'QPushButton:hover { background:#2d2850; color:#fff; }')
        btn_close.clicked.connect(self.accept)

        inner = QVBoxLayout(wrap)
        inner.setContentsMargins(32, 28, 32, 24)
        inner.setSpacing(10)
        inner.addWidget(title)
        inner.addWidget(version)
        inner.addWidget(desc)
        inner.addWidget(link)
        inner.addWidget(sep)
        inner.addWidget(mit)
        inner.addSpacing(4)
        inner.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignHCenter)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(wrap)


class QuitDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        wrap = QWidget(self)
        wrap.setObjectName('wrap')
        wrap.setStyleSheet(
            '#wrap { background:#1a1630; border:1px solid #443e70; border-radius:12px; }')

        title = QLabel('Quit Thermal Canary')
        title.setStyleSheet('color:#ffffff; font-family:Inter; font-size:14px; font-weight:bold;')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        msg = QLabel('Close the application?')
        msg.setStyleSheet('color:#aaaacc; font-family:Inter; font-size:12px;')
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_cancel = QPushButton('Cancel')
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            'QPushButton { background:#252040; border:1px solid #443e70; border-radius:6px;'
            ' color:#aaa; font-family:Inter; font-size:12px; padding:6px 20px; }'
            'QPushButton:hover { background:#2d2850; color:#fff; }')
        btn_cancel.clicked.connect(self.reject)

        btn_quit = QPushButton('Quit')
        btn_quit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_quit.setStyleSheet(
            'QPushButton { background:#5a1020; border:1px solid #ff2040; border-radius:6px;'
            ' color:#ff6070; font-family:Inter; font-size:12px; font-weight:bold; padding:6px 20px; }'
            'QPushButton:hover { background:#7a1828; color:#fff; }')
        btn_quit.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_quit)

        inner = QVBoxLayout(wrap)
        inner.setContentsMargins(28, 24, 28, 24)
        inner.setSpacing(14)
        inner.addWidget(title)
        inner.addWidget(msg)
        inner.addLayout(btn_row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(wrap)


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


class ThermalCanary(QWidget):
    def __init__(self, config: Config, icon_path: str = ''):
        super().__init__()
        self._config = config
        self.setWindowTitle('Thermal Canary')
        self.setWindowFlags(Qt.WindowType.Window)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        # Prevent layout from pushing its minimumSizeHint into WM_NORMAL_HINTS,
        # which causes Mutter to drop fullscreen on short monitors (e.g. 480px tall).
        outer.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        self._gauge_area = GaugeArea(config)
        gauge_area = self._gauge_area
        grid = QGridLayout(gauge_area)
        grid.setSpacing(8)
        grid.setContentsMargins(16, 16, 16, 16)
        for c in range(3): grid.setColumnStretch(c, 1)
        for r in range(2): grid.setRowStretch(r, 1)

        self.g_cpu_t = Gauge('CPU Temp',  '°C', 0, 100, '#ff4060', config, warn=TEMP_WARM, crit=TEMP_HOT, blink_above=TEMP_CRIT)
        self.g_cpu_u = Gauge('CPU Usage',  '%',  0, 100, '#39ff14', config, warn=85, crit=95)
        self.g_mem   = Gauge('RAM Usage',  '%',  0, 100, '#a855f7', config, warn=80, crit=92)
        self.g_gpu_t = Gauge('GPU Temp',  '°C', 0, 100, '#ff7020', config, warn=TEMP_WARM, crit=TEMP_HOT, blink_above=TEMP_CRIT)
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
        self._worker.gpu_ready.connect(self._on_gpu_ready)
        self._thread.start()

        # Sidebar is an overlay — NOT in the layout — so its minimumSizeHint
        # never propagates into WM_NORMAL_HINTS and can't trigger Mutter to
        # drop fullscreen state during the slide animation.
        self._sidebar = SettingsSidebar(config, self._worker, self, pro=_pro)
        self._sidebar.setGeometry(self.width(), 0, 0, self.height())
        self._sidebar.hide()

        btn_style = (
            'QToolButton { background:rgba(255,255,255,20); border:none; '
            'border-radius:16px; color:#888; font-size:16px; }'
            'QToolButton:hover { background:rgba(255,255,255,55); color:#fff; }')

        self._gear_btn = QToolButton(self)
        self._gear_btn.setText('⚙')
        self._gear_btn.setFixedSize(32, 32)
        self._gear_btn.setStyleSheet(btn_style)
        self._gear_btn.clicked.connect(self.toggle_settings)
        self._gear_btn.raise_()

        self._close_btn = QToolButton(self)
        self._close_btn.setText('✕')
        self._close_btn.setFixedSize(32, 32)
        self._close_btn.setStyleSheet(btn_style)
        self._close_btn.clicked.connect(self._confirm_quit)
        self._close_btn.raise_()

        self._tray = TrayController(self, icon_path, config,
                                    on_quit=self._confirm_quit,
                                    on_about=self._show_about)

        QShortcut(QKeySequence('Ctrl+,'), self, self.toggle_settings)
        esc = QShortcut(QKeySequence('Escape'), self)
        esc.setContext(Qt.ShortcutContext.WindowShortcut)
        esc.activated.connect(self._close_settings)

        # Animate geometry directly — avoids layout invalidation that
        # would re-propagate minimumSizeHint to WM_NORMAL_HINTS.
        self._anim = QPropertyAnimation(self._sidebar, b'geometry')
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._on_anim_finished)
        self._sidebar_open = False
        self.setMinimumSize(0, 0)

        config.changed.connect(self._on_config_changed)

    def toggle_settings(self):
        if self._sidebar_open:
            self._close_settings()
        else:
            self._open_settings()

    def _restack_overlay(self):
        self._sidebar.raise_()
        self._gear_btn.raise_()
        self._close_btn.raise_()

    def _open_settings(self):
        self._sidebar_open = True
        self._sidebar.show()
        self._restack_overlay()
        self._anim.stop()
        self._anim.setStartValue(self._sidebar.geometry())
        self._anim.setEndValue(QRect(self.width() - SIDEBAR_W, 0, SIDEBAR_W, self.height()))
        self._anim.start()

    def _close_settings(self):
        if not self._sidebar_open:
            return
        self._sidebar_open = False
        self._anim.stop()
        self._anim.setStartValue(self._sidebar.geometry())
        self._anim.setEndValue(QRect(self.width(), 0, 0, self.height()))
        self._anim.start()

    def _on_anim_finished(self):
        if not self._sidebar_open:
            self._sidebar.hide()
            self._sidebar.setGeometry(self.width(), 0, 0, self.height())

    def _on_gpu_ready(self, found: bool, fan_label: str):
        if not found:
            for g in (self.g_gpu_t, self.g_fan, self.g_vram):
                g.set_unavailable(True)
        elif fan_label != 'GPU Fan':
            self.g_fan.set_label(fan_label)

    def _show_about(self):
        dlg = AboutDialog(self)
        dlg.adjustSize()
        dlg.move(self.geometry().center() - dlg.rect().center())
        dlg.exec()

    def _confirm_quit(self):
        dlg = QuitDialog(self)
        dlg.adjustSize()
        dlg.move(self.geometry().center() - dlg.rect().center())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._config.save_now()
            QMetaObject.invokeMethod(
                self._worker, 'stop',
                Qt.ConnectionType.BlockingQueuedConnection)
            self._thread.quit()
            self._thread.wait()
            QApplication.instance().quit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._gear_btn.move(self.width() - 84, 8)
        self._close_btn.move(self.width() - 44, 8)
        if self._sidebar_open:
            self._sidebar.setGeometry(self.width() - SIDEBAR_W, 0, SIDEBAR_W, self.height())
        else:
            self._sidebar.setGeometry(self.width(), 0, 0, self.height())

    def _on_reading(self, cpu_t, gpu_t, gpu_f, cpu_u, mem, gpu_vram):
        self.g_cpu_t.set_value(cpu_t)
        self.g_gpu_t.set_value(gpu_t)
        self.g_fan.set_value(gpu_f)
        self.g_cpu_u.set_value(cpu_u)
        self.g_mem.set_value(mem)
        self.g_vram.set_value(gpu_vram)
        if PRO:
            self._sidebar.push_reading(cpu_t, gpu_t, cpu_u, mem, gpu_vram)

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
        elif key == 'cpu_temp_source':
            QMetaObject.invokeMethod(
                self._worker, 'reset_cpu_buf',
                Qt.ConnectionType.QueuedConnection)
        elif key in ('screen_index', 'screen_uuid'):
            self._move_to_screen_by_uuid(self._config.get('screen_uuid'))

    def _move_to_screen_by_uuid(self, target_uuid: str | None):
        from thermalcanary.screens import find_index_by_uuid
        screens = QApplication.instance().screens()
        if not screens:
            return
        idx = find_index_by_uuid(screens, target_uuid)
        if idx is None:
            idx = self._config.get('screen_index')
        self._move_to_screen(idx)

    def _move_to_screen(self, idx: int):
        screens = QApplication.instance().screens()
        if not screens:
            return
        screen = screens[min(max(idx, 0), len(screens) - 1)]
        geo = screen.geometry()

        self.setMinimumSize(0, 0)
        self.showNormal()
        self.setMinimumSize(0, 0)

        handle = self.windowHandle()
        if handle:
            handle.setScreen(screen)

        self.setGeometry(geo)
        QTimer.singleShot(50, self.showFullScreen)
        QTimer.singleShot(100, self._restack_overlay)

    def closeEvent(self, event):
        if self._tray.tray is not None and self._config.get('tray_minimize_to_tray'):
            event.ignore()
            self.hide()
            self._tray.update_menu_label()
            return
        self._config.save_now()
        if self._thread.isRunning():
            # stop() must run in the worker thread (QTimer lives there).
            # Guard isRunning() first: BlockingQueuedConnection on a stopped
            # thread deadlocks because no event loop is there to reply.
            QMetaObject.invokeMethod(
                self._worker, 'stop',
                Qt.ConnectionType.BlockingQueuedConnection)
            self._thread.quit()
            self._thread.wait()
        super().closeEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self._config.get('bg_color')))
        p.end()

    def place_on_screen(self):
        target_uuid = self._config.get('screen_uuid')
        self.show()
        QTimer.singleShot(300, lambda: self._move_to_screen_by_uuid(target_uuid))


_lock_file = None  # module-level ref keeps the fd alive so the lock is never released


def main():
    import fcntl
    # Force XCB; geometry/fullscreen logic is tuned for X11/XWayland.
    os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')
    # GNOME Wayland sessions may not set DISPLAY — target the XWayland socket.
    if not os.environ.get('DISPLAY'):
        os.environ['DISPLAY'] = ':0'

    global _lock_file
    _runtime = os.environ.get('XDG_RUNTIME_DIR', '')
    if _runtime:
        lock_path = Path(_runtime) / 'thermalcanary.lock'
    else:
        lock_path = Path.home() / '.cache' / 'thermalcanary' / 'thermalcanary.lock'
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    _lock_file = open(lock_path, 'w')
    try:
        fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print('[Thermal Canary] Already running — exiting.', file=sys.stderr)
        sys.exit(0)

    QGuiApplication.setDesktopFileName('thermalcanary')

    app = QApplication(sys.argv)
    app.setApplicationName('thermalcanary')
    app.setApplicationDisplayName('Thermal Canary')

    icon_path = (Path(os.environ.get('XDG_DATA_HOME', '~/.local/share')).expanduser()
                 / 'thermalcanary' / 'assets' / 'thermalcanary.png')
    app.setWindowIcon(QIcon.fromTheme('thermalcanary', QIcon(str(icon_path))))

    config = Config()
    config.clamp_screen_indices(app.screens())

    from thermalcanary.first_run import run_if_needed
    run_if_needed(config)

    win = ThermalCanary(config, icon_path=str(icon_path))
    win.place_on_screen()
    sys.exit(app.exec())
