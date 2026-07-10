from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_APP_MARKET_DATA_CENTER_V1"
STATUS_FILE = "HQE_APP_MARKET_DATA_CENTER_STATUS.json"
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

SOURCE_REGISTRY = {
    "fyers": {"display_name": "Fyers", "status": "AVAILABLE", "mode": "DATA_ONLY"},
    "zerodha": {"display_name": "Zerodha", "status": "PLACEHOLDER", "mode": "DISABLED"},
    "angel_one": {"display_name": "Angel One", "status": "PLACEHOLDER", "mode": "DISABLED"},
    "upstox": {"display_name": "Upstox", "status": "PLACEHOLDER", "mode": "DISABLED"},
    "groww": {"display_name": "Groww", "status": "PLACEHOLDER", "mode": "DISABLED"},
    "dhan": {"display_name": "Dhan", "status": "PLACEHOLDER", "mode": "DISABLED"},
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def market_window_state(at_utc: datetime | None = None) -> str:
    current = (at_utc or now_utc()).astimezone(IST)
    if current.weekday() >= 5:
        return "CLOSED_WEEKEND"
    current_time = current.time().replace(tzinfo=None)
    return "OPEN" if time(9, 15) <= current_time <= time(15, 30) else "CLOSED"


def parse_timestamp(value: str) -> datetime | None:
    raw = value.strip()
    if not raw:
        return None
    for candidate in (raw, raw.replace("Z", "+00:00"), raw.replace(" ", "T")):
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=IST)
        return parsed.astimezone(timezone.utc)
    return None


def candidate_csv_files(repo_root: Path, workspace: Path) -> list[Path]:
    found: dict[Path, Path] = {}
    for root in (workspace, repo_root / "data" / "processed", repo_root / "data" / "live"):
        if not root.exists():
            continue
        for path in root.rglob("*.csv"):
            if path.is_file():
                found[path.resolve()] = path
    return sorted(found.values(), key=lambda path: path.stat().st_mtime, reverse=True)


def inspect_csv(path: Path) -> dict[str, Any]:
    rows = 0
    latest: datetime | None = None
    timestamp_column = ""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            names = [str(name or "").strip() for name in (reader.fieldnames or [])]
            lowered = {name.lower(): name for name in names}
            for option in ("datetime", "timestamp", "date_time", "time", "date"):
                if option in lowered:
                    timestamp_column = lowered[option]
                    break
            for row in reader:
                rows += 1
                if timestamp_column:
                    parsed = parse_timestamp(str(row.get(timestamp_column, "")))
                    if parsed and (latest is None or parsed > latest):
                        latest = parsed
    except Exception as exc:
        return {
            "path": str(path), "status": "UNREADABLE", "rows": 0,
            "timestamp_column": "", "latest_timestamp_utc": "",
            "error": type(exc).__name__,
        }
    return {
        "path": str(path), "status": "READABLE", "rows": rows,
        "timestamp_column": timestamp_column,
        "latest_timestamp_utc": latest.replace(microsecond=0).isoformat() if latest else "",
        "error": "",
    }


def latest_market_data(repo_root: Path, workspace: Path) -> dict[str, Any]:
    candidates = candidate_csv_files(repo_root, workspace)
    if not candidates:
        return {
            "status": "WAITING", "message": "No market-data CSV found.",
            "path": "", "rows": 0, "latest_timestamp_utc": "", "age_minutes": None,
        }

    best: dict[str, Any] | None = None
    for candidate in candidates[:20]:
        inspected = inspect_csv(candidate)
        if inspected["status"] == "READABLE" and inspected["rows"] > 0:
            best = inspected
            if inspected["latest_timestamp_utc"]:
                break

    if best is None:
        return {
            "status": "CHECK",
            "message": "Market-data CSV files exist but could not be validated.",
            "path": str(candidates[0]), "rows": 0,
            "latest_timestamp_utc": "", "age_minutes": None,
        }

    latest = parse_timestamp(str(best["latest_timestamp_utc"])) if best["latest_timestamp_utc"] else None
    age = max(0.0, round((now_utc() - latest).total_seconds() / 60.0, 1)) if latest else None
    window = market_window_state()

    if latest is None:
        status = "DATA_FOUND"
        message = f"{best['rows']} rows found; timestamp unavailable."
    elif window != "OPEN":
        status = "MARKET_CLOSED_EVIDENCE"
        message = f"Latest stored candle is {age} minutes old; market is closed."
    elif age is not None and age <= 20:
        status = "LIVE"
        message = f"Latest candle is {age} minutes old."
    elif age is not None and age <= 180:
        status = "STALE"
        message = f"Latest candle is {age} minutes old."
    else:
        status = "CHECK"
        message = f"Latest candle is {age} minutes old."

    return {**best, "status": status, "message": message, "age_minutes": age, "market_window": window}


