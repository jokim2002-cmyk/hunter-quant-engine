from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from zoneinfo import ZoneInfo

VERSION = "HQE_WATCH_HEALTH_MONITOR_V1"
INDIA_TZ = ZoneInfo("Asia/Kolkata")
STATUS_FILENAME = "HQE_WATCH_HEALTH_STATUS.json"

DATA_FILES = (
    "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv",
    "DAY_001_PERSISTENT_PAPER_WATCH_LOOP.csv",
    "HQE_PERSISTENT_MARKET_DAY_PAPER_WATCH_STATUS.json",
    "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: Optional[datetime]) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat() if value else "UNKNOWN"


def format_ist(value: Optional[datetime]) -> str:
    if value is None:
        return "UNKNOWN"
    return value.astimezone(INDIA_TZ).strftime("%d-%m-%Y %I:%M:%S %p IST")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def market_session(now_ist: Optional[datetime] = None) -> str:
    now = now_ist or utc_now().astimezone(INDIA_TZ)
    if now.weekday() >= 5:
        return "CLOSED"
    open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return "OPEN" if open_time <= now <= close_time else "CLOSED"


def watch_process() -> Dict[str, Any]:
    if os.name != "nt":
        return {"running": False, "pid": None, "reason": "WINDOWS_PROCESS_CHECK_UNAVAILABLE"}

    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            "Where-Object {$_.CommandLine -like "
            "'*hqe_market_day_persistent_paper_watch_loop.py*'} | "
            "Select-Object -First 1 ProcessId,CommandLine | ConvertTo-Json -Compress"
        ),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"running": False, "pid": None, "reason": type(exc).__name__}

    raw = completed.stdout.strip()
    if not raw:
        return {"running": False, "pid": None, "reason": "PROCESS_NOT_FOUND"}

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"running": False, "pid": None, "reason": "PROCESS_QUERY_INVALID_JSON"}

    pid = payload.get("ProcessId")
    return {
        "running": bool(pid),
        "pid": pid,
        "command_line": payload.get("CommandLine", ""),
        "reason": "PROCESS_FOUND" if pid else "PROCESS_NOT_FOUND",
    }


def existing_files(workspace: Path) -> Iterable[Path]:
    for name in DATA_FILES:
        path = workspace / name
        if path.exists() and path.is_file():
            yield path


def newest_data_update(workspace: Path) -> Dict[str, Any]:
    candidates = []
    for path in existing_files(workspace):
        stat = path.stat()
        candidates.append(
            {
                "path": str(path),
                "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                "size_bytes": stat.st_size,
            }
        )

    if not candidates:
        return {
            "latest_path": "NOT_FOUND",
            "latest_update": None,
            "candidate_count": 0,
        }

    latest = max(candidates, key=lambda item: item["modified_utc"])
    return {
        "latest_path": latest["path"],
        "latest_update": latest["modified_utc"],
        "latest_size_bytes": latest["size_bytes"],
        "candidate_count": len(candidates),
    }


def fetch_failure_reason(workspace: Path) -> str:
    payload = read_json(
        workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
    )

    for key in (
        "error",
        "error_message",
        "failure_reason",
        "reason",
        "message",
    ):
        value = payload.get(key)
        if value:
            return str(value)

    status = str(
        payload.get("status")
        or payload.get("decision")
        or payload.get("fetch_status")
        or "UNKNOWN"
    )

    if "COMPLETED" in status.upper() or "PASS" in status.upper():
        return "NONE_REPORTED"
    return status


def age_seconds(value: Optional[datetime], now: datetime) -> Optional[int]:
    if value is None:
        return None
    return max(0, int((now - value).total_seconds()))


def collect_health(
    workspace: Path,
    *,
    now: Optional[datetime] = None,
    process_override: Optional[Dict[str, Any]] = None,
    write: bool = True,
) -> Dict[str, Any]:
    current = now or utc_now()
    process = process_override or watch_process()
    data = newest_data_update(workspace)
    latest_update = data.get("latest_update")
    age = age_seconds(latest_update, current)
    session = market_session(current.astimezone(INDIA_TZ))

    previous = read_json(workspace / STATUS_FILENAME)
    previous_stale = int(previous.get("consecutive_stale_cycles", 0) or 0)

    stale_threshold_seconds = 600
    is_stale = age is None or age > stale_threshold_seconds

    if not process.get("running"):
        overall = "STOPPED"
        reason = process.get("reason", "PROCESS_NOT_FOUND")
        stale_cycles = previous_stale
    elif session == "CLOSED":
        overall = "MARKET_CLOSED_IDLE"
        reason = "MARKET_SESSION_CLOSED"
        stale_cycles = 0
    elif is_stale:
        overall = "DEGRADED_DATA_STALE"
        reason = (
            "NO_DATA_FILES_FOUND"
            if age is None
            else f"LAST_DATA_UPDATE_{age}_SECONDS_AGO"
        )
        stale_cycles = previous_stale + 1
    else:
        overall = "HEALTHY"
        reason = "PROCESS_RUNNING_AND_DATA_FRESH"
        stale_cycles = 0

    payload = {
        "version": VERSION,
        "generated_at_utc": iso_utc(current),
        "heartbeat_ist": format_ist(current),
        "workspace": str(workspace),
        "overall_health": overall,
        "health_reason": reason,
        "market_session": session,
        "process_running": bool(process.get("running")),
        "watch_pid": process.get("pid"),
        "process_check_reason": process.get("reason"),
        "last_successful_data_update_utc": iso_utc(latest_update),
        "last_successful_data_update_ist": format_ist(latest_update),
        "data_age_seconds": age,
        "data_age_minutes": round(age / 60, 2) if age is not None else None,
        "freshness_threshold_seconds": stale_threshold_seconds,
        "consecutive_stale_cycles": stale_cycles,
        "latest_data_file": data.get("latest_path"),
        "data_candidate_count": data.get("candidate_count", 0),
        "fetch_failure_reason": fetch_failure_reason(workspace),
        "paper_only": True,
        "data_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }

    if write:
        atomic_write_json(workspace / STATUS_FILENAME, payload)

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE watch health monitor")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    if not workspace.exists():
        raise SystemExit(f"Workspace not found: {workspace}")

    payload = collect_health(workspace, write=not args.no_write)
    print(json.dumps(payload, indent=2, sort_keys=True))

    return 0 if payload["overall_health"] != "STOPPED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
