from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_license_sign_and_verify_roundtrip(tmp_path):
    lic = load_module(REPO / "scripts" / "hqe_product_license_common.py", "lic_common_test")
    public_key, private_key = lic.generate_rsa_keypair(bits=512)
    mid = "HQE-TEST-MACHINE"
    payload = lic.create_license_payload("Test Customer", "test@example.com", mid, "2099-12-31")
    key = lic.make_license_key(payload, private_key)
    result = lic.verify_license_key(key, public_key, expected_machine_id=mid)
    assert result["valid"] is True
    mismatch = lic.verify_license_key(key, public_key, expected_machine_id="HQE-OTHER")
    assert mismatch["valid"] is False
    assert mismatch["reason"] == "machine_id_mismatch"


def test_product_app_guard_check():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "hqe_product_app.py"), "--guard-check"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["guard_check_status"] == "PASS"
    assert payload["no_real_orders"] is True
    assert payload["no_broker_execution"] is True


def test_icon_generator_creates_ico(tmp_path):
    out = tmp_path / "HQE.ico"
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "hqe_product_app_icon.py"), "--output", str(out)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "ICON_WRITTEN" in result.stdout
    assert out.exists()
    assert out.read_bytes()[:4] == b"\x00\x00\x01\x00"


def test_product_pack_runner_creates_freeze(tmp_path):
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO / "scripts" / "RUN_MODULES_271_290_PRODUCT_APP_PACK.ps1"),
            "-Workspace",
            str(tmp_path),
            "-TradingDate",
            "2026-07-10",
            "-DayNumber",
            "1",
            "-UserId",
            "jokim-local",
            "-Symbol",
            "NSE:NIFTY50-INDEX",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "MODULES_271_290_PRODUCT_APP_PACK_SAFE_RUN_COMPLETE" in result.stdout
    final_json = tmp_path / "MODULE_290_HQE_PRODUCT_MVP_FREEZE_STATUS.json"
    assert final_json.exists()
    payload = json.loads(final_json.read_text(encoding="utf-8"))
    assert payload["modules_271_to_290_complete"] is True
    assert payload["real_money_enabled"] is False


def test_local_installer_script_present():
    assert (REPO / "scripts" / "INSTALL_HQE_PRODUCT_APP_LOCAL.ps1").exists()
    assert (REPO / "scripts" / "INSTALL_HQE_PRODUCT_APP_NEW_PC.ps1").exists()
    assert (REPO / "docs" / "HQE_CUSTOMER_USER_GUIDE.md").exists()
    assert (REPO / "docs" / "HQE_OWNER_SELLER_GUIDE.md").exists()
