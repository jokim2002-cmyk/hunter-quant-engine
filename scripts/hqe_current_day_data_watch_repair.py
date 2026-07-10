from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from hqe_fyers_candle_csv_writer import write_from_fetch_status

VERSION = "HQE_CURRENT_DAY_DATA_WATCH_REPAIR_V1"
INDIA_TZ = ZoneInfo("Asia/Kolkata")
STATUS_FILENAME = "HQE_CURRENT_DAY_DATA_WATCH_REPAIR.json"


def now_ist() -> datetime:
    return datetime.now(timezone.utc).astimezone(INDIA_TZ)


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def parse_datetime(value: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=INDIA_TZ)
    return parsed.astimezone(INDIA_TZ)


def latest_csv_candle(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "row_count": 0,
            "latest_candle_ist": None,
            "latest_candle_date": None,
            "latest_candle_age_seconds": None,
        }

    latest: Optional[datetime] = None
    rows = 0

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows += 1
            parsed = parse_datetime(str(row.get("datetime") or ""))
            if parsed is not None and (latest is None or parsed > latest):
                latest = parsed

    current = now_ist()
    age = max(0, int((current - latest).total_seconds())) if latest else None

    return {
        "row_count": rows,
        "latest_candle_ist": latest.isoformat() if latest else None,
        "latest_candle_date": latest.date().isoformat() if latest else None,
        "latest_candle_age_seconds": age,
    }


def python_watch_processes() -> List[Dict[str, Any]]:
    if os.name != "nt":
        return []

    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            "Where-Object {"
            "$_.CommandLine -like '*hqe_market_day_persistent_paper_watch_loop.py*' "
            "-and $_.Name -match '^python(w)?\\.exe$'"
            "} | "
            "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | "
            "ConvertTo-Json -Compress"
        ),
    ]

    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []

    raw = completed.stdout.strip()
    if not raw:
        return []

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        payload = [payload]

    return [
        item for item in payload
        if isinstance(item, dict)
        and item.get("ProcessId")
        and str(item.get("Name", "")).lower() in {"python.exe", "pythonw.exe"}
    ]


def canonical_process(processes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    items = processes if processes is not None else python_watch_processes()
    if not items:
        return {
            "running": False,
            "canonical_pid": None,
            "process_count": 0,
            "reason": "ACTUAL_PYTHON_WATCH_PROCESS_NOT_FOUND",
        }

    ids = {int(item["ProcessId"]) for item in items}
    roots = [
        item for item in items
        if int(item.get("ParentProcessId") or 0) not in ids
    ]
    preferred = roots or items
    selected = min(preferred, key=lambda item: int(item["ProcessId"]))

    return {
        "running": True,
        "canonical_pid": int(selected["ProcessId"]),
        "process_count": len(items),
        "reason": "ROOT_PYTHON_WATCH_PROCESS" if selected in roots else "LOWEST_PID_FALLBACK",
    }


def market_open(current: datetime) -> bool:
    if current.weekday() >= 5:
        return False
    opening = current.replace(hour=9, minute=15, second=0, microsecond=0)
    closing = current.replace(hour=15, minute=30, second=0, microsecond=0)
    return opening <= current <= closing


def execute_current_day_fetch(repo: Path, workspace: Path) -> Dict[str, Any]:
    current = now_ist()
    trading_date = current.date().isoformat()
    python_exe = repo / ".venv" / "Scripts" / "python.exe"
    fetcher = repo / "scripts" / "hqe_fyers_historical_5m_data_only_fetcher.py"

    command = [
        str(python_exe),
        str(fetcher),
        "--workspace",
        str(workspace),
        "--trading-date",
        trading_date,
        "--day-number",
        "1",
        "--user-id",
        "hqe-user",
        "--symbol",
        "NSE:NIFTY50-INDEX",
        "--write",
        "--execute-live-data-only",
    ]

    completed = subprocess.run(
        command,
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
    )

    status_path = workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
    csv_path = workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"
    writer_result = write_from_fetch_status(status_path, csv_path)
    status = read_json(status_path)
    history = status.get("history_result") or {}
    response = history.get("response_redacted") or {}

    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-1500:],
        "stderr_tail": completed.stderr[-1500:],
        "trading_date_requested": trading_date,
        "api_code": response.get("code"),
        "api_status": response.get("s"),
        "api_message": response.get("message"),
        "api_rows": int(history.get("rows") or 0),
        "writer_result": writer_result,
    }


