from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

VERSION = "HQE_FYERS_FETCH_EVIDENCE_TRUTH_V1"
INDIA_TZ = ZoneInfo("Asia/Kolkata")
OUTPUT_FILENAME = "HQE_FYERS_FETCH_EVIDENCE_TRUTH.json"
CANDLE_FILES = (
    "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv",
    "DAY_001_PERSISTENT_PAPER_WATCH_LOOP.csv",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


def parse_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None

    text = str(value).strip()
    normalized = text.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = None

    if parsed is None:
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        try:
            number = float(text)
        except ValueError:
            return None
        if number > 10_000_000_000:
            number /= 1000
        try:
            parsed = datetime.fromtimestamp(number, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=INDIA_TZ)
    return parsed.astimezone(timezone.utc)


def iso_utc(value: Optional[datetime]) -> str:
    if value is None:
        return "UNKNOWN"
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def format_ist(value: Optional[datetime]) -> str:
    if value is None:
        return "UNKNOWN"
    return value.astimezone(INDIA_TZ).strftime("%d-%m-%Y %I:%M:%S %p IST")


def market_is_open(now: datetime) -> bool:
    current = now.astimezone(INDIA_TZ)
    if current.weekday() >= 5:
        return False
    opening = current.replace(hour=9, minute=15, second=0, microsecond=0)
    closing = current.replace(hour=15, minute=30, second=0, microsecond=0)
    return opening <= current <= closing


def find_datetime_column(fieldnames: Iterable[str]) -> Optional[str]:
    normalized = {name.strip().lower(): name for name in fieldnames if name}
    for candidate in ("datetime", "timestamp", "time", "date", "candle_time", "bar_time"):
        if candidate in normalized:
            return normalized[candidate]
    return None


def latest_candle_from_csv(path: Path) -> Dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"path": str(path), "status": "FILE_NOT_FOUND", "latest_candle_utc": None, "row_count": 0}

    latest: Optional[datetime] = None
    row_count = 0

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            column = find_datetime_column(reader.fieldnames or [])
            if column is None:
                return {
                    "path": str(path),
                    "status": "DATETIME_COLUMN_NOT_FOUND",
                    "latest_candle_utc": None,
                    "row_count": 0,
                }

            for row in reader:
                row_count += 1
                parsed = parse_datetime(row.get(column))
                if parsed is not None and (latest is None or parsed > latest):
                    latest = parsed
    except (OSError, csv.Error) as exc:
        return {
            "path": str(path),
            "status": "CSV_READ_ERROR",
            "error": f"{type(exc).__name__}: {exc}",
            "latest_candle_utc": None,
            "row_count": row_count,
        }

    return {
        "path": str(path),
        "status": "PASS" if latest else "NO_VALID_CANDLE_TIMESTAMP",
        "latest_candle_utc": latest,
        "row_count": row_count,
    }


def newest_candle(workspace: Path) -> Dict[str, Any]:
    sources = [latest_candle_from_csv(workspace / name) for name in CANDLE_FILES]
    valid = [item for item in sources if item.get("latest_candle_utc") is not None]

    if not valid:
        return {
            "latest_candle_utc": None,
            "latest_candle_file": "NOT_FOUND",
            "latest_candle_rows": 0,
            "sources": sources,
        }

    latest = max(valid, key=lambda item: item["latest_candle_utc"])
    return {
        "latest_candle_utc": latest["latest_candle_utc"],
        "latest_candle_file": latest["path"],
        "latest_candle_rows": latest["row_count"],
        "sources": sources,
    }


def query_watch_processes() -> List[Dict[str, Any]]:
    if os.name != "nt":
        return []

    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            "Where-Object {$_.CommandLine -like "
            "'*hqe_market_day_persistent_paper_watch_loop.py*'} | "
            "Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine | "
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
    return [item for item in payload if isinstance(item, dict) and item.get("ProcessId")]


