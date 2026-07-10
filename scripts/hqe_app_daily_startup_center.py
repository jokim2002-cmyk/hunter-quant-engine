from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_APP_DAILY_STARTUP_CENTER_V1"
STATUS_FILE = "HQE_APP_DAILY_STARTUP_STATUS.json"
IST = timezone(timedelta(hours=5, minutes=30))

SAFETY_LOCK = {
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


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def next_market_day(from_date: date | None = None) -> date:
    candidate = (from_date or datetime.now(IST).date()) + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


def discover_day_numbers(workspace: Path) -> list[int]:
    pattern = re.compile(r"DAY[_ -]?(\d{1,4})", re.IGNORECASE)
    numbers: set[int] = set()
    if not workspace.exists():
        return []
    for path in workspace.rglob("*"):
        match = pattern.search(path.name)
        if match:
            numbers.add(int(match.group(1)))
    return sorted(numbers)


def latest_day_number(workspace: Path) -> int:
    numbers = discover_day_numbers(workspace)
    return numbers[-1] if numbers else 0


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def _run_guard(repo_root: Path, script_name: str) -> dict[str, Any]:
    script = repo_root / "scripts" / script_name
    if not script.exists():
        return {"status": "MISSING", "message": f"Missing: {script.name}"}
    completed = subprocess.run(
        [
            str(repo_root / ".venv" / "Scripts" / "python.exe"),
            str(script),
            "--guard-check",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "status": "PASS" if completed.returncode == 0 else "FAILED",
        "message": script.name,
        "return_code": completed.returncode,
    }


def _auth_status(repo_root: Path) -> dict[str, Any]:
    import sys
    scripts = str(repo_root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    try:
        from hqe_app_fyers_auth import auth_status_snapshot
        payload = auth_status_snapshot()
        return {
            "status": str(payload.get("status", "UNKNOWN")),
            "message": str(payload.get("message", "")),
        }
    except Exception as exc:
        return {
            "status": "CHECK",
            "message": f"Auth status unavailable: {type(exc).__name__}",
        }


def _market_data_status(repo_root: Path, workspace: Path) -> dict[str, Any]:
    import sys
    scripts = str(repo_root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    try:
        from hqe_app_market_data_center import market_data_snapshot
        payload = market_data_snapshot(repo_root, workspace)
        latest = payload.get("latest_data", {})
        return {
            "status": str(latest.get("status", "UNKNOWN")),
            "rows": int(latest.get("rows", 0) or 0),
            "message": str(latest.get("message", "")),
        }
    except Exception as exc:
        return {
            "status": "CHECK",
            "rows": 0,
            "message": f"Market-data status unavailable: {type(exc).__name__}",
        }


def daily_readiness_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    latest_day = latest_day_number(workspace)
    auth = _auth_status(repo_root)
    market_data = _market_data_status(repo_root, workspace)
    guards = {
        "startup": _run_guard(repo_root, "hqe_next_market_day_startup_pack.py"),
        "rollover": _run_guard(repo_root, "hqe_validation_day_auto_rollover_plan.py"),
        "daily_close": _run_guard(repo_root, "hqe_daily_close_auto_report_pack.py"),
    }
    checklist = {
        "workspace_ready": workspace.exists(),
        "fyers_login_ready": auth["status"] == "READY",
        "market_data_available": market_data["rows"] > 0,
        "startup_guard_pass": guards["startup"]["status"] == "PASS",
        "rollover_guard_pass": guards["rollover"]["status"] == "PASS",
        "daily_close_guard_pass": guards["daily_close"]["status"] == "PASS",
        "latest_day_known": latest_day > 0,
    }
    passed = sum(bool(value) for value in checklist.values())
    total = len(checklist)
    overall = "READY" if passed == total else "CHECK_REQUIRED"
    next_day = latest_day + 1 if latest_day else 1
    next_date = next_market_day().isoformat()
    return {
        "version": VERSION,
        "generated_at_utc": utc_now_text(),
        "overall_status": overall,
        "checklist": checklist,
        "checks_passed": passed,
        "checks_total": total,
        "latest_day_number": latest_day,
        "next_day_number": next_day,
        "next_market_day": next_date,
        "auth": auth,
        "market_data": market_data,
        "guards": guards,
        "display_text": (
            f"Daily readiness: {overall} | Checks: {passed}/{total} | "
            f"Latest day: {latest_day or 'none'} | "
            f"Next: DAY_{next_day:03d} on {next_date}"
        ),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def prepare_next_day_command(
    repo_root: Path,
    workspace: Path,
    *,
    trading_date: str,
    day_number: int,
) -> list[str]:
    return [
        str(repo_root / ".venv" / "Scripts" / "python.exe"),
        str(repo_root / "scripts" / "hqe_next_market_day_startup_pack.py"),
        "--workspace",
        str(workspace),
        "--trading-date",
        trading_date,
        "--day-number",
        str(day_number),
        "--user-id",
        "JOKIM",
        "--symbol",
        "NSE:NIFTY50-INDEX",
        "--write",
    ]


def execute_prepare_next_day(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    snapshot = daily_readiness_snapshot(repo_root, workspace)
    status_path = workspace / STATUS_FILE
    if snapshot["guards"]["startup"]["status"] != "PASS":
        payload = {
            "version": VERSION,
            "status": "BLOCKED",
            "message": "Startup guard did not pass.",
            "completed_at_utc": utc_now_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        }
        _write_json(status_path, payload)
        return payload

    command = prepare_next_day_command(
        repo_root,
        workspace,
        trading_date=snapshot["next_market_day"],
        day_number=int(snapshot["next_day_number"]),
    )
    _write_json(
        status_path,
        {
            "version": VERSION,
            "status": "RUNNING",
            "message": "Preparing next market day safely.",
            "started_at_utc": utc_now_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        },
    )
    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=180,
    )
    passed = completed.returncode == 0
    payload = {
        "version": VERSION,
        "status": "PASS" if passed else "FAILED",
        "message": (
            f"DAY_{int(snapshot['next_day_number']):03d} prepared for "
            f"{snapshot['next_market_day']}."
            if passed
            else "Next market-day preparation failed safely."
        ),
        "completed_at_utc": utc_now_text(),
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-1000:],
        "stderr_tail": completed.stderr[-1000:],
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }
    _write_json(status_path, payload)
    return payload


def operation_status(workspace: Path) -> dict[str, str]:
    payload = _read_json(workspace / STATUS_FILE)
    return {
        "status": str(payload.get("status", "IDLE")),
        "message": str(payload.get("message", "")),
    }


def launch_daily_startup_worker(
    repo_root: Path,
    workspace: Path,
) -> subprocess.Popen[Any]:
    pythonw = repo_root / ".venv" / "Scripts" / "pythonw.exe"
    executable = pythonw if pythonw.exists() else repo_root / ".venv" / "Scripts" / "python.exe"
    command = [
        str(executable),
        str(Path(__file__).resolve()),
        "--repo-root",
        str(repo_root),
        "--workspace",
        str(workspace),
        "--prepare-next-day",
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
        "workflow": "DAILY_STARTUP_AND_OPERATOR_CHECKLIST",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE app daily startup center")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--prepare-next-day", action="store_true")
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
        payload = daily_readiness_snapshot(repo_root, workspace)
        payload["operation"] = operation_status(workspace)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.prepare_next_day:
        payload = execute_prepare_next_day(repo_root, workspace)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1
    parser.error("Use --guard-check, --snapshot or --prepare-next-day.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
