# Spec: docs/specs/core-monitoring.md#sensor-autodetect--selection-ui
import psutil
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel, QComboBox)
from PyQt6.QtCore import Qt
from thermalcanary.config import Config


_HIDE_CHIPS = ('nvme', 'iwlwifi', 'pch_', 'nouveau', 'amdgpu', 'radeon', 'BAT', 'acpitz')


def detect_available_sensors() -> dict[str, list[str]]:
    """Returns list of (display_label, key) pairs under 'cpu_temp'."""
    sources: dict[str, list[tuple[str, str]]] = {'cpu_temp': [('auto', 'auto')]}
    try:
        for chip, entries in psutil.sensors_temperatures().items():
            if any(chip.startswith(p) for p in _HIDE_CHIPS):
                continue
            for e in entries:
                key = f'{chip}/{e.label}' if e.label else chip
                if any(k == key for _, k in sources['cpu_temp']):
                    continue
                label = f'{chip}/{e.label}' if e.label else chip
                sources['cpu_temp'].append((label, key))
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

        gpu_note = QLabel('GPU Fan gauge reads directly from NVML.\n0% = fans stopped (normal at low GPU load).')
        gpu_note.setStyleSheet('color:#554e80; font-size:10px;')
        gpu_note.setWordWrap(True)
        v.addWidget(gpu_note)

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
        for slot, row_label in [('cpu_temp', 'CPU Temp')]:
            cb = QComboBox()
            cb.setStyleSheet(combo_style)
            for display, key in self._sources.get(slot, [('auto', 'auto')]):
                cb.addItem(display, key)
            saved = self._config.get(f'{slot}_source') or 'auto'
            idx = cb.findData(saved)
            cb.setCurrentIndex(max(0, idx))
            cb.currentIndexChanged.connect(
                lambda _, cb=cb, k=f'{slot}_source': self._config.set(k, cb.currentData()))
            self._combos[slot] = cb
            form.addRow(row_label, cb)

        v.addLayout(form)
