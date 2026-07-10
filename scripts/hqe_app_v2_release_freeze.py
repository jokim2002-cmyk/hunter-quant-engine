from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

VERSION = "HQE_APP_V2_RELEASE_FREEZE_V1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def git_head() -> str:
    cp = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(repo_root()),
        capture_output=True,
        text=True,
        check=True,
    )
    return cp.stdout.strip()


def build(workspace: Path) -> Dict[str, Any]:
    smoke = read_json(workspace / "HQE_APP_V2_MANUAL_SMOKE_RESULT.json")
    dry_run = read_json(workspace / "HQE_APP_V2_FINAL_DRY_RUN.json")
    ui_gate = read_json(workspace / "HQE_APP_V2_UI_READINESS_GATE.json")

    required_files = {
        "app_v2": repo_root() / "scripts" / "hqe_product_app_v2.py",
        "broker_center": repo_root() / "scripts" / "hqe_broker_connect_center.py",
        "hidden_supervisor": repo_root() / "scripts" / "hqe_hidden_paper_watch_supervisor.py",
        "public_launcher": repo_root() / "OPEN_HQE_APP_V2.cmd",
        "app_icon": repo_root() / "assets" / "HQE_PRODUCT_APP.ico",
    }

    checks = {
        "required_files_present": all(path.exists() for path in required_files.values()),
        "manual_smoke_pass": smoke.get("manual_smoke_pass") is True,
        "final_dry_run_pass": dry_run.get("dry_run_status") == "PASS",
        "ui_readiness_pass": ui_gate.get("ui_readiness_status") == "PASS",
        "real_orders_locked": (
            smoke.get("real_orders_enabled") is False
            and dry_run.get("real_orders_enabled") is False
            and ui_gate.get("real_orders_enabled") is False
        ),
        "broker_execution_locked": (
            smoke.get("broker_execution_enabled") is False
            and dry_run.get("broker_execution_enabled") is False
            and ui_gate.get("broker_execution_enabled") is False
        ),
        "auto_trading_locked": (
            smoke.get("auto_trading_enabled") is False
            and dry_run.get("auto_trading_enabled") is False
            and ui_gate.get("auto_trading_enabled") is False
        ),
    }

    passed = all(checks.values())

    return {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repo_head": git_head(),
        "workspace": str(workspace),
        "release_freeze_status": "PASS" if passed else "HOLD",
        "decision": (
            "HQE_APP_V2_PUBLIC_TRADER_UI_RELEASE_FROZEN"
            if passed
            else "HQE_APP_V2_RELEASE_FREEZE_WAITING_FOR_EVIDENCE"
        ),
        "checks": checks,
        "required_files": {key: str(path) for key, path in required_files.items()},
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def write_outputs(workspace: Path, payload: Dict[str, Any]) -> None:
    json_path = workspace / "HQE_APP_V2_RELEASE_FREEZE.json"
    html_path = workspace / "HQE_APP_V2_RELEASE_FREEZE.html"

    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    body = html.escape(json.dumps(payload, indent=2, sort_keys=True))
    html_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>HQE App V2 Release Freeze</title>"
        "<style>body{font-family:Segoe UI;background:#0f172a;color:#e2e8f0;padding:24px}"
        "pre{background:#17213a;padding:18px;border-radius:10px;white-space:pre-wrap}"
        ".safe{color:#86efac;font-weight:bold}</style></head><body>"
        "<h1>HQE App V2 Release Freeze</h1>"
        "<p class='safe'>PAPER ONLY / DATA ONLY / NO REAL ORDERS / "
        "NO BROKER EXECUTION / NO AUTO TRADING</p>"
        f"<pre>{body}</pre></body></html>",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE App V2 release freeze")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    payload = build(workspace)

    if args.write:
        write_outputs(workspace, payload)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["release_freeze_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
