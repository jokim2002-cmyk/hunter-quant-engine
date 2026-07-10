from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_APP_SAFETY_EVIDENCE_CENTER_V1"
STATUS_FILE = "HQE_APP_SAFETY_AUDIT_STATUS.json"

PERMANENT_SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}

GUARD_SCRIPTS = (
    "hqe_product_app_v2.py",
    "hqe_app_daily_startup_center.py",
    "hqe_app_daily_close_center.py",
    "hqe_app_market_data_center.py",
    "hqe_app_broker_data_health.py",
    "hqe_app_fyers_auth.py",
    "hqe_next_market_day_startup_pack.py",
    "hqe_validation_day_auto_rollover_plan.py",
    "hqe_daily_close_auto_report_pack.py",
)


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


def evidence_category(path: Path) -> str:
    name = path.name.upper()
    if "KILL" in name and "SWITCH" in name:
        return "kill_switch"
    if "SAFETY" in name:
        return "safety"
    if "GUARD" in name:
        return "guard"
    if "DECISION" in name:
        return "decision"
    if "STATUS" in name:
        return "status"
    return "other"


def extract_kill_switch_state(payload: dict[str, Any]) -> str:
    keys = (
        "kill_switch",
        "kill_switch_triggered",
        "kill_switch_active",
        "safety_kill_switch",
    )
    for key in keys:
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, bool):
            return "TRIGGERED" if value else "CLEAR"
        text = str(value).strip().upper()
        if text in {"YES", "TRUE", "TRIGGERED", "ACTIVE", "ON"}:
            return "TRIGGERED"
        if text in {"NO", "FALSE", "CLEAR", "INACTIVE", "OFF"}:
            return "CLEAR"
        if text:
            return text

    decision = str(payload.get("decision", "")).strip().upper()
    if "KILL" in decision and "TRIGGER" in decision:
        return "TRIGGERED"
    return "UNKNOWN"


