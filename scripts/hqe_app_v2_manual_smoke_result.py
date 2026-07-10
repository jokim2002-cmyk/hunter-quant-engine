from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

VERSION = "HQE_APP_V2_MANUAL_SMOKE_RESULT_V1"

REQUIRED_CHECKS = [
    "APP_OPEN",
    "SAFETY_BANNER",
    "STATUS_CARDS",
    "BROKER_CARDS",
    "BROKER_CENTER",
    "NO_ORDER_CONTROLS",
    "REPORT_VIEWER",
    "EVIDENCE_FOLDER",
    "PAPER_WATCH",
    "LAYOUT",
]


def build_payload(workspace: Path, result: str, notes: str) -> Dict[str, Any]:
    normalized = result.strip().upper()
    passed = normalized == "PASS"

    checks: List[Dict[str, Any]] = [
        {
            "id": check_id,
            "status": "PASS" if passed else "NOT_CONFIRMED",
        }
        for check_id in REQUIRED_CHECKS
    ]

    return {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "workspace": str(workspace),
        "manual_smoke_result": normalized,
        "manual_smoke_pass": passed,
        "operator_notes": notes.strip(),
        "checks": checks,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def write_outputs(workspace: Path, payload: Dict[str, Any]) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    json_path = workspace / "HQE_APP_V2_MANUAL_SMOKE_RESULT.json"
    md_path = workspace / "HQE_APP_V2_MANUAL_SMOKE_RESULT.md"

    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# HQE App V2 Manual Smoke Result",
        "",
        f"- Result: `{payload['manual_smoke_result']}`",
        f"- Generated UTC: `{payload['generated_at_utc']}`",
        f"- Workspace: `{payload['workspace']}`",
        "",
        "## Checks",
        "",
    ]
    for item in payload["checks"]:
        lines.append(f"- {item['id']}: `{item['status']}`")

    lines.extend([
        "",
        "## Notes",
        "",
        payload["operator_notes"] or "No notes provided.",
        "",
        "## Safety",
        "",
        "- Real money: NO",
        "- Real orders: NO",
        "- Broker execution: NO",
        "- Auto trading: NO",
        "",
        "This is not a profitability claim.",
    ])

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE App V2 manual smoke result")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--result", required=True, choices=["PASS", "FAIL", "pass", "fail"])
    parser.add_argument("--notes", default="")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    payload = build_payload(workspace, args.result, args.notes)

    if args.write:
        write_outputs(workspace, payload)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["manual_smoke_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