def start_watch(repo: Path, workspace: Path) -> Dict[str, Any]:
    existing = canonical_process()
    if existing["running"]:
        return {
            "started": False,
            "reason": "WATCH_ALREADY_RUNNING",
            **existing,
        }

    current = now_ist()
    python_exe = repo / ".venv" / "Scripts" / "python.exe"
    watch_script = repo / "scripts" / "hqe_market_day_persistent_paper_watch_loop.py"
    stdout_path = workspace / "HQE_PAPER_WATCH_STDOUT.log"
    stderr_path = workspace / "HQE_PAPER_WATCH_STDERR.log"

    command = [
        str(python_exe),
        str(watch_script),
        "--workspace",
        str(workspace),
        "--trading-date",
        current.date().isoformat(),
        "--day-number",
        "1",
        "--user-id",
        "hqe-user",
        "--symbol",
        "NSE:NIFTY50-INDEX",
        "--interval-seconds",
        "300",
        "--max-cycles",
        "0",
        "--run-data-fetch",
    ]

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    with stdout_path.open("a", encoding="utf-8") as stdout_handle, stderr_path.open(
        "a", encoding="utf-8"
    ) as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=repo,
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )

    time.sleep(3)
    detected = canonical_process()

    return {
        "started": True,
        "launcher_pid": process.pid,
        "command": command,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        **detected,
    }


def derive_unified_health(workspace: Path) -> Dict[str, Any]:
    current = now_ist()
    fetch_status = read_json(
        workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
    )
    history = fetch_status.get("history_result") or {}
    response = history.get("response_redacted") or {}
    candle = latest_csv_candle(
        workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"
    )
    process = canonical_process()

    auth_ok = response.get("code") == 200 and response.get("s") == "ok"
    current_day = candle["latest_candle_date"] == current.date().isoformat()
    fresh = (
        candle["latest_candle_age_seconds"] is not None
        and candle["latest_candle_age_seconds"] <= 600
    )

    if not auth_ok:
        overall = "AUTH_FAILED"
        recommendation = "REFRESH_FYERS_ACCESS_TOKEN"
    elif not current_day:
        overall = "CURRENT_DAY_DATA_MISSING"
        recommendation = "RUN_CURRENT_DAY_FETCH"
    elif market_open(current) and not fresh:
        overall = "CURRENT_DAY_DATA_STALE"
        recommendation = "CHECK_FETCH_CYCLE"
    elif not process["running"]:
        overall = "WATCH_PROCESS_STOPPED"
        recommendation = "START_PAPER_WATCH"
    else:
        overall = "HEALTHY"
        recommendation = "CONTINUE_PAPER_WATCH"

    return {
        "version": VERSION,
        "generated_at_ist": current.isoformat(),
        "overall_health": overall,
        "operator_recommendation": recommendation,
        "auth_ok": auth_ok,
        "api_code": response.get("code"),
        "api_status": response.get("s"),
        "market_open": market_open(current),
        "current_trading_date": current.date().isoformat(),
        "current_day_candle_present": current_day,
        "data_fresh": fresh,
        **candle,
        **process,
        "paper_only": True,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def run_repair(repo: Path, workspace: Path) -> Dict[str, Any]:
    fetch = execute_current_day_fetch(repo, workspace)
    watch = start_watch(repo, workspace)
    health = derive_unified_health(workspace)

    payload = {
        "version": VERSION,
        "repo": str(repo),
        "workspace": str(workspace),
        "fetch": fetch,
        "watch": watch,
        "health": health,
        "paper_only": True,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }
    atomic_write_json(workspace / STATUS_FILENAME, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair current-day data and paper watch")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--repo-root")
    parser.add_argument("--status-only", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[1]
    workspace = Path(args.workspace)

    if args.status_only:
        payload = derive_unified_health(workspace)
    else:
        payload = run_repair(repo, workspace)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