def latest_evidence(workspace: Path) -> dict[str, str]:
    patterns = (
        "*LIVE_DATA*CYCLE*STATUS*.json",
        "*FYERS*FETCHER*STATUS*.json",
        "*MARKET*DATA*STATUS*.json",
        "*PAPER*WATCH*STATUS*.json",
    )
    candidates: list[Path] = []
    if workspace.exists():
        for pattern in patterns:
            candidates.extend(path for path in workspace.rglob(pattern) if path.is_file())
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return {"status": "WAITING", "path": "", "message": "No feed evidence found."}
    latest = candidates[0]
    payload = read_json(latest)
    raw = str(
        payload.get("cycle_status")
        or payload.get("status")
        or payload.get("decision")
        or payload.get("guard_check_status")
        or "EVIDENCE_FOUND"
    ).upper()
    return {"status": raw, "path": str(latest), "message": raw}


def operation_status(workspace: Path) -> dict[str, str]:
    payload = read_json(workspace / STATUS_FILE)
    return {
        "status": str(payload.get("status", "IDLE")),
        "message": str(payload.get("message", "")),
        "completed_at_utc": str(payload.get("completed_at_utc", "")),
    }


def market_data_snapshot(repo_root: Path, workspace: Path) -> dict[str, Any]:
    data = latest_market_data(repo_root, workspace)
    evidence = latest_evidence(workspace)
    operation = operation_status(workspace)
    display = (
        f"Source: Fyers | Feed: {data['status']} | "
        f"Rows: {data.get('rows', 0)} | Refresh: {operation['status']}"
    )
    return {
        "version": VERSION,
        "generated_at_utc": iso_now(),
        "active_source": "fyers",
        "active_source_display_name": "Fyers",
        "sources": SOURCE_REGISTRY,
        "market_window": market_window_state(),
        "latest_data": data,
        "latest_evidence": evidence,
        "operation": operation,
        "display_text": display,
        "secret_values_redacted": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def safe_refresh_command(repo_root: Path, workspace: Path, symbol: str) -> list[str]:
    return [
        str(repo_root / ".venv" / "Scripts" / "python.exe"),
        str(repo_root / "scripts" / "hqe_fyers_historical_5m_data_only_fetcher.py"),
        "--workspace", str(workspace),
        "--symbol", symbol,
        "--execute-live-data-only",
        "--write",
    ]


def execute_safe_refresh(repo_root: Path, workspace: Path, symbol: str) -> dict[str, Any]:
    output_path = workspace / STATUS_FILE
    command = safe_refresh_command(repo_root, workspace, symbol)
    if not Path(command[1]).exists():
        payload = {
            "version": VERSION, "status": "FAILED",
            "message": "Safe data-only fetcher is missing.",
            "completed_at_utc": iso_now(),
            "real_orders_enabled": False, "broker_execution_enabled": False,
        }
        write_json(output_path, payload)
        return payload

    write_json(output_path, {
        "version": VERSION, "status": "RUNNING",
        "message": "Refreshing Fyers market data only.",
        "started_at_utc": iso_now(),
        "real_orders_enabled": False, "broker_execution_enabled": False,
    })

    completed = subprocess.run(
        command, cwd=repo_root, env=os.environ.copy(),
        capture_output=True, text=True, timeout=240,
    )
    passed = completed.returncode == 0
    payload = {
        "version": VERSION,
        "status": "PASS" if passed else "FAILED",
        "message": (
            "Fyers market data refreshed safely."
            if passed else
            "Market-data refresh failed. Check Fyers login and connection."
        ),
        "completed_at_utc": iso_now(),
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-1200:],
        "stderr_tail": completed.stderr[-1200:],
        "secret_values_redacted": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }
    write_json(output_path, payload)
    return payload


def launch_market_data_worker(
    repo_root: Path,
    workspace: Path,
    operation: str,
    symbol: str = "NSE:NIFTY50-INDEX",
) -> subprocess.Popen[Any]:
    pythonw = repo_root / ".venv" / "Scripts" / "pythonw.exe"
    executable = pythonw if pythonw.exists() else repo_root / ".venv" / "Scripts" / "python.exe"
    command = [
        str(executable), str(Path(__file__).resolve()),
        "--repo-root", str(repo_root),
        "--workspace", str(workspace),
        "--execute-operation", operation,
        "--symbol", symbol,
    ]
    return subprocess.Popen(
        command, cwd=repo_root,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "active_source": "fyers",
        "source_count": len(SOURCE_REGISTRY),
        "network_mode": "DATA_ONLY",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE app market-data center")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--workspace", default="")
    parser.add_argument("--symbol", default="NSE:NIFTY50-INDEX")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    parser.add_argument("--execute-operation", choices=["refresh_fyers_data"])
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")

    repo_root = Path(args.repo_root)
    workspace = Path(args.workspace)
    if args.snapshot:
        print(json.dumps(market_data_snapshot(repo_root, workspace), indent=2, sort_keys=True))
        return 0
    if args.execute_operation == "refresh_fyers_data":
        payload = execute_safe_refresh(repo_root, workspace, args.symbol)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1
    parser.error("Use --guard-check, --snapshot or --execute-operation.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