def canonical_watch_process(processes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    items = processes if processes is not None else query_watch_processes()
    if not items:
        return {
            "process_count": 0,
            "canonical_pid": None,
            "canonical_reason": "PROCESS_NOT_FOUND",
            "processes": [],
        }

    ids = {int(item["ProcessId"]) for item in items}
    roots = [item for item in items if int(item.get("ParentProcessId") or 0) not in ids]
    preferred = roots or items
    canonical = min(preferred, key=lambda item: int(item["ProcessId"]))

    return {
        "process_count": len(items),
        "canonical_pid": int(canonical["ProcessId"]),
        "canonical_parent_pid": int(canonical.get("ParentProcessId") or 0),
        "canonical_executable": canonical.get("ExecutablePath", ""),
        "canonical_reason": "ROOT_WATCH_PROCESS" if canonical in roots else "LOWEST_PID_FALLBACK",
        "processes": items,
    }


def fetch_status_payload(workspace: Path) -> Dict[str, Any]:
    path = workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
    payload = read_json(path)
    status = str(payload.get("status") or payload.get("decision") or payload.get("fetch_status") or "UNKNOWN")
    error = str(
        payload.get("error")
        or payload.get("error_message")
        or payload.get("failure_reason")
        or payload.get("reason")
        or "NONE_REPORTED"
    )
    completed = any(token in status.upper() for token in ("COMPLETED", "PASS", "SUCCESS"))
    return {
        "status_file": str(path),
        "raw_status": status,
        "reported_completed": completed,
        "reported_error": error,
    }


def build_truth(
    workspace: Path,
    *,
    now: Optional[datetime] = None,
    processes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    current = now or utc_now()
    candle = newest_candle(workspace)
    process = canonical_watch_process(processes)
    fetch = fetch_status_payload(workspace)

    latest_candle = candle.get("latest_candle_utc")
    candle_age = (
        max(0, int((current - latest_candle).total_seconds()))
        if latest_candle is not None
        else None
    )

    open_now = market_is_open(current)
    maximum_age_seconds = 600
    candle_fresh = candle_age is not None and candle_age <= maximum_age_seconds

    if not process["canonical_pid"]:
        truth = "WATCH_PROCESS_STOPPED"
        recommendation = "START_PAPER_WATCH"
    elif not open_now:
        truth = "MARKET_CLOSED_IDLE"
        recommendation = "NO_RESTART_REQUIRED"
    elif not fetch["reported_completed"]:
        truth = "FETCH_FAILED"
        recommendation = "CHECK_FYERS_FETCH_STATUS_AND_CREDENTIALS"
    elif latest_candle is None:
        truth = "FETCH_COMPLETED_BUT_NO_CANDLE_DATA"
        recommendation = "CHECK_FYERS_RESPONSE_AND_CSV_WRITER"
    elif not candle_fresh:
        truth = "FETCH_COMPLETED_BUT_CANDLE_STALE"
        recommendation = "RESTART_WATCH_ONLY_AFTER_FETCH_DIAGNOSTIC"
    else:
        truth = "LIVE_DATA_FRESH"
        recommendation = "CONTINUE_PAPER_WATCH"

    return {
        "version": VERSION,
        "generated_at_utc": iso_utc(current),
        "generated_at_ist": format_ist(current),
        "workspace": str(workspace),
        "market_open": open_now,
        "fetch_truth": truth,
        "operator_recommendation": recommendation,
        "fetch_reported_status": fetch["raw_status"],
        "fetch_reported_completed": fetch["reported_completed"],
        "fetch_reported_error": fetch["reported_error"],
        "latest_candle_utc": iso_utc(latest_candle),
        "latest_candle_ist": format_ist(latest_candle),
        "latest_candle_age_seconds": candle_age,
        "latest_candle_age_minutes": round(candle_age / 60, 2) if candle_age is not None else None,
        "maximum_candle_age_seconds": maximum_age_seconds,
        "latest_candle_file": candle.get("latest_candle_file"),
        "latest_candle_rows": candle.get("latest_candle_rows", 0),
        "canonical_watch_pid": process["canonical_pid"],
        "watch_process_count": process["process_count"],
        "canonical_pid_reason": process["canonical_reason"],
        "candle_sources": [
            {**item, "latest_candle_utc": iso_utc(item.get("latest_candle_utc"))}
            for item in candle["sources"]
        ],
        "paper_only": True,
        "data_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE Fyers fetch evidence truth")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    if not workspace.exists():
        raise SystemExit(f"Workspace not found: {workspace}")

    payload = build_truth(workspace)
    if not args.no_write:
        atomic_write_json(workspace / OUTPUT_FILENAME, payload)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
