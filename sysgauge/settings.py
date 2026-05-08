from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QLabel, QSpinBox, QComboBox, QPushButton,
                              QFrame, QColorDialog, QSizePolicy,
                              QApplication, QStackedWidget, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from sysgauge.config import Config, DEFAULTS

SIDEBAR_W = 320


class ColorButton(QPushButton):
    color_changed = pyqtSignal(str)

    def __init__(self, hex_color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 28)
        self.set_color(hex_color)
        self.clicked.connect(self._pick)

    def set_color(self, hex_color: str):
        self._hex = hex_color
        self.setStyleSheet(
            f'background:{hex_color}; border:1px solid #555; border-radius:4px;')

    def _pick(self):
        col = QColorDialog.getColor(QColor(self._hex), self, 'Pick color')
        if col.isValid():
            self.set_color(col.name())
            self.color_changed.emit(col.name())


class SettingsSidebar(QWidget):
    def __init__(self, config: Config, worker, parent=None, pro=None):
        super().__init__(parent)
        self._config = config
        self._worker = worker
        self._pro = pro
        self._session_panel = None
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self._build_ui()

    def _section(self, form: QFormLayout, text: str):
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            'color:#7c6ef5; font-size:10px; font-weight:bold;'
            'letter-spacing:2px; margin-top:10px;')
        form.addRow(lbl)

    def _build_ui(self):
        self.setStyleSheet("""
            SettingsSidebar { background: #1a1630; }
            QWidget { background: #1a1630; color: #ccc; font-family: Inter; }
            QSpinBox, QComboBox {
                background: #252040; border: 1px solid #443e70;
                border-radius: 4px; padding: 4px 8px; color: #eee; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox::down-arrow { width: 10px; height: 10px; }
            QComboBox QAbstractItemView {
                background: #252040; color: #eee;
                border: 1px solid #443e70;
                selection-background-color: #3d3870;
                selection-color: #fff;
                outline: none; }
            QSpinBox::up-button, QSpinBox::down-button { width: 16px; }
            QSlider::groove:horizontal {
                background: #332e55; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal {
                background: #7c6ef5; width: 14px; height: 14px;
                margin: -5px 0; border-radius: 7px; }
            QSlider::sub-page:horizontal { background: #7c6ef5; border-radius: 2px; }
        """)

        cfg = self._config

        self._stack = QStackedWidget(self)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._stack)

        settings_page = QWidget()
        outer = QVBoxLayout(settings_page)
        outer.setContentsMargins(16, 48, 16, 16)
        outer.setSpacing(6)

        title = QLabel('Settings')
        title.setStyleSheet(
            'color:#fff; font-size:16px; font-weight:bold; margin-bottom:4px;')
        outer.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet('color:#332e55; margin-bottom:4px;')
        outer.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # Display
        self._section(form, 'Display')
        self._screens = QApplication.instance().screens()
        self._screen_combo = QComboBox()
        self._refresh_combo_items()
        si = cfg.get('screen_index')
        si = si if isinstance(si, int) and si >= 0 else 0
        self._screen_combo.setCurrentIndex(min(si, len(self._screens) - 1))
        self._screen_combo.currentIndexChanged.connect(
            lambda i: cfg.set('screen_index', i))
        form.addRow('Monitor', self._screen_combo)

        self._set_default_btn = QPushButton('Set as default')
        self._set_default_btn.setStyleSheet(
            'QPushButton { background:#2d2850; border:1px solid #443e70; '
            'border-radius:4px; padding:4px 8px; color:#aaa; font-size:11px; }'
            'QPushButton:hover { background:#3d3870; color:#fff; }')
        self._set_default_btn.clicked.connect(self._save_default_monitor)
        form.addRow('', self._set_default_btn)

        # Sampling
        self._section(form, 'Sampling')
        self._poll_spin = QSpinBox()
        self._poll_spin.setRange(100, 10000)
        self._poll_spin.setSingleStep(100)
        self._poll_spin.setSuffix(' ms')
        self._poll_spin.setValue(cfg.get('poll_ms'))
        self._poll_spin.valueChanged.connect(lambda v: cfg.set('poll_ms', v))
        form.addRow('Poll rate', self._poll_spin)

        self._smooth_spin = QSpinBox()
        self._smooth_spin.setRange(1, 60)
        self._smooth_spin.setSuffix(' samples')
        self._smooth_spin.setValue(cfg.get('smooth_n'))
        self._smooth_spin.valueChanged.connect(lambda v: cfg.set('smooth_n', v))
        form.addRow('Smoothing', self._smooth_spin)

        # Colors
        self._section(form, 'Colors')
        self._color_btns: dict[str, ColorButton] = {}
        for key, label in [
            ('bg_color',    'Background'),
            ('inner_color', 'Inner circle'),
            ('track_color', 'Arc track'),
            ('tick_color',  'Tick marks'),
        ]:
            btn = ColorButton(cfg.get(key))
            btn.color_changed.connect(lambda v, k=key: cfg.set(k, v))
            self._color_btns[key] = btn
            form.addRow(label, btn)

        outer.addLayout(form)
        outer.addStretch()

        if self._pro:
            pro_btn = QPushButton('Pro Features →')
            pro_btn.setStyleSheet(
                'QPushButton { background:#2d2850; border:1px solid #7c6ef5; '
                'border-radius:4px; padding:8px; color:#7c6ef5; font-weight:bold; }'
                'QPushButton:hover { background:#3d3870; color:#fff; border-color:#fff; }')
            pro_btn.clicked.connect(lambda: self._stack.setCurrentIndex(1))
            outer.addWidget(pro_btn)

        reset_btn = QPushButton('Reset to defaults')
        reset_btn.setStyleSheet(
            'QPushButton { background:#2d2850; border:1px solid #443e70; '
            'border-radius:4px; padding:8px; color:#aaa; }'
            'QPushButton:hover { background:#3d3870; color:#fff; }')
        reset_btn.clicked.connect(self._reset)
        outer.addWidget(reset_btn)

        self._stack.addWidget(settings_page)

        if self._pro:
            self._stack.addWidget(self._build_pro_page())

    def _build_pro_page(self) -> QWidget:
        from sysgauge_pro import LicensePanel, SessionPanel, HistoryPanel, HealthPanel

        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        back_btn = QPushButton('← Settings')
        back_btn.setStyleSheet(
            'QPushButton { background:#1a1630; border:none; border-bottom:1px solid #332e55; '
            'border-radius:0; padding:10px 16px; color:#888; text-align:left; }'
            'QPushButton:hover { color:#fff; }')
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        v.addWidget(back_btn)

        tabs = QTabWidget()
        tabs.setStyleSheet(
            'QTabWidget::pane { border:none; }'
            'QTabBar::tab { background:#252040; color:#888; padding:6px 10px; '
            'font-size:11px; border-bottom:2px solid transparent; }'
            'QTabBar::tab:selected { color:#7c6ef5; border-bottom:2px solid #7c6ef5; }'
            'QTabBar::tab:hover { color:#ccc; }')

        self._license_panel = LicensePanel()
        self._session_panel = SessionPanel()
        self._history_panel = HistoryPanel()
        self._health_panel = HealthPanel()

        self._session_panel.session_stopped.connect(lambda _: self._history_panel._load())
        self._session_panel.history_requested.connect(lambda: tabs.setCurrentWidget(self._history_panel))

        tabs.addTab(self._license_panel, 'License')
        tabs.addTab(self._session_panel, 'Sessions')
        tabs.addTab(self._history_panel, 'History')
        tabs.addTab(self._health_panel, 'Health')

        v.addWidget(tabs)
        return page

    def push_reading(self, cpu_t: float, gpu_t: float, cpu_u: float,
                     mem: float, gpu_vram: float) -> None:
        if self._session_panel is not None:
            self._session_panel.push(cpu_t, gpu_t, cpu_u, mem, gpu_vram)

    def _refresh_combo_items(self):
        default_idx = self._config.get('default_screen_index')
        current = self._screen_combo.currentIndex()
        self._screen_combo.blockSignals(True)
        self._screen_combo.clear()
        for i, s in enumerate(self._screens):
            g = s.availableGeometry()
            star = ' ★' if i == default_idx else ''
            self._screen_combo.addItem(f'Monitor {i + 1}  {g.width()}×{g.height()}{star}')
        self._screen_combo.setCurrentIndex(max(current, 0))
        self._screen_combo.blockSignals(False)

    def _save_default_monitor(self):
        idx = self._screen_combo.currentIndex()
        self._config.set('default_screen_index', idx)
        self._refresh_combo_items()

    def _reset(self):
        cfg = self._config
        # Preserve user's saved default monitor — reset everything else
        saved_default = cfg.get('default_screen_index')
        for k, v in DEFAULTS.items():
            cfg.set(k, v)
        cfg.set('default_screen_index', saved_default)
        cfg.set('screen_index', saved_default)
        self._poll_spin.setValue(DEFAULTS['poll_ms'])
        self._smooth_spin.setValue(DEFAULTS['smooth_n'])
        for key, btn in self._color_btns.items():
            btn.set_color(DEFAULTS[key])
        idx = min(saved_default, self._screen_combo.count() - 1)
        self._screen_combo.setCurrentIndex(idx)
        self._refresh_combo_items()
