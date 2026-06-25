"""Tests for thermalcanary._setup (desktop-integration installer)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

try:
    from thermalcanary._setup import _DESKTOP, _AUTOSTART, _install, _uninstall, main
    _HAS_SETUP = True
except ImportError:
    _HAS_SETUP = False

pytestmark = pytest.mark.skipif(not _HAS_SETUP, reason="_setup not in sandbox")


# ---------------------------------------------------------------------------
# main() routing
# ---------------------------------------------------------------------------

def test_main_routes_to_install(mocker):
    install_mock = mocker.patch('thermalcanary._setup._install')
    uninstall_mock = mocker.patch('thermalcanary._setup._uninstall')
    mocker.patch.object(sys, 'argv', ['thermalcanary-setup'])
    main()
    install_mock.assert_called_once()
    uninstall_mock.assert_not_called()


def test_main_routes_to_uninstall(mocker):
    install_mock = mocker.patch('thermalcanary._setup._install')
    uninstall_mock = mocker.patch('thermalcanary._setup._uninstall')
    mocker.patch.object(sys, 'argv', ['thermalcanary-setup', '--uninstall'])
    main()
    uninstall_mock.assert_called_once()
    install_mock.assert_not_called()


# ---------------------------------------------------------------------------
# _install()
# ---------------------------------------------------------------------------

def test_install_creates_icon(tmp_path, mocker):
    mocker.patch('thermalcanary._setup.Path.home', return_value=tmp_path)
    fake_src = tmp_path / 'icon.png'
    fake_src.write_bytes(b'\x89PNG')
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=fake_src)
    ctx.__exit__ = MagicMock(return_value=False)
    mocker.patch('thermalcanary._setup.importlib.resources.as_file', return_value=ctx)
    mocker.patch('thermalcanary._setup.importlib.resources.files', return_value=MagicMock())
    mocker.patch('thermalcanary._setup.subprocess.run')

    _install()

    icon_dst = tmp_path / '.local/share/icons/hicolor/256x256/apps/thermalcanary.png'
    assert icon_dst.exists()


def test_install_writes_desktop_file(tmp_path, mocker):
    mocker.patch('thermalcanary._setup.Path.home', return_value=tmp_path)
    fake_src = tmp_path / 'icon.png'
    fake_src.write_bytes(b'\x89PNG')
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=fake_src)
    ctx.__exit__ = MagicMock(return_value=False)
    mocker.patch('thermalcanary._setup.importlib.resources.as_file', return_value=ctx)
    mocker.patch('thermalcanary._setup.importlib.resources.files', return_value=MagicMock())
    mocker.patch('thermalcanary._setup.subprocess.run')

    _install()

    apps = tmp_path / '.local/share/applications/thermalcanary.desktop'
    assert apps.read_text() == _DESKTOP


def test_install_writes_autostart_file(tmp_path, mocker):
    mocker.patch('thermalcanary._setup.Path.home', return_value=tmp_path)
    fake_src = tmp_path / 'icon.png'
    fake_src.write_bytes(b'\x89PNG')
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=fake_src)
    ctx.__exit__ = MagicMock(return_value=False)
    mocker.patch('thermalcanary._setup.importlib.resources.as_file', return_value=ctx)
    mocker.patch('thermalcanary._setup.importlib.resources.files', return_value=MagicMock())
    mocker.patch('thermalcanary._setup.subprocess.run')

    _install()

    autostart = tmp_path / '.config/autostart/thermalcanary.desktop'
    assert autostart.read_text() == _AUTOSTART


def test_install_calls_update_commands(tmp_path, mocker):
    mocker.patch('thermalcanary._setup.Path.home', return_value=tmp_path)
    fake_src = tmp_path / 'icon.png'
    fake_src.write_bytes(b'\x89PNG')
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=fake_src)
    ctx.__exit__ = MagicMock(return_value=False)
    mocker.patch('thermalcanary._setup.importlib.resources.as_file', return_value=ctx)
    mocker.patch('thermalcanary._setup.importlib.resources.files', return_value=MagicMock())
    run_mock = mocker.patch('thermalcanary._setup.subprocess.run')

    _install()

    cmds = [c.args[0][0] for c in run_mock.call_args_list]
    assert 'update-desktop-database' in cmds
    assert 'gtk-update-icon-cache' in cmds


# ---------------------------------------------------------------------------
# _uninstall()
# ---------------------------------------------------------------------------

def test_uninstall_removes_existing_files(tmp_path, mocker):
    mocker.patch('thermalcanary._setup.Path.home', return_value=tmp_path)
    mocker.patch('thermalcanary._setup.subprocess.run')

    desktop = tmp_path / '.local/share/applications/thermalcanary.desktop'
    autostart = tmp_path / '.config/autostart/thermalcanary.desktop'
    icon = tmp_path / '.local/share/icons/hicolor/256x256/apps/thermalcanary.png'
    for p in (desktop, autostart, icon):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('x')

    _uninstall()

    assert not desktop.exists()
    assert not autostart.exists()
    assert not icon.exists()


def test_uninstall_handles_missing_files(tmp_path, mocker):
    mocker.patch('thermalcanary._setup.Path.home', return_value=tmp_path)
    mocker.patch('thermalcanary._setup.subprocess.run')

    # No files created — should not raise
    _uninstall()


def test_uninstall_calls_update_desktop_database(tmp_path, mocker):
    mocker.patch('thermalcanary._setup.Path.home', return_value=tmp_path)
    run_mock = mocker.patch('thermalcanary._setup.subprocess.run')

    _uninstall()

    cmds = [c.args[0][0] for c in run_mock.call_args_list]
    assert 'update-desktop-database' in cmds
