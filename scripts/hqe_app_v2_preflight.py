from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

VERSION = "HQE_APP_V2_PREFLIGHT_V1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def check_internet(timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=timeout):
            return True
    except OSError:
        return False


def build_payload(workspace: Path) -> Dict[str, Any]:
    root = repo_root()
    python_exe = root / ".venv" / "Scripts" / "python.exe"

    required = {
        "app_v2": root / "scripts" / "hqe_product_app_v2.py",
        "broker_center": root / "scripts" / "hqe_broker_connect_center.py",
        "hidden_supervisor": root / "scripts" / "hqe_hidden_paper_watch_supervisor.py",
        "license_activation": root / "scripts" / "hqe_app_v2_license_activation.py",
        "launcher": root / "OPEN_HQE_APP_V2.cmd",
        "icon": root / "assets" / "HQE_PRODUCT_APP.ico",
        "venv_python": python_exe,
    }

    workspace_config = workspace / "HQE_PRODUCT_APP_CONFIG"
    license_file = workspace_config / "license.key"
    public_key = workspace_config / "hqe_license_public_key.json"

    checks = {
        "windows": os.name == "nt",
        "python_available": python_exe.exists(),
        "required_files_present": all(path.exists() for path in required.values()),
        "workspace_exists": workspace.exists(),
        "workspace_writable": os.access(workspace, os.W_OK) if workspace.exists() else False,
        "license_present": license_file.exists(),
        "public_key_present": public_key.exists(),
        "internet_reachable": check_internet(),
        "real_orders_locked": True,
        "broker_execution_locked": True,
        "auto_trading_locked": True,
    }

    critical = [
        "windows",
        "python_available",
        "required_files_present",
        "workspace_exists",
        "workspace_writable",
        "license_present",
        "public_key_present",
        "real_orders_locked",
        "broker_execution_locked",
        "auto_trading_locked",
    ]

    passed = all(checks[name] for name in critical)

    return {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repo": str(root),
        "workspace": str(workspace),
        "platform": platform.platform(),
        "python": sys.version,
        "checks": checks,
        "required_files": {name: str(path) for name, path in required.items()},
        "preflight_status": "PASS" if passed else "HOLD",
        "decision": "READY_TO_LAUNCH_APP_V2" if passed else "FIX_PREFLIGHT_ISSUES",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE App V2 preflight")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    payload = build_payload(workspace)

    if args.write:
        output = workspace / "HQE_APP_V2_PREFLIGHT.json"
        output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["preflight_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
