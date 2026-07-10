from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

VERSION = "HQE_APP_V2_OPERATOR_SMOKE_PACK_V1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def checklist() -> List[Dict[str, Any]]:
    return [
        {"id": "APP_OPEN", "label": "HQE App V2 opens without terminal error", "required": True},
        {"id": "SAFETY_BANNER", "label": "Safe Mode banner is visible", "required": True},
        {"id": "STATUS_CARDS", "label": "Internet, broker, market data and paper watch cards are visible", "required": True},
        {"id": "BROKER_CARDS", "label": "Six broker cards are visible", "required": True},
        {"id": "BROKER_CENTER", "label": "Broker Connect Center opens", "required": True},
        {"id": "NO_ORDER_CONTROLS", "label": "No real order controls are visible", "required": True},
        {"id": "REPORT_VIEWER", "label": "Today Report button works or gives a clear no-report message", "required": True},
        {"id": "EVIDENCE_FOLDER", "label": "Evidence folder button opens workspace", "required": True},
        {"id": "PAPER_WATCH", "label": "Paper Watch start/stop buttons are present", "required": True},
        {"id": "LAYOUT", "label": "Text is readable and no control is clipped at 1020x680 or larger", "required": True},
    ]


def build_payload(workspace: Path) -> Dict[str, Any]:
    launcher = repo_root() / "OPEN_HQE_APP_V2.cmd"
    return {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "workspace": str(workspace),
        "operator_smoke_status": "READY_FOR_MANUAL_REVIEW",
        "launcher": str(launcher),
        "launcher_exists": launcher.exists(),
        "checklist": checklist(),
        "required_check_count": sum(1 for item in checklist() if item["required"]),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def write_outputs(workspace: Path, payload: Dict[str, Any]) -> None:
    workspace.mkdir(parents=True, exist_ok=True)

    json_path = workspace / "HQE_APP_V2_OPERATOR_SMOKE_PACK.json"
    md_path = workspace / "HQE_APP_V2_OPERATOR_SMOKE_CHECKLIST.md"
    launch_path = workspace / "RUN_HQE_APP_V2_OPERATOR_SMOKE.cmd"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# HQE App V2 Operator Smoke Checklist",
        "",
        "Safety: PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING",
        "",
    ]
    for item in payload["checklist"]:
        lines.append(f"- [ ] {item['label']}")
    lines.extend([
        "",
        "## Result",
        "",
        "- [ ] PASS: All required checks completed",
        "- [ ] FAIL: One or more required checks failed",
        "",
        "This is not a profitability claim.",
    ])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    launch_path.write_text(
        "@echo off\n"
        "setlocal\n"
        f'cd /d "{repo_root()}"\n'
        'call "OPEN_HQE_APP_V2.cmd"\n'
        "endlocal\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE App V2 operator smoke pack")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    payload = build_payload(workspace)

    if args.write:
        write_outputs(workspace, payload)

    if args.launch:
        launcher = repo_root() / "OPEN_HQE_APP_V2.cmd"
        subprocess.Popen([str(launcher)], cwd=str(repo_root()), shell=True)
        payload["launch_requested"] = True

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["launcher_exists"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
