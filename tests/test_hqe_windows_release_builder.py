from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LAUNCHER = REPO / 'scripts' / 'hqe_desktop_exe_launcher.py'
BUILDER = REPO / 'scripts' / 'hqe_windows_release_builder.py'
INSTALLER = REPO / 'release' / 'HQE_INSTALL_DESKTOP_SHORTCUT.ps1'

def load_builder():
    spec = importlib.util.spec_from_file_location('hqe_windows_release_builder', BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_launcher_forwards_to_current_source_app():
    text = LAUNCHER.read_text(encoding='utf-8-sig')
    assert "'hqe_product_app_v2.py'" in text
    assert "environment['HQE_REPO_HINT'] = str(repo)" in text
    assert 'CREATE_NO_WINDOW' in text
    assert 'DIAGNOSTIC_FLAGS' in text

def test_builder_is_windowed_onefile_with_product_icon(tmp_path):
    module = load_builder()
    command = module.build_command(
        Path('python.exe'), Path('launcher.py'), Path('app.ico'),
        tmp_path / 'dist', tmp_path / 'work'
    )
    assert '--onefile' in command
    assert '--windowed' in command
    assert '--icon' in command
    assert 'HunterQuantEngine' in command

def test_installer_prefers_exe_and_keeps_source_fallback():
    text = INSTALLER.read_text(encoding='utf-8-sig')
    assert 'dist\\HunterQuantEngine.exe' in text
    assert 'if (Test-Path -LiteralPath $Exe)' in text
    assert '$TargetPath = $Pythonw' in text
    assert 'assets\\HQE_PRODUCT_APP.ico' in text
