from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_APP_DAILY_CLOSE_CENTER_V1"
STATUS_FILE = "HQE_APP_DAILY_CLOSE_CENTER_STATUS.json"
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


def now_utc_text() -> str:
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


def _date_from_text(value: str) -> str:
    patterns = (
        r"(20\d{2})[-_](\d{2})[-_](\d{2})",
        r"(20\d{2})(\d{2})(\d{2})",
    )
    for pattern in patterns:
        match = re.search(pattern, value)
        if not match:
            continue
        candidate = "-".join(match.groups())
        try:
            return datetime.strptime(candidate, "%Y-%m-%d").date().isoformat()
        except ValueError:
            continue
    return ""


def discover_latest_trading_date(workspace: Path) -> str:
    candidates: list[tuple[float, str]] = []
    if workspace.exists():
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue
            date_text = _date_from_text(path.name)
            if not date_text and path.suffix.lower() == ".json":
                payload = read_json(path)
                for key in (
                    "trading_date",
                    "session_date",
                    "market_date",
                    "date",
                ):
                    raw = str(payload.get(key, "")).strip()
                    date_text = _date_from_text(raw)
                    if date_text:
                        break
            if date_text:
                candidates.append((path.stat().st_mtime, date_text))
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]
    return datetime.now(IST).date().isoformat()


def _latest_matching(workspace: Path, patterns: tuple[str, ...]) -> str:
    candidates: list[Path] = []
    if workspace.exists():
        for pattern in patterns:
            candidates.extend(path for path in workspace.rglob(pattern) if path.is_file())
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return str(candidates[0]) if candidates else ""


def latest_close_artifacts(workspace: Path) -> dict[str, str]:
    report = _latest_matching(
        workspace,
        (
            "*DAILY*REPORT*",
            "*MARKET_CLOSE_PACK*",
            "*REPORT_PACK*",
        ),
    )
    evidence = _latest_matching(
        workspace,
        (
            "*MARKET_CLOSE_EVIDENCE*.json",
            "*DAILY_CLOSE*EVIDENCE*.json",
            "*CLOSE*EVIDENCE*.json",
        ),
    )
    return {
        "latest_report": report,
        "latest_evidence": evidence,
    }


def run_close_guard(repo_root: Path) -> dict[str, Any]:
    script = repo_root / "scripts" / "hqe_daily_close_auto_report_pack.py"
    if not script.exists():
        return {
            "status": "MISSING",
            "message": "Daily-close report script is missing.",
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
        timeout=60,
    )
    return {
        "status": "PASS" if completed.returncode == 0 else "FAILED",
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-800:],
        "stderr_tail": completed.stderr[-800:],
    }


def operation_status(workspace: Path) -> dict[str, str]:
    payload = read_json(workspace / STATUS_FILE)
    return {
        "status": str(payload.get("status", "IDLE")),
        "message": str(payload.get("message", "")),
        "completed_at_utc": str(payload.get("completed_at_utc", "")),
    }


def daily_close_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    day_number = latest_day_number(workspace)
    trading_date = discover_latest_trading_date(workspace)
    artifacts = latest_close_artifacts(workspace)
    guard = run_close_guard(repo_root)
    operation = operation_status(workspace)

    ready = bool(
        workspace.exists()
        and day_number > 0
        and trading_date
        and guard["status"] == "PASS"
    )
    overall = "READY_TO_CLOSE" if ready else "CHECK_REQUIRED"
    display = (
        f"Daily close: {overall} | DAY_{day_number:03d} | "
        f"Date: {trading_date} | Operation: {operation['status']}"
        if day_number
        else (
            f"Daily close: {overall} | Day: not detected | "
            f"Date: {trading_date} | Operation: {operation['status']}"
        )
    )
    return {
        "version": VERSION,
        "generated_at_utc": now_utc_text(),
        "overall_status": overall,
        "workspace_ready": workspace.exists(),
        "day_number": day_number,
        "trading_date": trading_date,
        "guard": guard,
        "operation": operation,
        **artifacts,
        "display_text": display,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def daily_close_command(
    repo_root: Path,
    workspace: Path,
    *,
    trading_date: str,
    day_number: int,
) -> list[str]:
    return [
        str(repo_root / ".venv" / "Scripts" / "python.exe"),
        str(repo_root / "scripts" / "hqe_daily_close_auto_report_pack.py"),
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


def execute_daily_close(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    snapshot = daily_close_snapshot(repo_root, workspace)
    output_path = workspace / STATUS_FILE

    if snapshot["overall_status"] != "READY_TO_CLOSE":
        payload = {
            "version": VERSION,
            "status": "BLOCKED",
            "message": "Daily close is not ready. Check workspace, day and guard status.",
            "completed_at_utc": now_utc_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        }
        write_json(output_path, payload)
        return payload

    command = daily_close_command(
        repo_root,
        workspace,
        trading_date=str(snapshot["trading_date"]),
        day_number=int(snapshot["day_number"]),
    )
    write_json(
        output_path,
        {
            "version": VERSION,
            "status": "RUNNING",
            "message": "Generating daily close report safely.",
            "started_at_utc": now_utc_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        },
    )
    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=240,
    )
    passed = completed.returncode == 0
    refreshed = latest_close_artifacts(workspace)
    payload = {
        "version": VERSION,
        "status": "PASS" if passed else "FAILED",
        "message": (
            f"DAY_{int(snapshot['day_number']):03d} daily close report generated."
            if passed
            else "Daily close report generation failed safely."
        ),
        "completed_at_utc": now_utc_text(),
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-1200:],
        "stderr_tail": completed.stderr[-1200:],
        **refreshed,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }
    write_json(output_path, payload)
    return payload


def launch_daily_close_worker(
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
        "--execute-close",
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
        "workflow": "END_OF_DAY_CLOSE_AND_REPORT",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE app daily close center")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--execute-close", action="store_true")
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
            daily_close_snapshot(repo_root, workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.execute_close:
        payload = execute_daily_close(repo_root, workspace)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1

    parser.error("Use --guard-check, --snapshot or --execute-close.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
