# Spec: docs/specs/core-monitoring.md#sensor-autodetect--selection-ui
import psutil
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel, QComboBox)
from PyQt6.QtCore import Qt
from thermalcanary.config import Config


def detect_available_sensors() -> dict[str, list[str]]:
    sources: dict[str, list[str]] = {'cpu_temp': ['auto'], 'fan': ['auto']}
    try:
        for chip, entries in psutil.sensors_temperatures().items():
            for e in entries:
                key = f'{chip}/{e.label}' if e.label else chip
                if key not in sources['cpu_temp']:
                    sources['cpu_temp'].append(key)
    except Exception:
        pass
    try:
        for chip, entries in psutil.sensors_fans().items():
            for e in entries:
                key = f'{chip}/{e.label}' if e.label else chip
                if key not in sources['fan']:
                    sources['fan'].append(key)
    except Exception:
        pass
    return sources


class SensorSelectWidget(QWidget):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config = config
        self._sources = detect_available_sensors()
        self._build_ui()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(6)

        header = QLabel('SENSOR SOURCES')
        header.setStyleSheet(
            'color:#7c6ef5; font-size:10px; font-weight:bold; letter-spacing:2px;')
        v.addWidget(header)

        note = QLabel('"Auto" uses the highest-priority detected source.')
        note.setStyleSheet('color:#666; font-size:10px;')
        note.setWordWrap(True)
        v.addWidget(note)

        combo_style = (
            'QComboBox { background:#252040; border:1px solid #443e70; '
            'border-radius:4px; padding:4px 8px; color:#eee; }'
            'QComboBox::drop-down { border:none; width:18px; }'
            'QComboBox QAbstractItemView { background:#252040; color:#eee; '
            'border:1px solid #443e70; selection-background-color:#3d3870; outline:none; }')

        form = QFormLayout()
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._combos: dict[str, QComboBox] = {}
        for slot, label in [('cpu_temp', 'CPU Temp'), ('fan', 'Fan')]:
            cb = QComboBox()
            cb.setStyleSheet(combo_style)
            for s in self._sources.get(slot, ['auto']):
                cb.addItem(s)
            saved = self._config.get(f'{slot}_source') or 'auto'
            idx = cb.findText(saved)
            cb.setCurrentIndex(max(0, idx))
            cb.currentTextChanged.connect(
                lambda val, k=f'{slot}_source': self._config.set(k, val))
            self._combos[slot] = cb
            form.addRow(label, cb)

        v.addLayout(form)
