# Spec: docs/specs/core-monitoring.md#first-run-monitor-picker
import glob
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QListWidget, QListWidgetItem, QPushButton, QWidget)
from PyQt6.QtCore import Qt


def _detect_gpus() -> list[dict]:
    gpus = []

    # Nvidia via NVML
    try:
        import pynvml
        pynvml.nvmlInit()
        for i in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(h)
            gpus.append({'index': i, 'name': name, 'backend': 'nvml'})
    except Exception:
        pass

    # AMD + Intel via sysfs hwmon
    _SYSFS_BACKENDS = {'amdgpu': 'amdgpu', 'xe': 'intel', 'i915': 'intel'}
    _VENDOR_LABELS  = {'amdgpu': 'AMD', 'intel': 'Intel'}
    seen_cards: set[str] = set()
    for name_path in sorted(glob.glob('/sys/class/drm/card*/device/hwmon/hwmon*/name')):
        try:
            hwmon_name = open(name_path).read().strip()
            backend = _SYSFS_BACKENDS.get(hwmon_name)
            if not backend:
                continue
            card = name_path.split('/')[4]
            if card in seen_cards:
                continue
            seen_cards.add(card)
            vendor = _VENDOR_LABELS[backend]
            gpus.append({
                'index': len(gpus),
                'name': f'{vendor} GPU ({card})',
                'backend': backend,
                'card': card,
            })
        except OSError:
            pass

    return gpus


class _FirstRunDialog(QDialog):
    def __init__(self, gpus: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._gpus = gpus
        self._selected: dict | None = None
        self._build_ui()

    def _build_ui(self):
        wrap = QWidget(self)
        wrap.setObjectName('wrap')
        wrap.setStyleSheet(
            '#wrap { background:#1a1630; border:1px solid #443e70; border-radius:12px; }')

        v = QVBoxLayout(wrap)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(14)

        title = QLabel('Welcome to Thermal Canary')
        title.setStyleSheet('font-size:16px; font-weight:bold; color:#fff; font-family:Inter;')
        v.addWidget(title)

        subtitle = QLabel('Select the GPU you want to monitor:')
        subtitle.setStyleSheet('color:#aaa; font-size:12px; font-family:Inter;')
        v.addWidget(subtitle)

        self._list = QListWidget()
        self._list.setStyleSheet(
            'QListWidget { background:#252040; border:1px solid #443e70; '
            'border-radius:4px; color:#eee; font-family:Inter; }'
            'QListWidget::item { padding:6px; }'
            'QListWidget::item:selected { background:#3d3870; color:#fff; }')
        for gpu in self._gpus:
            self._list.addItem(QListWidgetItem(gpu['name']))
        if self._gpus:
            self._list.setCurrentRow(0)
        v.addWidget(self._list)

        row = QHBoxLayout()
        row.addStretch()
        ok_btn = QPushButton('Start Monitoring')
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet(
            'QPushButton { background:#7c6ef5; border:none; border-radius:4px; '
            'padding:8px 18px; color:#fff; font-weight:bold; font-family:Inter; }'
            'QPushButton:hover { background:#9080ff; }')
        ok_btn.clicked.connect(self._accept)
        row.addWidget(ok_btn)
        v.addLayout(row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(wrap)

    def _accept(self):
        row = self._list.currentRow()
        if 0 <= row < len(self._gpus):
            self._selected = self._gpus[row]
        self.accept()

    def selected_gpu(self) -> dict | None:
        return self._selected


def _apply_gpu(config, gpu: dict) -> None:
    config.set('gpu_index',   gpu['index'])
    config.set('gpu_backend', gpu['backend'])
    if 'card' in gpu:
        config.set('gpu_card', gpu['card'])


def run_if_needed(config) -> None:
    if config.get('first_run_done'):
        return
    gpus = _detect_gpus()
    if len(gpus) <= 1:
        # Single GPU — auto-configure silently
        if gpus:
            _apply_gpu(config, gpus[0])
        config.set('first_run_done', True)
        return
    dlg = _FirstRunDialog(gpus)
    dlg.exec()
    if dlg.selected_gpu():
        _apply_gpu(config, dlg.selected_gpu())
    config.set('first_run_done', True)
