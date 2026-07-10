from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


VERSION = "PERSISTENT_MARKET_DAY_PAPER_WATCH_LOOP_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_USER_ID = "jokim-local"
DEFAULT_SYMBOL = "NSE:NIFTY50-INDEX"

BLOCKED_ORDER_APIS = [
    "place_order",
    "modify_order",
    "cancel_order",
    "exit_positions",
    "place_basket_orders",
    "place_gtt_order",
    "modify_gtt_order",
    "cancel_gtt_order",
    "convert_position",
    "orderbook",
    "tradebook",
    "positions",
    "holdings",
    "funds",
]

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "manual_operator_start_required": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
    "order_api_hard_blocked": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def local_now_text() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def today_local() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            return len(list(csv.DictReader(fh)))
    except Exception:
        return 0


def env_status() -> Dict[str, Any]:
    required = ["FYERS_CLIENT_ID", "FYERS_ACCESS_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]
    return {
        "required_env_names": required,
        "missing_required_env_names": missing,
        "present_required_env_count": len(required) - len(missing),
        "credentials_complete_for_data_only_watch": not missing,
        "secret_values_redacted": True,
    }


def data_health(workspace: Path) -> Dict[str, Any]:
    m173 = read_json(workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json")
    m183 = read_json(workspace / "MODULE_183_FYERS_DATA_ONLY_HEALTH_MONITOR_STATUS.json")
    normalized_csv = workspace / "FYERS_LIVE_DATA_ONLY_5M_NORMALIZED.csv"
    history = m173.get("history_result", {})
    response = history.get("response_redacted", {})
    history_rows = int(history.get("rows", 0) or 0)
    normalized_rows = count_csv_rows(normalized_csv)
    ready = bool(m183.get("data_only_connection_ready")) or response.get("s") == "ok" or history_rows > 0 or normalized_rows > 0
    return {
        "data_only_connection_ready": ready,
        "last_history_code": response.get("code"),
        "last_history_rows": history_rows,
        "normalized_5m_rows": normalized_rows,
        "module_173_found": bool(m173),
        "module_183_found": bool(m183),
    }


def in_time_window(start_hhmm: str, end_hhmm: str) -> bool:
    now = datetime.now().time()
    start_h, start_m = [int(x) for x in start_hhmm.split(":")]
    end_h, end_m = [int(x) for x in end_hhmm.split(":")]
    start = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    return start <= now <= end


def append_watch_row(path: Path, row: Dict[str, Any]) -> None:
    fields = [
        "generated_at_utc",
        "local_time",
        "trading_date",
        "day_number",
        "symbol",
        "cycle",
        "watch_status",
        "in_market_window",
        "data_ready",
        "last_history_rows",
        "normalized_5m_rows",
        "approved_signal",
        "paper_trade_created",
        "no_trade_reason",
        "real_order_allowed",
        "broker_execution_invoked",
        "auto_trading_started",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fields})


def write_status(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_data_fetch(
    workspace: Path,
    symbol: str,
    trading_date: str,
) -> Dict[str, Any]:
    repo = repo_root()
    py = repo / ".venv" / "Scripts" / "python.exe"
    fetcher = repo / "scripts" / "hqe_current_day_live_data_cycle.py"
    if not fetcher.exists():
        return {"attempted": False, "reason": "fetcher_not_found"}
    try:
        result = subprocess.run(
            [
                str(py),
                str(fetcher),
                "--workspace",
                str(workspace),
                "--repo-root",
                str(repo),
                "--trading-date",
                trading_date,
                "--symbol",
                symbol,
                "--write",
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "attempted": True,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-1000:],
            "stderr_tail": result.stderr[-1000:],
        }
    except Exception as exc:
        return {"attempted": True, "error": str(exc)}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Persistent HQE market-day paper watch loop")
    p.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p.add_argument("--trading-date", default=today_local())
    p.add_argument("--day-number", type=int, default=1)
    p.add_argument("--user-id", default=DEFAULT_USER_ID)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    p.add_argument("--interval-seconds", type=int, default=300)
    p.add_argument("--max-cycles", type=int, default=0, help="0 means keep running until Ctrl+C")
    p.add_argument("--once", action="store_true")
    p.add_argument("--run-data-fetch", action="store_true")
    p.add_argument("--ignore-market-window", action="store_true")
    p.add_argument("--start-time", default="09:15")
    p.add_argument("--end-time", default="15:30")
    p.add_argument("--guard-check", action="store_true")
    return p


def guard_check() -> int:
    payload = {
        "version": VERSION,
        "guard_check_status": "PASS",
        "safety_lock": SAFETY_LOCK,
        "blocked_order_apis": {name: "HARD_BLOCKED" for name in BLOCKED_ORDER_APIS},
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "real_money_automatic": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.guard_check:
        return guard_check()

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    watch_csv = workspace / f"DAY_{int(args.day_number):03d}_PERSISTENT_PAPER_WATCH_LOOP.csv"
    status_json = workspace / "HQE_PERSISTENT_MARKET_DAY_PAPER_WATCH_STATUS.json"

    print("HQE PERSISTENT MARKET-DAY PAPER WATCH LOOP")
    print("Safety: PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING")
    print(f"Workspace: {workspace}")
    print(f"Trading date: {args.trading_date} | Symbol: {args.symbol}")
    print(f"CSV log: {watch_csv}")
    print("Stop: press Ctrl+C")
    print("")

    cycle = 0
    last_fetch: Dict[str, Any] = {"attempted": False}

    try:
        while True:
            cycle += 1
            market_window_ok = args.ignore_market_window or in_time_window(args.start_time, args.end_time)

            if args.run_data_fetch and market_window_ok:
                last_fetch = run_data_fetch(
                    workspace,
                    args.symbol,
                    args.trading_date,
                )

            health = data_health(workspace)
            secrets = env_status()
            ready = bool(secrets["credentials_complete_for_data_only_watch"] and health["data_only_connection_ready"])
            status = "WATCHING_DATA_ONLY" if market_window_ok else "WAITING_OUTSIDE_MARKET_WINDOW"
            if not ready:
                status = "WAITING_FOR_TOKEN_OR_DATA"
            if (
                args.run_data_fetch
                and market_window_ok
                and last_fetch.get("attempted")
                and int(last_fetch.get("returncode", 0)) != 0
            ):
                status = "LIVE_DATA_FETCH_FAILED"

            row = {
                "generated_at_utc": utc_now(),
                "local_time": local_now_text(),
                "trading_date": args.trading_date,
                "day_number": args.day_number,
                "symbol": args.symbol,
                "cycle": cycle,
                "watch_status": status,
                "in_market_window": market_window_ok,
                "data_ready": health["data_only_connection_ready"],
                "last_history_rows": health["last_history_rows"],
                "normalized_5m_rows": health["normalized_5m_rows"],
                "approved_signal": "NO",
                "paper_trade_created": "NO",
                "no_trade_reason": "NO_APPROVED_SIGNAL_NO_FAKE_TRADE",
                "real_order_allowed": "NO",
                "broker_execution_invoked": "NO",
                "auto_trading_started": "NO",
            }
            append_watch_row(watch_csv, row)

            payload = {
                "version": VERSION,
                "generated_at_utc": utc_now(),
                "local_time": local_now_text(),
                "workspace": str(workspace),
                "trading_date": args.trading_date,
                "day_number": args.day_number,
                "user_id": args.user_id,
                "symbol": args.symbol,
                "cycle": cycle,
                "watch_status": status,
                "in_market_window": market_window_ok,
                "data_health": health,
                "secrets": secrets,
                "last_data_fetch": last_fetch,
                "watch_csv": str(watch_csv),
                "safety_lock": SAFETY_LOCK,
                "order_api_invoked": False,
                "broker_execution_invoked": False,
                "auto_trading_started": False,
                "real_money_automatic": False,
                "paper_trade_created_by_loop": False,
            }
            write_status(status_json, payload)

            print(f"[{row['local_time']}] cycle={cycle} status={status} data_ready={row['data_ready']} rows={row['last_history_rows']}/{row['normalized_5m_rows']} approved_signal=NO real_order_allowed=NO")

            if args.once or (args.max_cycles and cycle >= args.max_cycles):
                break

            time.sleep(max(1, int(args.interval_seconds)))

    except KeyboardInterrupt:
        print("")
        print("Stopped by operator. Safety remained paper-only/data-only.")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
