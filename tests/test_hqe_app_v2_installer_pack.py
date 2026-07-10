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


def test_installer_pack_created(tmp_path):
    module = load("hqe_app_v2_installer_pack_builder.py", "installer_pack_test")
    payload = module.build_installer_pack(
        fake_release(tmp_path),
        tmp_path / "output",
        "2.0.0-test",
        str(REPO),
        r"D:\HQE_BACKTEST_RUNS\ACTIVE",
    )

    package = Path(payload["package_dir"])
    assert payload["installer_status"] == "PASS"
    assert (package / "INSTALL_HQE_APP_V2.cmd").exists()
    assert (package / "INSTALL_HQE_APP_V2.ps1").exists()
    assert (package / "UNINSTALL_HQE_APP_V2.cmd").exists()
    assert (package / "LAUNCH_HQE_APP_V2.cmd").exists()
    assert (package / "HQE_APP_V2_INSTALLER_MANIFEST.json").exists()
    assert payload["real_orders_enabled"] is False


def test_installer_scripts_are_no_admin_and_safe(tmp_path):
    module = load("hqe_app_v2_installer_pack_builder.py", "installer_safety_test")
    payload = module.build_installer_pack(
        fake_release(tmp_path),
        tmp_path / "output",
        "2.0.0-test",
        str(REPO),
        r"D:\HQE_BACKTEST_RUNS\ACTIVE",
    )

    package = Path(payload["package_dir"])
    install_text = (package / "INSTALL_HQE_APP_V2.ps1").read_text(encoding="utf-8")
    launch_text = (package / "LAUNCH_HQE_APP_V2.cmd").read_text(encoding="utf-8")

    assert "LOCALAPPDATA" in install_text
    assert "WScript.Shell" in install_text
    assert "runas" not in install_text.lower()
    assert "--repo-root" in launch_text
    assert "place_order" not in launch_text.lower()


def test_install_verify_payload(tmp_path):
    module = load("hqe_app_v2_install_verify.py", "install_verify_test")

    install = tmp_path / "installed"
    required = [
        "LAUNCH_HQE_APP_V2.cmd",
        "scripts/hqe_app_v2_preflight.py",
        "scripts/hqe_product_app_v2.py",
        "scripts/hqe_multi_broker_data_architecture.py",
        "assets/HQE_PRODUCT_APP.ico",
        "HQE_APP_V2_VERSION.json",
        "HQE_APP_V2_INSTALLER_MANIFEST.json",
    ]

    for rel in required:
        path = install / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")

    payload = module.build_payload(install, "2.0.0-test")

    assert payload["install_verify_status"] == "PASS"
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
