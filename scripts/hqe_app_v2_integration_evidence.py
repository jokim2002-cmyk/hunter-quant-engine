from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

VERSION = "HQE_APP_V2_INTEGRATION_EVIDENCE_V1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_json(script: str, args: list[str]) -> Dict[str, Any]:
    cp = subprocess.run(
        [sys.executable, str(repo_root() / "scripts" / script), *args],
        cwd=str(repo_root()), capture_output=True, text=True, check=True)
    return json.loads(cp.stdout)


def build(workspace: Path) -> Dict[str, Any]:
    app = run_json("hqe_product_app_v2.py", ["--workspace", str(workspace), "--status"])
    broker = run_json("hqe_broker_connect_center.py",
                      ["--workspace", str(workspace), "--guard-check"])
    supervisor = run_json("hqe_hidden_paper_watch_supervisor.py",
                          ["--workspace", str(workspace), "--status"])
    passed = (
        app.get("broker_count") == 6
        and broker.get("guard_check_status") == "PASS"
        and supervisor.get("real_orders_enabled") is False
    )
    return {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(
            microsecond=0).isoformat(),
        "workspace": str(workspace),
        "integration_status": "PASS" if passed else "PARTIAL",
        "decision": "APP_V2_BROKER_CENTER_AND_HIDDEN_RUNNER_INTEGRATED"
        if passed else "APP_V2_INTEGRATION_REPAIR_REQUIRED",
        "app_v2": app,
        "broker_connect_center": broker,
        "hidden_runner_supervisor": supervisor,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }


def write_outputs(workspace: Path, payload: Dict[str, Any]) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "HQE_APP_V2_INTEGRATION_EVIDENCE.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    body = html.escape(json.dumps(payload, indent=2, sort_keys=True))
    (workspace / "HQE_APP_V2_INTEGRATION_EVIDENCE.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>HQE App V2 Integration Evidence</title>"
        "<style>body{font-family:Segoe UI;background:#0f172a;color:#e2e8f0;"
        "padding:24px}pre{background:#17213a;padding:18px;border-radius:10px;"
        "white-space:pre-wrap}.safe{color:#86efac;font-weight:bold}</style>"
        "</head><body><h1>HQE App V2 Integration Evidence</h1>"
        "<p class='safe'>PAPER ONLY / DATA ONLY / NO REAL ORDERS / "
        "NO BROKER EXECUTION / NO AUTO TRADING</p>"
        f"<pre>{body}</pre></body></html>", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE App V2 integration evidence")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    payload = build(Path(args.workspace))
    if args.write:
        write_outputs(Path(args.workspace), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["integration_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
