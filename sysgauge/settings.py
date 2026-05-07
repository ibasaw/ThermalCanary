from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QLabel, QSpinBox, QComboBox, QPushButton,
                              QFrame, QColorDialog, QSizePolicy,
                              QApplication)
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
    def __init__(self, config: Config, worker, parent=None):
        super().__init__(parent)
        self._config = config
        self._worker = worker
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
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
            QSpinBox::up-button, QSpinBox::down-button { width: 16px; }
            QSlider::groove:horizontal {
                background: #332e55; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal {
                background: #7c6ef5; width: 14px; height: 14px;
                margin: -5px 0; border-radius: 7px; }
            QSlider::sub-page:horizontal { background: #7c6ef5; border-radius: 2px; }
        """)

        cfg = self._config
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 20, 16, 16)
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
        self._screen_combo = QComboBox()
        screens = QApplication.instance().screens()
        for i, s in enumerate(screens):
            g = s.availableGeometry()
            self._screen_combo.addItem(f'Monitor {i + 1}  ({g.width()}×{g.height()})')
        self._screen_combo.setCurrentIndex(
            min(cfg.get('screen_index'), len(screens) - 1))
        self._screen_combo.currentIndexChanged.connect(
            lambda i: cfg.set('screen_index', i))
        form.addRow('Monitor', self._screen_combo)

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

        reset_btn = QPushButton('Reset to defaults')
        reset_btn.setStyleSheet(
            'QPushButton { background:#2d2850; border:1px solid #443e70; '
            'border-radius:4px; padding:8px; color:#aaa; }'
            'QPushButton:hover { background:#3d3870; color:#fff; }')
        reset_btn.clicked.connect(self._reset)
        outer.addWidget(reset_btn)

    def _reset(self):
        cfg = self._config
        for k, v in DEFAULTS.items():
            cfg.set(k, v)
        self._poll_spin.setValue(DEFAULTS['poll_ms'])
        self._smooth_spin.setValue(DEFAULTS['smooth_n'])
        for key, btn in self._color_btns.items():
            btn.set_color(DEFAULTS[key])
        idx = min(DEFAULTS['screen_index'], self._screen_combo.count() - 1)
        self._screen_combo.setCurrentIndex(idx)
