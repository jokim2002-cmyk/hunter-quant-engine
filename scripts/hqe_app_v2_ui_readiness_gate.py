from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

VERSION = "HQE_APP_V2_UI_READINESS_GATE_V1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_payload() -> Dict[str, Any]:
    root = repo_root()
    app_path = root / "scripts" / "hqe_product_app_v2.py"
    broker_path = root / "scripts" / "hqe_broker_connect_center.py"
    launcher_path = root / "OPEN_HQE_APP_V2.cmd"
    icon_path = root / "assets" / "HQE_PRODUCT_APP.ico"

    app_text = app_path.read_text(encoding="utf-8-sig") if app_path.exists() else ""
    broker_text = broker_path.read_text(encoding="utf-8-sig") if broker_path.exists() else ""

    checks = {
        "app_v2_exists": app_path.exists(),
        "broker_connect_center_exists": broker_path.exists(),
        "public_launcher_exists": launcher_path.exists(),
        "app_icon_exists": icon_path.exists(),
        "safety_banner_present": "SAFE MODE ACTIVE" in app_text,
        "broker_connect_button_present": 'text="Broker Connect Center"' in app_text,
        "start_watch_button_present": 'text="Start Paper Watch"' in app_text,
        "stop_watch_button_present": 'text="Stop Paper Watch"' in app_text,
        "today_report_button_present": 'text="Open Today Report"' in app_text,
        "evidence_folder_button_present": 'text="Open Evidence Folder"' in app_text,
        "six_broker_registry_used": "BROKER_REGISTRY" in app_text,
        "credential_fields_dynamic": "definition.credential_fields" in broker_text,
        "secret_persistence_disabled": "credential_values_written_to_disk" in broker_text,
        "real_order_controls_absent": 'text="Place Order"' not in app_text,
    }

    passed = all(checks.values())
    return {
        "version": VERSION,
        "ui_readiness_status": "PASS" if passed else "FAIL",
        "decision": "APP_V2_READY_FOR_MANUAL_OPERATOR_SMOKE"
        if passed else "APP_V2_UI_REPAIR_REQUIRED",
        "checks": checks,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE App V2 UI readiness gate")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    payload = build_payload()
    if args.write:
        workspace = Path(args.workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        path = workspace / "HQE_APP_V2_UI_READINESS_GATE.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        payload["status_file"] = str(path)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ui_readiness_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
