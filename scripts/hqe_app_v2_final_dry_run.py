from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

VERSION = "HQE_APP_V2_FINAL_DRY_RUN_V1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_json(script: str, args: list[str]) -> Dict[str, Any]:
    cp = subprocess.run(
        [sys.executable, str(repo_root() / "scripts" / script), *args],
        cwd=str(repo_root()),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(cp.stdout)


def build(workspace: Path) -> Dict[str, Any]:
    app = run_json("hqe_product_app_v2.py", ["--workspace", str(workspace), "--status"])
    broker = run_json("hqe_broker_connect_center.py", ["--workspace", str(workspace), "--guard-check"])
    supervisor = run_json("hqe_hidden_paper_watch_supervisor.py", ["--workspace", str(workspace), "--guard-check"])
    workflow = run_json("hqe_app_v2_public_workflow.py", ["--workspace", str(workspace), "--guard-check"])
    integration = run_json("hqe_app_v2_integration_evidence.py", ["--workspace", str(workspace)])

    checks = {
        "app_v2_status_available": app.get("version") == "HQE_APP_V2_PUBLIC_TRADER_UI_V1",
        "six_brokers_present": app.get("broker_count") == 6,
        "broker_center_safe": broker.get("guard_check_status") == "PASS",
        "hidden_runner_safe": supervisor.get("guard_check_status") == "PASS",
        "public_workflow_safe": workflow.get("guard_check_status") == "PASS",
        "integration_pass": integration.get("integration_status") == "PASS",
        "internet_status_available": app.get("internet", {}).get("status") in {"ONLINE", "OFFLINE"},
        "real_orders_locked": app.get("real_orders_enabled") is False,
        "broker_execution_locked": app.get("broker_execution_enabled") is False,
        "auto_trading_locked": app.get("auto_trading_enabled") is False,
    }
    informational = {
        "today_report_available": bool(app.get("today_report_available")),
        "today_report_note": (
            "Report found in workspace."
            if app.get("today_report_available")
            else "No report found in this workspace; this does not fail architecture dry-run."
        ),
    }
    passed = all(checks.values())

    return {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "workspace": str(workspace),
        "dry_run_status": "PASS" if passed else "FAIL",
        "decision": "APP_V2_PUBLIC_WORKFLOW_READY_FOR_OPERATOR_SMOKE"
        if passed else "APP_V2_PUBLIC_WORKFLOW_REPAIR_REQUIRED",
        "checks": checks,
        "informational": informational,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def write_outputs(workspace: Path, payload: Dict[str, Any]) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    json_path = workspace / "HQE_APP_V2_FINAL_DRY_RUN.json"
    html_path = workspace / "HQE_APP_V2_FINAL_DRY_RUN.html"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    body = html.escape(json.dumps(payload, indent=2, sort_keys=True))
    html_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>HQE App V2 Final Dry Run</title>"
        "<style>body{font-family:Segoe UI;background:#0f172a;color:#e2e8f0;padding:24px}"
        "pre{background:#17213a;padding:18px;border-radius:10px;white-space:pre-wrap}"
        ".safe{color:#86efac;font-weight:bold}</style></head>"
        "<body><h1>HQE App V2 Final Dry Run</h1>"
        "<p class='safe'>PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING</p>"
        f"<pre>{body}</pre></body></html>",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE App V2 final dry run")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.workspace)
    payload = build(workspace)
    if args.write:
        write_outputs(workspace, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["dry_run_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