def discover_safety_evidence(
    repo_root: Path,
    workspace: Path,
    *,
    max_files: int = 5000,
) -> list[dict[str, Any]]:
    roots = (
        workspace,
        repo_root / "reports",
        repo_root / "evidence",
        repo_root / "logs",
    )
    keywords = ("SAFETY", "GUARD", "KILL", "DECISION", "STATUS")
    candidates: list[Path] = []
    scanned = 0

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if scanned >= max_files:
                break
            if not path.is_file():
                continue
            scanned += 1
            upper_name = path.name.upper()
            if not any(keyword in upper_name for keyword in keywords):
                continue
            if path.suffix.lower() not in {".json", ".txt", ".md", ".csv"}:
                continue
            candidates.append(path)

    unique = {path.resolve(): path for path in candidates}
    ordered = sorted(
        unique.values(),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    evidence: list[dict[str, Any]] = []
    for path in ordered[:250]:
        stat = path.stat()
        payload = read_json(path) if path.suffix.lower() == ".json" else {}
        evidence.append(
            {
                "name": path.name,
                "path": str(path),
                "category": evidence_category(path),
                "updated_at_utc": datetime.fromtimestamp(
                    stat.st_mtime,
                    timezone.utc,
                ).replace(microsecond=0).isoformat(),
                "size_bytes": stat.st_size,
                "kill_switch_state": extract_kill_switch_state(payload),
                "guard_check_status": str(
                    payload.get("guard_check_status", "")
                ).strip().upper(),
                "decision": str(payload.get("decision", "")).strip(),
            }
        )
    return evidence


def latest_audit_status(workspace: Path) -> dict[str, str]:
    payload = read_json(workspace / STATUS_FILE)
    return {
        "status": str(payload.get("status", "IDLE")),
        "message": str(payload.get("message", "")),
        "completed_at_utc": str(payload.get("completed_at_utc", "")),
    }


def run_guard_check(
    repo_root: Path,
    script_name: str,
) -> dict[str, Any]:
    script = repo_root / "scripts" / script_name
    if not script.exists():
        return {
            "script": script_name,
            "status": "MISSING",
            "return_code": None,
        }

    completed = subprocess.run(
        [
            str(repo_root / ".venv" / "Scripts" / "python.exe"),
            str(script),
            "--guard-check",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=90,
    )
    return {
        "script": script_name,
        "status": "PASS" if completed.returncode == 0 else "FAILED",
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-700:],
        "stderr_tail": completed.stderr[-700:],
    }


def safety_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    evidence = discover_safety_evidence(repo_root, workspace)
    audit = latest_audit_status(workspace)

    triggered = [
        item for item in evidence
        if item["kill_switch_state"] == "TRIGGERED"
    ]
    clear = [
        item for item in evidence
        if item["kill_switch_state"] == "CLEAR"
    ]

    kill_switch_status = "TRIGGERED" if triggered else (
        "CLEAR" if clear else "NO_TRIGGER_EVIDENCE"
    )
    permanent_locks_ok = all(PERMANENT_SAFETY_LOCK.values())
    overall = (
        "LOCKED_SAFE"
        if permanent_locks_ok and kill_switch_status != "TRIGGERED"
        else "ATTENTION_REQUIRED"
    )

    display = (
        f"Safety: {overall} | Kill switch: {kill_switch_status} | "
        f"Evidence: {len(evidence)} | Audit: {audit['status']}"
    )
    return {
        "version": VERSION,
        "generated_at_utc": utc_now_text(),
        "overall_status": overall,
        "kill_switch_status": kill_switch_status,
        "triggered_evidence_count": len(triggered),
        "clear_evidence_count": len(clear),
        "evidence_count": len(evidence),
        "evidence": evidence,
        "latest_evidence_path": evidence[0]["path"] if evidence else "",
        "audit": audit,
        "permanent_safety_lock": PERMANENT_SAFETY_LOCK,
        "display_text": display,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def execute_safety_audit(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    output_path = workspace / STATUS_FILE
    write_json(
        output_path,
        {
            "version": VERSION,
            "status": "RUNNING",
            "message": "Running read-only HQE safety guard audit.",
            "started_at_utc": utc_now_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        },
    )

    results = [
        run_guard_check(repo_root, script_name)
        for script_name in GUARD_SCRIPTS
    ]
    failed = [
        result for result in results
        if result["status"] == "FAILED"
    ]
    missing = [
        result for result in results
        if result["status"] == "MISSING"
    ]

    passed = not failed and not missing
    payload = {
        "version": VERSION,
        "status": "PASS" if passed else "CHECK_REQUIRED",
        "message": (
            "All HQE safety guards passed."
            if passed
            else (
                f"Safety audit needs review: "
                f"{len(failed)} failed, {len(missing)} missing."
            )
        ),
        "completed_at_utc": utc_now_text(),
        "results": results,
        "failed_count": len(failed),
        "missing_count": len(missing),
        "permanent_safety_lock": PERMANENT_SAFETY_LOCK,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }
    write_json(output_path, payload)
    return payload


def launch_safety_audit_worker(
    repo_root: Path,
    workspace: Path,
) -> subprocess.Popen[Any]:
    pythonw = repo_root / ".venv" / "Scripts" / "pythonw.exe"
    executable = (
        pythonw
        if pythonw.exists()
        else repo_root / ".venv" / "Scripts" / "python.exe"
    )
    command = [
        str(executable),
        str(Path(__file__).resolve()),
        "--repo-root",
        str(repo_root),
        "--workspace",
        str(workspace),
        "--run-audit",
    ]
    return subprocess.Popen(
        command,
        cwd=repo_root,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "SAFETY_AND_KILL_SWITCH_EVIDENCE_CENTER",
        "read_only_evidence_scan": True,
        "permanent_safety_lock": PERMANENT_SAFETY_LOCK,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE app safety and kill-switch evidence center"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--run-audit", action="store_true")
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
            safety_snapshot(repo_root, workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.run_audit:
        payload = execute_safety_audit(repo_root, workspace)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1

    parser.error("Use --guard-check, --snapshot or --run-audit.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
