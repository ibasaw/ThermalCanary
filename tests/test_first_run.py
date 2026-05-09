import pytest
try:
    from thermalcanary.first_run import (
        _FirstRunDialog, _apply_gpu, run_if_needed, _detect_gpus,
    )
    _HAS_FIRST_RUN = True
except ImportError:
    _HAS_FIRST_RUN = False

pytestmark = pytest.mark.skipif(
    not _HAS_FIRST_RUN,
    reason="thermalcanary.first_run not in mutmut sandbox",
)

_GPUS = [
    {'index': 0, 'name': 'RTX 4070', 'backend': 'nvml'},
    {'index': 1, 'name': 'AMD GPU (card0)', 'backend': 'amdgpu', 'card': 'card0'},
]


def test_dialog_creates_with_gpu_list(qtbot):
    dlg = _FirstRunDialog(_GPUS)
    qtbot.addWidget(dlg)
    assert dlg.selected_gpu() is None


def test_dialog_accept_selects_current_row(qtbot):
    dlg = _FirstRunDialog(_GPUS)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(1)
    dlg._accept()
    assert dlg.selected_gpu() == _GPUS[1]


def test_dialog_accept_first_row_by_default(qtbot):
    dlg = _FirstRunDialog(_GPUS)
    qtbot.addWidget(dlg)
    dlg._accept()
    assert dlg.selected_gpu() == _GPUS[0]


def test_dialog_empty_gpu_list(qtbot):
    dlg = _FirstRunDialog([])
    qtbot.addWidget(dlg)
    dlg._accept()
    assert dlg.selected_gpu() is None


def test_apply_gpu_nvml(tmp_config):
    gpu = {'index': 2, 'name': 'RTX 4090', 'backend': 'nvml'}
    _apply_gpu(tmp_config, gpu)
    assert tmp_config.get('gpu_backend') == 'nvml'
    assert tmp_config.get('gpu_index') == 2


def test_apply_gpu_amd_sets_card(tmp_config):
    gpu = {'index': 0, 'name': 'AMD GPU', 'backend': 'amdgpu', 'card': 'card1'}
    _apply_gpu(tmp_config, gpu)
    assert tmp_config.get('gpu_backend') == 'amdgpu'
    assert tmp_config.get('gpu_card') == 'card1'


def test_apply_gpu_intel_no_card_key(tmp_config):
    gpu = {'index': 0, 'name': 'Intel GPU', 'backend': 'intel'}
    _apply_gpu(tmp_config, gpu)
    assert tmp_config.get('gpu_backend') == 'intel'


def test_run_if_needed_skips_when_done(tmp_config):
    tmp_config.set('first_run_done', True)
    run_if_needed(tmp_config)  # must return immediately without dialog


def test_run_if_needed_auto_configures_single_gpu(tmp_config, mocker):
    mocker.patch(
        'thermalcanary.first_run._detect_gpus',
        return_value=[{'index': 0, 'name': 'RTX 4070', 'backend': 'nvml'}],
    )
    run_if_needed(tmp_config)
    assert tmp_config.get('first_run_done') is True
    assert tmp_config.get('gpu_backend') == 'nvml'
    assert tmp_config.get('gpu_index') == 0


def test_run_if_needed_no_gpu_marks_done(tmp_config, mocker):
    mocker.patch('thermalcanary.first_run._detect_gpus', return_value=[])
    run_if_needed(tmp_config)
    assert tmp_config.get('first_run_done') is True


def test_run_if_needed_multi_gpu_shows_dialog(tmp_config, mocker):
    mocker.patch('thermalcanary.first_run._detect_gpus', return_value=_GPUS)
    dlg_mock = mocker.MagicMock()
    dlg_mock.selected_gpu.return_value = _GPUS[1]
    mocker.patch('thermalcanary.first_run._FirstRunDialog', return_value=dlg_mock)
    run_if_needed(tmp_config)
    dlg_mock.exec.assert_called_once()
    assert tmp_config.get('first_run_done') is True
    assert tmp_config.get('gpu_backend') == 'amdgpu'


def test_detect_gpus_returns_list(mocker):
    mocker.patch('thermalcanary.first_run.glob.glob', return_value=[])
    mocker.patch('pynvml.nvmlInit', side_effect=Exception('no nvidia'))
    result = _detect_gpus()
    assert isinstance(result, list)
