# Spec: docs/specs/system-tray.md
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt


class TrayController:
    def __init__(self, window, icon: QIcon, config, on_quit=None, on_about=None):
        self.window = window
        self.tray = None
        self._config = config
        self._on_quit = on_quit or QApplication.instance().quit
        self._on_about = on_about

        if not QSystemTrayIcon.isSystemTrayAvailable():
            if not config.get('tray_warning_shown'):
                self._show_no_tray_warning()
                config.set('tray_warning_shown', True)
            return

        self.tray = QSystemTrayIcon(icon, parent=window)
        self.tray.setToolTip('Thermal Canary')

        menu = QMenu()
        self._show_action = QAction('Hide', menu)
        self._show_action.triggered.connect(self._toggle)
        menu.addAction(self._show_action)
        menu.addSeparator()
        if self._on_about:
            menu.addAction(QAction('About', menu, triggered=self._on_about))
        menu.addAction(QAction('Quit', menu, triggered=self._on_quit))

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activate)
        self.tray.show()

    def _show_no_tray_warning(self):
        dlg = QDialog()
        dlg.setWindowTitle('Thermal Canary')
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        dlg.setStyleSheet('background:#1a1630; color:#ccc; font-family:Inter;')
        v = QVBoxLayout(dlg)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)
        msg = QLabel(
            'System tray not detected. Window will stay in the taskbar.\n\n'
            'On GNOME, install the AppIndicator extension to enable tray mode.\n'
            'KDE Plasma, XFCE, and Sway/Hyprland require no extra setup.')
        msg.setWordWrap(True)
        msg.setStyleSheet('color:#ccc; font-size:12px;')
        v.addWidget(msg)
        btn = QPushButton('OK')
        btn.setStyleSheet(
            'QPushButton { background:#7c6ef5; border:none; border-radius:4px; '
            'padding:6px 18px; color:#fff; font-weight:bold; }'
            'QPushButton:hover { background:#9080ff; }')
        btn.clicked.connect(dlg.accept)
        v.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()

    def update_menu_label(self):
        if self.tray is None:
            return
        # Use explicit intent flag: isVisible() is unreliable after a DPMS
        # unmap where the window is gone but the user never asked to hide it.
        self._show_action.setText('Hide' if not getattr(self, '_user_hidden', False) else 'Show')

    def _toggle(self):
        if getattr(self, '_user_hidden', False):
            self._user_hidden = False
            self._raise()
        else:
            self._user_hidden = True
            self.window.hide()
        self.update_menu_label()

    def _raise(self):
        # Do NOT call setWindowFlags() here — it destroys the native QWindow
        # and forces a remap on the primary monitor. Flags are set once in
        # ThermalCanary.__init__ and must never change at runtime.
        if not QApplication.instance().screens():
            return  # all monitors asleep — _on_screens_changed will retry on wake
        self.window.place_on_screen()
        self.window.raise_()
        self.window.activateWindow()

    def _on_activate(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle()
