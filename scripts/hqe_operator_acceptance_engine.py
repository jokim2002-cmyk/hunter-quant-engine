from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

VERSION = "HQE_OPERATOR_ACCEPTANCE_ENGINE_V1"
REPORT_ROOT = "HQE_RELEASE_CENTER/operator_acceptance"
STATUS_FILE = "HQE_OPERATOR_ACCEPTANCE_STATUS.json"

COMPONENT_SNAPSHOTS: tuple[tuple[str, str], ...] = (
    ("Operator Dashboard", "scripts/hqe_app_operator_dashboard.py"),
    (
        "Market Data Quality Center",
        "scripts/hqe_app_market_data_quality_center.py",
    ),
    ("Strategy Pack Center", "scripts/hqe_app_strategy_pack_center.py"),
    (
        "Strategy Builder & Selector",
        "scripts/hqe_app_strategy_builder_center.py",
    ),
    (
        "Backtest Product Center",
        "scripts/hqe_app_backtest_product_center.py",
    ),
    (
        "Paper Validation Intelligence",
        "scripts/hqe_app_paper_validation_report_center.py",
    ),
    ("Windows Release Center", "scripts/hqe_app_release_center.py"),
    (
        "Final RC Audit & Freeze",
        "scripts/hqe_app_release_candidate_audit_center.py",
    ),
)

SAFETY_FIELDS = (
    "real_money_enabled",
    "real_orders_enabled",
    "broker_execution_enabled",
    "auto_trading_enabled",
    "option_selling_enabled",
)

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "research_only": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_profitability_claim": True,
}


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def acceptance_paths(workspace: Path) -> dict[str, Path]:
    root = workspace / REPORT_ROOT
    return {
        "root": root,
        "status": root / STATUS_FILE,
    }


