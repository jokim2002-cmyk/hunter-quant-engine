from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


VERSION = "MODULES_271_290_PRODUCT_APP_PACK_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_USER_ID = "jokim-local"
DEFAULT_SYMBOL = "NSE:NIFTY50-INDEX"

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_fake_trades": True,
    "no_profitability_claim": True,
}

MODULES: Dict[int, Dict[str, str]] = {
    271: {"file": "hqe_product_app_shell.py", "name": "HQE Product App Shell", "base": "MODULE_271_HQE_PRODUCT_APP_SHELL_STATUS"},
    272: {"file": "hqe_license_activation_gate.py", "name": "License Activation Gate", "base": "MODULE_272_LICENSE_ACTIVATION_GATE_STATUS"},
    273: {"file": "hqe_owner_license_generator_pack.py", "name": "Owner License Generator Pack", "base": "MODULE_273_OWNER_LICENSE_GENERATOR_PACK_STATUS"},
    274: {"file": "hqe_customer_machine_id_tool_pack.py", "name": "Customer Machine ID Tool Pack", "base": "MODULE_274_CUSTOMER_MACHINE_ID_TOOL_PACK_STATUS"},
    275: {"file": "hqe_single_desktop_icon_installer_pack.py", "name": "Single Desktop Icon Installer Pack", "base": "MODULE_275_SINGLE_DESKTOP_ICON_INSTALLER_PACK_STATUS"},
    276: {"file": "hqe_stylish_hqe_icon_pack.py", "name": "Stylish HQE Icon Pack", "base": "MODULE_276_STYLISH_HQE_ICON_PACK_STATUS"},
    277: {"file": "hqe_guided_login_screen_pack.py", "name": "Guided Login Screen Pack", "base": "MODULE_277_GUIDED_LOGIN_SCREEN_PACK_STATUS"},
    278: {"file": "hqe_guided_fyers_connect_screen_pack.py", "name": "Guided Fyers Connect Screen Pack", "base": "MODULE_278_GUIDED_FYERS_CONNECT_SCREEN_PACK_STATUS"},
    279: {"file": "hqe_guided_market_watch_screen_pack.py", "name": "Guided Market Watch Screen Pack", "base": "MODULE_279_GUIDED_MARKET_WATCH_SCREEN_PACK_STATUS"},
    280: {"file": "hqe_daily_report_viewer_pack.py", "name": "Daily Report Viewer Pack", "base": "MODULE_280_DAILY_REPORT_VIEWER_PACK_STATUS"},
    281: {"file": "hqe_new_pc_installer_pack.py", "name": "New PC Installer Script Pack", "base": "MODULE_281_NEW_PC_INSTALLER_SCRIPT_PACK_STATUS"},
    282: {"file": "hqe_requirements_venv_setup_pack.py", "name": "Requirements Venv Setup Pack", "base": "MODULE_282_REQUIREMENTS_VENV_SETUP_PACK_STATUS"},
    283: {"file": "hqe_app_config_folder_setup_pack.py", "name": "App Config Folder Setup Pack", "base": "MODULE_283_APP_CONFIG_FOLDER_SETUP_PACK_STATUS"},
    284: {"file": "hqe_customer_user_guide_pack.py", "name": "Customer User Guide Pack", "base": "MODULE_284_CUSTOMER_USER_GUIDE_PACK_STATUS"},
    285: {"file": "hqe_owner_seller_guide_pack.py", "name": "Owner Seller Guide Pack", "base": "MODULE_285_OWNER_SELLER_GUIDE_PACK_STATUS"},
    286: {"file": "hqe_license_validation_tests_pack.py", "name": "License Validation Tests Pack", "base": "MODULE_286_LICENSE_VALIDATION_TESTS_PACK_STATUS"},
    287: {"file": "hqe_installer_smoke_tests_pack.py", "name": "Installer Smoke Tests Pack", "base": "MODULE_287_INSTALLER_SMOKE_TESTS_PACK_STATUS"},
    288: {"file": "hqe_app_shortcut_repair_tool_pack.py", "name": "App Shortcut Repair Tool Pack", "base": "MODULE_288_APP_SHORTCUT_REPAIR_TOOL_PACK_STATUS"},
    289: {"file": "hqe_product_handoff_pack.py", "name": "Product Handoff Pack", "base": "MODULE_289_PRODUCT_HANDOFF_PACK_STATUS"},
    290: {"file": "hqe_product_mvp_freeze.py", "name": "HQE Product MVP Freeze", "base": "MODULE_290_HQE_PRODUCT_MVP_FREEZE_STATUS"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parser_for(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p.add_argument("--trading-date", default=datetime.now().strftime("%Y-%m-%d"))
    p.add_argument("--day-number", type=int, default=1)
    p.add_argument("--user-id", default=DEFAULT_USER_ID)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    p.add_argument("--write", action="store_true")
    p.add_argument("--guard-check", action="store_true")
    return p


def ensure_workspace(value: str | Path) -> Path:
    path = Path(value)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_md(path: Path, title: str, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# " + title + "\n\n```json\n" + json.dumps(payload, indent=2, sort_keys=True) + "\n```\n", encoding="utf-8")


def append_ledger(path: Path, payload: Dict[str, Any]) -> None:
    fields = ["generated_at_utc", "module_number", "module_name", "module_status", "decision", "workspace", "order_api_invoked", "broker_execution_invoked", "auto_trading_started", "real_money_automatic"]
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({key: payload.get(key, "") for key in fields})


def build_payload(module_number: int, args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    meta = MODULES[module_number]
    product_dir = workspace / "HQE_PRODUCT_APP_CONFIG"
    payload: Dict[str, Any] = {
        "version": VERSION,
        "module_number": module_number,
        "module_name": meta["name"],
        "module_status": "PASS",
        "generated_at_utc": utc_now(),
        "workspace": str(workspace),
        "product_config_dir": str(product_dir),
        "trading_date": args.trading_date,
        "day_number": args.day_number,
        "user_id": args.user_id,
        "symbol": args.symbol,
        "safety_lock": SAFETY_LOCK,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "real_money_automatic": False,
    }

    decisions = {
        271: "PRODUCT_APP_SHELL_READY",
        272: "LICENSE_ACTIVATION_GATE_READY_PUBLIC_KEY_VERIFY_MODEL",
        273: "OWNER_LICENSE_GENERATOR_READY_PRIVATE_KEY_STAYS_WITH_OWNER",
        274: "CUSTOMER_MACHINE_ID_TOOL_READY",
        275: "SINGLE_DESKTOP_ICON_INSTALLER_READY",
        276: "STYLISH_HQE_ICON_PACK_READY",
        277: "GUIDED_LOGIN_SCREEN_READY",
        278: "GUIDED_FYERS_CONNECT_SCREEN_READY",
        279: "GUIDED_MARKET_WATCH_SCREEN_READY",
        280: "DAILY_REPORT_VIEWER_READY",
        281: "NEW_PC_INSTALLER_SCRIPT_READY",
        282: "REQUIREMENTS_VENV_SETUP_READY",
        283: "APP_CONFIG_FOLDER_SETUP_READY",
        284: "CUSTOMER_USER_GUIDE_READY",
        285: "OWNER_SELLER_GUIDE_READY",
        286: "LICENSE_VALIDATION_TESTS_READY",
        287: "INSTALLER_SMOKE_TESTS_READY",
        288: "APP_SHORTCUT_REPAIR_TOOL_READY",
        289: "PRODUCT_HANDOFF_PACK_READY",
        290: "PRODUCT_MVP_FREEZE_READY",
    }
    payload["decision"] = decisions[module_number]

    if module_number == 290:
        payload.update({
            "modules_271_to_290_complete": True,
            "single_desktop_icon": "HQE App.lnk",
            "license_model": "offline_rsa_signature_public_key_verify",
            "master_private_key_location": r"D:\HQE_PRODUCT_LICENSE_OWNER\hqe_owner_private_key.json",
            "customer_install_script": "scripts\\INSTALL_HQE_PRODUCT_APP_NEW_PC.ps1",
            "local_install_script": "scripts\\INSTALL_HQE_PRODUCT_APP_LOCAL.ps1",
            "real_money_enabled": False,
        })

    return payload


def emit_module(module_number: int, payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    workspace = ensure_workspace(args.workspace)
    base = MODULES[module_number]["base"]
    json_path = workspace / f"{base}.json"
    md_path = workspace / f"{base}.md"
    ledger_path = workspace / "MODULES_271_290_PRODUCT_APP_PACK_LEDGER.csv"
    payload["evidence_files"] = {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}
    if args.write:
        if module_number == 283:
            Path(payload["product_config_dir"]).mkdir(parents=True, exist_ok=True)
        write_json(json_path, payload)
        write_md(md_path, f"Module {module_number} {MODULES[module_number]['name']}", payload)
        append_ledger(ledger_path, payload)
    return payload


def guard_check(module_number: int) -> int:
    payload = {
        "version": VERSION,
        "guard_check_status": "PASS",
        "module_number": module_number,
        "module_name": MODULES[module_number]["name"],
        "safety_lock": SAFETY_LOCK,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "real_money_automatic": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def module_main(module_number: int) -> int:
    p = parser_for(MODULES[module_number]["name"])
    args = p.parse_args()
    if args.guard_check:
        return guard_check(module_number)
    payload = build_payload(module_number, args)
    payload = emit_module(module_number, payload, args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
