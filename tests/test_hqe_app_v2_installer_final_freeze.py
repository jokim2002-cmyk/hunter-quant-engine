from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fake_release(tmp_path: Path) -> Path:
    release = tmp_path / "release"
    (release / "scripts").mkdir(parents=True)
    (release / "assets").mkdir(parents=True)

    required = {
        "scripts/hqe_product_app_v2.py": "print('app')\n",
        "scripts/hqe_app_v2_preflight.py": "print('preflight')\n",
        "scripts/hqe_multi_broker_data_architecture.py": "BROKERS = 6\n",
        "assets/HQE_PRODUCT_APP.ico": "fake-icon",
        "START_HQE_APP_V2.cmd": "@echo off\n",
    }

    for rel, text in required.items():
        path = release / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    return release


def test_installer_pack_has_silent_launcher(tmp_path):
    module = load("hqe_app_v2_installer_pack_builder.py", "silent_installer_test")
    payload = module.build_installer_pack(
        fake_release(tmp_path),
        tmp_path / "output",
        "2.0.0-test",
        str(REPO),
        r"D:\HQE_BACKTEST_RUNS\ACTIVE",
    )

    package = Path(payload["package_dir"])
    assert payload["installer_status"] == "PASS"
    assert payload["silent_launch_enabled"] is True
    assert (package / "LAUNCH_HQE_APP_V2_SILENT.vbs").exists()

    install_text = (package / "INSTALL_HQE_APP_V2.ps1").read_text(encoding="utf-8")
    vbs_text = (package / "LAUNCH_HQE_APP_V2_SILENT.vbs").read_text(encoding="utf-8")

    assert "wscript.exe" in install_text.lower()
    assert "shortcut.arguments" in install_text.lower()
    assert "shell.run command, 0, false" in vbs_text.lower()


def test_uninstall_script_removes_shortcut_and_version(tmp_path):
    module = load("hqe_app_v2_installer_pack_builder.py", "uninstall_installer_test")
    payload = module.build_installer_pack(
        fake_release(tmp_path),
        tmp_path / "output",
        "2.0.0-test",
        str(REPO),
        r"D:\HQE_BACKTEST_RUNS\ACTIVE",
    )

    package = Path(payload["package_dir"])
    uninstall_text = (package / "UNINSTALL_HQE_APP_V2.ps1").read_text(encoding="utf-8")

    assert "Hunter Quant Engine.lnk" in uninstall_text
    assert "Remove-Item -LiteralPath $InstallRoot -Recurse -Force" in uninstall_text
    assert "CURRENT_VERSION.txt" in uninstall_text


def test_final_freeze_pass(tmp_path):
    module = load("hqe_app_v2_installer_final_freeze.py", "installer_freeze_test")

    package = tmp_path / "package"
    install = tmp_path / "install"
    shortcut = tmp_path / "Hunter Quant Engine.lnk"
    package.mkdir()
    install.mkdir()
    shortcut.write_text("shortcut", encoding="utf-8")

    (package / "HQE_APP_V2_INSTALLER_MANIFEST.json").write_text(
        '{"installer_status":"PASS","silent_launch_enabled":true,"app_version":"2.0.0-test","real_orders_enabled":false,"broker_execution_enabled":false,"auto_trading_enabled":false}',
        encoding="utf-8",
    )
    (install / "HQE_APP_V2_INSTALL_EVIDENCE.json").write_text(
        '{"silent_launch_enabled":true,"version":"2.0.0-test","real_orders_enabled":false,"broker_execution_enabled":false,"auto_trading_enabled":false}',
        encoding="utf-8",
    )
    (install / "HQE_APP_V2_INSTALL_VERIFY.json").write_text(
        '{"install_verify_status":"PASS","app_version":"2.0.0-test","real_orders_enabled":false,"broker_execution_enabled":false,"auto_trading_enabled":false}',
        encoding="utf-8",
    )
    (install / "LAUNCH_HQE_APP_V2.cmd").write_text("@echo off\n", encoding="utf-8")
    (install / "LAUNCH_HQE_APP_V2_SILENT.vbs").write_text("x", encoding="utf-8")

    payload = module.build_payload(package, install, shortcut, "2.0.0-test")

    assert payload["installer_final_freeze_status"] == "PASS"
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