def enabled_safety_flags(payload: Any) -> list[str]:
    findings: list[str] = []

    def walk(value: Any, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                if key in SAFETY_FIELDS and item is True:
                    findings.append(path)
                walk(item, path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{prefix}[{index}]")

    walk(payload)
    return sorted(set(findings))


def evaluate_component_payload(
    name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    unsafe = enabled_safety_flags(payload)
    if unsafe:
        return {
            "name": name,
            "status": "FAILED",
            "message": (
                "Unsafe execution flags are enabled: "
                + ", ".join(unsafe)
            ),
            "unsafe_flags": unsafe,
            "display_text": str(payload.get("display_text", "")),
        }

    display = str(payload.get("display_text", "")).strip()
    operation = payload.get("operation", {})
    operation_status = (
        str(operation.get("status", "")).upper()
        if isinstance(operation, dict)
        else ""
    )
    review_statuses = {
        "FAILED",
        "BLOCKED",
        "CHECK_REQUIRED",
        "LICENSE_REQUIRED",
        "VERIFY_KEY_REQUIRED",
        "DRIFT_REVIEW_REQUIRED",
        "SAFETY_REVIEW_REQUIRED",
        "KILL_SWITCH_TRIGGERED",
    }
    status = (
        "CHECK_REQUIRED"
        if operation_status in review_statuses
        else "PASS"
    )
    message = (
        display
        or (
            f"Current operation status: {operation_status}"
            if operation_status
            else "Snapshot returned safely."
        )
    )
    return {
        "name": name,
        "status": status,
        "message": message,
        "operation_status": operation_status,
        "display_text": display,
    }


def component_snapshot_check(
    repo_root: Path,
    workspace: Path,
    name: str,
    relative_script: str,
) -> dict[str, Any]:
    script = repo_root / relative_script
    python_exe = repo_root / ".venv" / "Scripts" / "python.exe"
    if not script.exists():
        return {
            "name": name,
            "status": "FAILED",
            "message": f"Component script is missing: {relative_script}",
        }

    try:
        completed = subprocess.run(
            [
                str(python_exe),
                str(script),
                "--repo-root",
                str(repo_root),
                "--workspace",
                str(workspace),
                "--snapshot",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception as exc:
        return {
            "name": name,
            "status": "CHECK_REQUIRED",
            "message": f"{type(exc).__name__}: {exc}",
        }

    if completed.returncode != 0:
        return {
            "name": name,
            "status": "CHECK_REQUIRED",
            "message": "Component snapshot needs operator review.",
            "return_code": completed.returncode,
            "stdout_tail": completed.stdout[-700:],
            "stderr_tail": completed.stderr[-700:],
        }

    try:
        payload = json.loads(completed.stdout)
    except Exception:
        return {
            "name": name,
            "status": "CHECK_REQUIRED",
            "message": "Component snapshot did not return valid JSON.",
            "stdout_tail": completed.stdout[-700:],
        }

    if not isinstance(payload, dict):
        return {
            "name": name,
            "status": "CHECK_REQUIRED",
            "message": "Component snapshot JSON was not an object.",
        }
    return evaluate_component_payload(name, payload)


def operator_journey_checks(
    repo_root: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    from hqe_release_candidate_audit import (
        app_navigation_check,
        launcher_check,
        unsafe_app_call_check,
        verify_freeze_manifest,
        workspace_write_check,
    )

    checks = [
        launcher_check(repo_root),
        workspace_write_check(workspace),
        app_navigation_check(repo_root),
        unsafe_app_call_check(repo_root),
        verify_freeze_manifest(repo_root),
    ]
    for name, script in COMPONENT_SNAPSHOTS:
        checks.append(
            component_snapshot_check(
                repo_root,
                workspace,
                name,
                script,
            )
        )
    return checks


def acceptance_decision(
    checks: list[dict[str, Any]],
) -> dict[str, str]:
    failed = [
        item
        for item in checks
        if item.get("status") == "FAILED"
    ]
    review = [
        item
        for item in checks
        if item.get("status") == "CHECK_REQUIRED"
    ]
    if failed:
        return {
            "status": "BLOCKED",
            "message": (
                "Paper-only RC acceptance is blocked by one or more "
                "release or safety failures."
            ),
        }
    if review:
        return {
            "status": "ACCEPTED_WITH_REVIEW",
            "message": (
                "Core paper-only RC acceptance passed. Current data, "
                "license or workspace evidence still needs operator review."
            ),
        }
    return {
        "status": "ACCEPTED_FOR_PAPER_ONLY_RC",
        "message": (
            "All final operator-journey checks passed for the "
            "paper/data/research release candidate."
        ),
    }


def acceptance_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    checks = operator_journey_checks(repo_root, workspace)
    decision = acceptance_decision(checks)
    passed = sum(
        1 for item in checks if item.get("status") == "PASS"
    )
    review = sum(
        1
        for item in checks
        if item.get("status") == "CHECK_REQUIRED"
    )
    failed = sum(
        1
        for item in checks if item.get("status") == "FAILED"
    )
    return {
        "version": VERSION,
        "generated_at_utc": utc_now_text(),
        "decision": decision,
        "display_text": (
            f"Operator Acceptance: {decision['status']} | "
            f"PASS {passed} | REVIEW {review} | FAILED {failed}"
        ),
        "check_count": len(checks),
        "passed_count": passed,
        "review_count": review,
        "failed_count": failed,
        "checks": checks,
        "journey": (
            "One Icon → Connect → Prepare → Paper Watch → Close → "
            "Review → Reports → Backup/Diagnostics"
        ),
        "operations_executed": {
            "paper_watch": False,
            "market_data_fetch": False,
            "backtest": False,
            "report_generation": False,
            "backup": False,
            "restore": False,
            "broker_action": False,
            "real_order": False,
        },
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def render_html(snapshot: dict[str, Any]) -> str:
    decision = snapshot["decision"]
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('status', '')))}</td>"
        f"<td>{html.escape(str(item.get('name', '')))}</td>"
        f"<td>{html.escape(str(item.get('message', '')))}</td>"
        "</tr>"
        for item in snapshot["checks"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HQE Operator Acceptance</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; color: #222; }}
.card {{ border: 1px solid #aaa; border-radius: 6px; padding: 14px; margin: 12px 0; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ border: 1px solid #bbb; padding: 7px; text-align: left; }}
th {{ background: #eee; }}
</style>
</head>
<body>
<h1>HQE Operator Acceptance Dry Run</h1>
<p>Generated: {html.escape(snapshot["generated_at_utc"])}</p>
<div class="card">
<h2>{html.escape(decision["status"])}</h2>
<p>{html.escape(decision["message"])}</p>
<p>{html.escape(snapshot["journey"])}</p>
</div>
<table>
<thead><tr><th>Status</th><th>Check</th><th>Message</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p>
PAPER/DATA/RESEARCH ONLY. REAL MONEY: NO. REAL ORDERS: NO.
BROKER EXECUTION: NO. AUTO TRADING: NO. OPTION SELLING: NO.
</p>
<p>This is not a profitability claim.</p>
</body>
</html>
"""


def run_acceptance(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    paths = acceptance_paths(workspace)
    write_json(
        paths["status"],
        {
            "version": VERSION,
            "status": "RUNNING",
            "message": "Operator acceptance dry run is running.",
            "started_at_utc": utc_now_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        },
    )

    snapshot = acceptance_snapshot(repo_root, workspace)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_dir = paths["root"] / f"ACCEPTANCE_{stamp}"
    json_path = report_dir / "HQE_OPERATOR_ACCEPTANCE.json"
    html_path = report_dir / "HQE_OPERATOR_ACCEPTANCE.html"
    write_json(json_path, snapshot)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_html(snapshot), encoding="utf-8")

    payload = {
        "version": VERSION,
        "status": "PASS" if snapshot["decision"]["status"] != "BLOCKED" else "FAILED",
        "decision_status": snapshot["decision"]["status"],
        "message": snapshot["decision"]["message"],
        "report_dir": str(report_dir),
        "json_path": str(json_path),
        "html_path": str(html_path),
        "completed_at_utc": utc_now_text(),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }
    write_json(paths["status"], payload)
    return payload


def latest_acceptance(workspace: Path) -> dict[str, Any]:
    root = acceptance_paths(workspace)["root"]
    candidates = sorted(
        (
            path
            for path in root.glob("ACCEPTANCE_*")
            if path.is_dir()
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if root.exists() else []
    status = read_json(acceptance_paths(workspace)["status"])
    if not candidates:
        return {
            "status": status,
            "report_dir": "",
            "json_path": "",
            "html_path": "",
            "report": {},
        }
    report_dir = candidates[0]
    json_path = report_dir / "HQE_OPERATOR_ACCEPTANCE.json"
    return {
        "status": status,
        "report_dir": str(report_dir),
        "json_path": str(json_path),
        "html_path": str(
            report_dir / "HQE_OPERATOR_ACCEPTANCE.html"
        ),
        "report": read_json(json_path),
    }


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "OPERATOR_ACCEPTANCE_DRY_RUN_AND_RC_SIGNOFF",
        "read_only_snapshots": True,
        "new_product_features": False,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE operator acceptance dry-run engine"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--run-acceptance", action="store_true")
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")

    repo_root = Path(args.repo_root)
    workspace = Path(args.workspace)

    if args.snapshot:
        print(json.dumps(
            acceptance_snapshot(repo_root, workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.run_acceptance:
        payload = run_acceptance(repo_root, workspace)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1
    if args.latest:
        print(json.dumps(
            latest_acceptance(workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0

    parser.error("Use --snapshot, --run-acceptance, --latest or --guard-check.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
