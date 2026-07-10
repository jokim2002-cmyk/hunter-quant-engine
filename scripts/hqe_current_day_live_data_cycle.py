from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo

from hqe_fyers_candle_csv_writer import write_from_fetch_status

VERSION = "HQE_CURRENT_DAY_LIVE_DATA_CYCLE_V1"
INDIA_TZ = ZoneInfo("Asia/Kolkata")
STATUS_FILENAME = "HQE_CURRENT_DAY_LIVE_DATA_CYCLE.json"


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


def run_cycle(
    repo: Path,
    workspace: Path,
    *,
    trading_date: str | None = None,
    day_number: int = 1,
    user_id: str = "hqe-user",
    symbol: str = "NSE:NIFTY50-INDEX",
) -> Dict[str, Any]:
    current_date = trading_date or now_ist().date().isoformat()
    python_exe = repo / ".venv" / "Scripts" / "python.exe"
    fetcher = repo / "scripts" / "hqe_fyers_historical_5m_data_only_fetcher.py"
    status_path = workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
    csv_path = workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"
    backup_path = workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv.pre_live_cycle_backup"

    had_existing_csv = csv_path.exists()
    if had_existing_csv:
        shutil.copy2(csv_path, backup_path)

    command = [
        str(python_exe),
        str(fetcher),
        "--workspace", str(workspace),
        "--trading-date", current_date,
        "--day-number", str(day_number),
        "--user-id", user_id,
        "--symbol", symbol,
        "--write",
        "--execute-live-data-only",
    ]

    child_env = os.environ.copy()
    token_candidates = [
        repo / "secrets" / "fyers_access_token.txt",
        Path.home() / "AppData" / "Local" / "HunterQuantEngine" / "FyersAuth" / "FYERS_ACCESS_TOKEN.txt",
    ]
    token_source = None
    for candidate in token_candidates:
        if candidate.exists():
            token = candidate.read_text(encoding="utf-8-sig").strip()
            if token:
                child_env["FYERS_ACCESS_TOKEN"] = token
                token_source = str(candidate)
                break

    completed = subprocess.run(
        command,
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
        env=child_env,
    )

    status = read_json(status_path)
    history = status.get("history_result") or {}
    response = history.get("response_redacted") or {}

    api_ok = (
        completed.returncode == 0
        and response.get("s") == "ok"
        and int(response.get("code") or 0) == 200
        and int(history.get("rows") or 0) > 0
    )

    writer_result: Dict[str, Any] = {
        "write_status": "NOT_RUN",
        "written_rows": 0,
        "row_count_match": False,
    }
    restored_previous_csv = False

    if api_ok:
        writer_result = write_from_fetch_status(status_path, csv_path)
        api_ok = (
            writer_result.get("write_status") == "CANDLES_WRITTEN_ATOMICALLY"
            and int(writer_result.get("written_rows") or 0) > 0
            and bool(writer_result.get("row_count_match"))
        )

    if not api_ok:
        if had_existing_csv and backup_path.exists():
            shutil.copy2(backup_path, csv_path)
            restored_previous_csv = True
        elif csv_path.exists():
            csv_path.unlink()

    if backup_path.exists():
        backup_path.unlink()

    payload = {
        "version": VERSION,
        "workspace": str(workspace),
        "trading_date_requested": current_date,
        "command": command,
        "token_hot_reload_enabled": True,
        "token_source": token_source,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-1200:],
        "stderr_tail": completed.stderr[-1200:],
        "api_code": response.get("code"),
        "api_status": response.get("s"),
        "api_message": response.get("message"),
        "api_rows": int(history.get("rows") or 0),
        "writer_result": writer_result,
        "restored_previous_csv": restored_previous_csv,
        "cycle_status": "LIVE_DATA_CYCLE_PASS" if api_ok else "LIVE_DATA_CYCLE_FAILED_GOOD_CSV_PRESERVED",
        "paper_only": True,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }

    atomic_write_json(workspace / STATUS_FILENAME, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE safe current-day live-data cycle")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--repo-root")
    parser.add_argument("--trading-date")
    parser.add_argument("--day-number", type=int, default=1)
    parser.add_argument("--user-id", default="hqe-user")
    parser.add_argument("--symbol", default="NSE:NIFTY50-INDEX")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[1]
    workspace = Path(args.workspace)

    payload = run_cycle(
        repo,
        workspace,
        trading_date=args.trading_date,
        day_number=args.day_number,
        user_id=args.user_id,
        symbol=args.symbol,
    )
    return 0 if payload["cycle_status"] == "LIVE_DATA_CYCLE_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
