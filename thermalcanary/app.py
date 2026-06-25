import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout,
                             QToolButton, QDialog, QLabel, QPushButton, QLayout)
from PyQt6.QtCore import (Qt, QTimer, QThread, QPropertyAnimation, QEasingCurve,
                           QMetaObject, Q_ARG, QRectF, QRect, QEvent)
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
        from PyQt6.QtGui import QPixmap

        wrap = QWidget(self)
        wrap.setObjectName('wrap')
        wrap.setStyleSheet(
            '#wrap { background:#1a1630; border:1px solid #443e70; border-radius:12px; }')

        # Canary icon at the top — try installed location, fall back to source assets.
        icon_paths = [
            Path(os.environ.get('XDG_DATA_HOME', '~/.local/share')).expanduser()
            / 'thermalcanary' / 'assets' / 'icon.png',
            Path(__file__).resolve().parent.parent / 'assets' / 'icon.png',
        ]
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for p in icon_paths:
            if p.exists():
                pix = QPixmap(str(p)).scaledToHeight(
                    96, Qt.TransformationMode.SmoothTransformation)
                logo.setPixmap(pix)
                break

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
        inner.setContentsMargins(32, 24, 32, 24)
        inner.setSpacing(10)
        inner.addWidget(logo)
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
    def __init__(self, config: Config, icon: 'QIcon | None' = None):
        super().__init__()
        self._config = config
        self.setWindowTitle('Thermal Canary')
        # ╔══════════════════════════════════════════════════════════════════╗
        # ║  ⚠  DO NOT ADD Qt.WindowType.Tool TO THESE FLAGS                 ║
        # ║                                                                  ║
        # ║  Mutter (Ubuntu GNOME) constrains _NET_WM_WINDOW_TYPE_UTILITY    ║
        # ║  windows to their current monitor — setGeometry() X,Y is        ║
        # ║  silently DROPPED, only W,H is honored. Cross-monitor switch    ║
        # ║  becomes impossible. Spent 6+ hours debugging this on 2026-05-09.║
        # ║                                                                  ║
        # ║  See: wiki/decisions/pyqt6-mutter-tool-flag-forbidden.md         ║
        # ╚══════════════════════════════════════════════════════════════════╝
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
        )

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

        self._tray = TrayController(self, icon, config,
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

        # State machine for cross-monitor switching: stash target until
        # WindowStateChange confirms Mutter has finished un-fullscreening.
        self._pending_target_geo = None
        self._pending_target_screen = None

        # Monotonic generation: bumped each time the screen topology settles.
        # Delayed placement callbacks compare against this and abort if stale.
        self._move_generation = 0

        # Debounce burst of screenAdded/screenRemoved/primaryScreenChanged
        # events fired by Mutter during DPMS wake — wait for the topology to
        # settle before re-clamping and re-placing the window.
        self._screens_settle_timer = QTimer(self)
        self._screens_settle_timer.setSingleShot(True)
        self._screens_settle_timer.setInterval(750)
        self._screens_settle_timer.timeout.connect(self._handle_screens_settled)

        config.changed.connect(self._on_config_changed)

        gui_app = QApplication.instance()
        gui_app.screenAdded.connect(self._on_screens_changed)
        gui_app.screenRemoved.connect(self._on_screens_changed)
        gui_app.primaryScreenChanged.connect(lambda _s: self._on_screens_changed())

    def _on_screens_changed(self, *_):
        # Coalesce the burst. Each new event restarts the timer; we act once
        # 750ms passes without any further screen events.
        self._screens_settle_timer.start()

    def _handle_screens_settled(self):
        # DPMS standby/wake: Mutter destroys and recreates QScreen objects.
        # Re-clamp config (UUID → fresh QScreen index) and re-place the window.
        screens = QApplication.instance().screens()
        if not screens:
            return
        self._config.clamp_screen_indices(screens)
        # Invalidate any in-flight move — its captured QScreen pointer is stale.
        self._pending_target_geo = None
        self._pending_target_screen = None
        self._move_generation += 1
        gen = self._move_generation
        QTimer.singleShot(0, lambda: self._place_on_screen_if_current(gen))

    def _place_on_screen_if_current(self, gen: int):
        if gen != self._move_generation:
            return
        self.place_on_screen()

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
        elif key == 'screen_uuid':
            # While screens are still settling after a DPMS wake, skip the
            # move — _handle_screens_settled will re-place from the freshly
            # clamped config once the topology stabilises.
            if self._screens_settle_timer.isActive():
                return
            self._move_to_screen_by_uuid(self._config.get('screen_uuid'))

    def _move_to_screen_by_uuid(self, target_uuid: str | None):
        from thermalcanary.screens import find_index_by_uuid
        screens = QApplication.instance().screens()
        if not screens:
            return
        idx = find_index_by_uuid(screens, target_uuid)
        if idx is None:
            idx = self._config.get('screen_index') or 0
        self._move_to_screen(idx)

    def _move_to_screen(self, idx: int):
        # Event-driven state machine for X11/Mutter cross-monitor placement:
        # - INITIAL placement (not fullscreen): apply geometry directly.
        # - SWITCH (currently fullscreen): un-fullscreen, wait for Mutter's
        #   WindowStateChange ack, THEN apply. Mutter clamps ConfigureRequests
        #   for fullscreen windows; timer-based guesses are racy.
        # See setWindowFlags() above — Qt.WindowType.Tool is forbidden here:
        # Mutter constrains UTILITY windows to their current monitor.
        screens = QApplication.instance().screens()
        if not screens:
            return
        target_screen = screens[min(max(idx, 0), len(screens) - 1)]
        target_geo = target_screen.geometry()

        self._pending_target_screen = target_screen
        self._pending_target_geo = target_geo
        gen = self._move_generation

        if not self.windowHandle():
            QTimer.singleShot(50, lambda: self._retry_move(idx, gen))
            return

        self.setMinimumSize(0, 0)

        if self.isFullScreen():
            self.showNormal()
            QTimer.singleShot(400, lambda: self._apply_pending_move_if_any(gen))
        else:
            self._apply_pending_move()

    def _retry_move(self, idx: int, gen: int):
        if gen != self._move_generation:
            return
        self._move_to_screen(idx)

    def _apply_pending_move_if_any(self, gen: int | None = None):
        if gen is not None and gen != self._move_generation:
            return
        if self._pending_target_geo is not None:
            self._apply_pending_move()

    def _apply_pending_move(self):
        target_geo = self._pending_target_geo
        target_screen = self._pending_target_screen
        if target_geo is None or target_screen is None:
            return
        self._pending_target_geo = None
        self._pending_target_screen = None

        # The QScreen pointer captured earlier may have been destroyed by a
        # DPMS cycle between scheduling this call and now. Refuse to proceed
        # with a stale pointer — _on_screens_changed will re-issue with a
        # fresh one when the screen comes back.
        if target_screen not in QApplication.instance().screens():
            return

        wh = self.windowHandle()
        if wh is None:
            return
        wh.setScreen(target_screen)
        self.setGeometry(target_geo)
        gen = self._move_generation

        def _refullscreen():
            if gen != self._move_generation:
                return
            if not self.isVisible():
                return
            self.showFullScreen()
            QTimer.singleShot(0, self._restack_overlay)

        QTimer.singleShot(50, _refullscreen)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            # Mutter ack'd un-fullscreen — NOW the ConfigureRequest is honored.
            if self._pending_target_geo is not None and not self.isFullScreen():
                self._apply_pending_move()

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
        """Place the window on the configured screen. Always UUID-driven, no index fallback."""
        # show() first: maps window. 300ms delay: Mutter processes MapNotify
        # fully before ConfigureRequest is sent.
        self.show()
        gen = self._move_generation
        def _deferred_move():
            if gen != self._move_generation:
                return
            self._move_to_screen_by_uuid(self._config.get('screen_uuid'))
        QTimer.singleShot(300, _deferred_move)
        # Hide from GNOME Dash / Alt+Tab without using Qt.WindowType.Tool (which
        # would re-introduce the cross-monitor placement bug). Set SKIP_TASKBAR
        # and SKIP_PAGER via wmctrl after the window is mapped.
        QTimer.singleShot(500, self._apply_skip_taskbar_pager)

    def _apply_skip_taskbar_pager(self):
        import subprocess  # nosec B404 - fixed argv, no shell, no user input
        wid = self.winId()
        if not wid:
            return
        try:
            subprocess.run(  # nosec B603 B607 - fixed argv, hex(winId) only
                ['wmctrl', '-i', '-r', hex(int(wid)),
                 '-b', 'add,skip_taskbar,skip_pager'],
                check=False, capture_output=True, timeout=2)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # wmctrl missing or timed out — non-fatal


_lock_file = None  # module-level ref keeps the fd alive so the lock is never released


def main():
    import fcntl
    import argparse
    import os
    from thermalcanary import APP_UUID

    # First-run setup runs in the parent so the user sees the output on their terminal.
    _desktop = Path.home() / '.local/share/applications/thermalcanary.desktop'
    if not _desktop.exists():
        try:
            from thermalcanary._setup import main as _do_setup
            _do_setup()
        except Exception:  # nosec B110
            pass

    # Daemonize: fork so the terminal is released immediately.
    # --foreground skips the fork (useful for debugging).
    if '--foreground' not in sys.argv:
        if os.fork() > 0:
            os._exit(0)  # parent exits hard — bash waitpid() returns, prompt reappears
        os.setsid()  # child: new session, detach from controlling terminal
        # Redirect stdin/stdout/stderr to /dev/null so the TTY is fully released.
        _devnull_r = os.open(os.devnull, os.O_RDONLY)
        _devnull_w = os.open(os.devnull, os.O_WRONLY)
        os.dup2(_devnull_r, 0)
        os.dup2(_devnull_w, 1)
        os.dup2(_devnull_w, 2)
        os.close(_devnull_r)
        os.close(_devnull_w)

    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--app-id', default=APP_UUID)
    ap.parse_known_args()  # consume --app-id so Qt doesn't see it as unknown arg

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
    app.setQuitOnLastWindowClosed(False)

    fallback_icon_file = (
        Path(os.environ.get('XDG_DATA_HOME', '~/.local/share')).expanduser()
        / 'icons' / 'hicolor' / '48x48' / 'apps' / 'thermalcanary.png'
    )
    icon = QIcon.fromTheme('thermalcanary', QIcon(str(fallback_icon_file)))
    app.setWindowIcon(icon)

    config = Config()
    config.clamp_screen_indices(app.screens())
    config.save_now()

    from thermalcanary.first_run import run_if_needed
    run_if_needed(config)

    win = ThermalCanary(config, icon=icon)
    win.place_on_screen()
    sys.exit(app.exec())
