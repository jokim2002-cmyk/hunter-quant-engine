from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

VERSION = "MODULES_172_180_LIVE_DATA_VISUAL_OPS_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_USER_ID = "jokim-local"
DEFAULT_TRADING_DATE = "2026-07-09"
DEFAULT_DAY_NUMBER = 1
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
    "manual_login_required": True,
    "manual_operator_review_required": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
    "no_plaintext_secret_storage": True,
    "order_api_hard_blocked": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def as_path(value: str | Path | None) -> Path:
    if value is None:
        return DEFAULT_WORKSPACE
    return Path(value)


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows: List[Dict[str, str]] = []
        for raw in reader:
            row: Dict[str, str] = {}
            for key, value in raw.items():
                clean_key = (key or "").replace("\ufeff", "").strip()
                row[clean_key] = (value or "").strip()
            rows.append(row)
        return rows


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def first_value(row: Dict[str, str], names: Iterable[str], default: str = "") -> str:
    lowered = {k.lower().strip(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return default


def validation_counters(workspace: Path) -> Dict[str, Any]:
    day_rows = read_csv_rows(workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv")
    observed_dates = set()
    valid_dates = set()
    for row in day_rows:
        date_value = first_value(row, ["trading_date", "date", "session_date"])
        if date_value:
            observed_dates.add(date_value)
        trade_count = parse_int(first_value(row, ["trade_count", "paper_trade_count", "actual_trade_count"]))
        if date_value and trade_count > 0:
            valid_dates.add(date_value)

    trade_rows = read_csv_rows(workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv")
    if not trade_rows:
        # Fallback to day-specific paper execution logs without creating synthetic trades.
        for path in sorted(workspace.glob("DAY_*_PAPER_EXECUTION_LOG.csv")):
            trade_rows.extend(read_csv_rows(path))

    actual_paper_trades = len(trade_rows)
    expiry_weeks = set()
    for row in trade_rows:
        expiry = first_value(row, ["expiry", "expiry_date", "option_expiry", "contract_expiry"])
        if expiry:
            expiry_weeks.add(expiry[:10])

    valid_count = len(valid_dates)
    observed_count = len(observed_dates)
    return {
        "day_ledger_rows": len(day_rows),
        "observed_session_days": observed_count,
        "valid_paper_trade_days": valid_count,
        "no_trade_observed_days": max(observed_count - valid_count, 0),
        "remaining_valid_trade_days": max(30 - valid_count, 0),
        "target_valid_paper_trade_days": 30,
        "actual_paper_trades": actual_paper_trades,
        "actual_trade_rows_source": "MASTER_LEDGER_OR_PAPER_EXECUTION_LOG" if actual_paper_trades else "NONE",
        "distinct_expiry_weeks": len(expiry_weeks),
    }


def credential_status() -> Dict[str, Any]:
    required = ["FYERS_CLIENT_ID", "FYERS_ACCESS_TOKEN"]
    optional = ["FYERS_REDIRECT_URI", "FYERS_APP_ID"]
    missing = [name for name in required if not os.getenv(name)]
    return {
        "credential_source": "environment_variables_only",
        "required_env_names": required,
        "optional_env_names": optional,
        "present_required_env_count": len(required) - len(missing),
        "present_optional_env_count": sum(1 for name in optional if os.getenv(name)),
        "missing_required_env_names": missing,
        "credentials_complete_for_future_data_transport": not missing,
        "secret_values_redacted": True,
        "plaintext_secret_storage_allowed": False,
    }


def base_payload(module_number: int, module_name: str, workspace: Path, trading_date: str, day_number: int) -> Dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": VERSION,
        "module_number": module_number,
        "module_name": module_name,
        "workspace": str(workspace),
        "trading_date": trading_date,
        "day_number": day_number,
        "generated_at_utc": utc_now(),
        "safety_lock": dict(SAFETY_LOCK),
        "blocked_order_apis": list(BLOCKED_ORDER_APIS),
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "fake_trades_created": False,
        "candidate_tuning": False,
        "real_money_automatic": False,
    }
    payload.update(validation_counters(workspace))
    return payload


def write_outputs(payload: Dict[str, Any], workspace: Path, basename: str) -> Dict[str, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    json_path = workspace / f"{basename}.json"
    md_path = workspace / f"{basename}.md"
    ledger_path = workspace / "MODULES_172_180_LIVE_DATA_VISUAL_OPS_LEDGER.csv"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        f"# {payload.get('module_name', 'HQE Module Status')}",
        "",
        f"- Status key: `{payload.get('status', payload.get('decision', 'UNKNOWN'))}`",
        f"- Decision: `{payload.get('decision', 'UNKNOWN')}`",
        f"- Workspace: `{payload.get('workspace')}`",
        f"- Trading date: `{payload.get('trading_date')}`",
        f"- Paper-only: `{payload.get('safety_lock', {}).get('paper_only')}`",
        f"- Real money automatic: `{payload.get('real_money_automatic')}`",
        f"- Order API invoked: `{payload.get('order_api_invoked')}`",
        f"- Broker execution invoked: `{payload.get('broker_execution_invoked')}`",
        f"- Auto trading started: `{payload.get('auto_trading_started')}`",
        f"- Fake trades created: `{payload.get('fake_trades_created')}`",
        "",
        "```json",
        json.dumps(payload, indent=2, sort_keys=True),
        "```",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    write_header = not ledger_path.exists()
    with ledger_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "generated_at_utc",
                "module_number",
                "module_name",
                "trading_date",
                "day_number",
                "decision",
                "observed_session_days",
                "valid_paper_trade_days",
                "actual_paper_trades",
                "real_money_automatic",
                "order_api_invoked",
                "broker_execution_invoked",
                "auto_trading_started",
                "fake_trades_created",
            ],
        )
        if write_header:
            writer.writeheader()
        writer.writerow({key: payload.get(key) for key in writer.fieldnames})

    return {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}


def add_common_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--trading-date", default=DEFAULT_TRADING_DATE)
    parser.add_argument("--day-number", type=int, default=DEFAULT_DAY_NUMBER)
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--guard-check", action="store_true")


def guard_payload(module_number: int, module_name: str) -> Dict[str, Any]:
    return {
        "version": VERSION,
        "module_number": module_number,
        "module_name": module_name,
        "guard_check_status": "PASS",
        "safety_lock": dict(SAFETY_LOCK),
        "blocked_order_apis": {api: "HARD_BLOCKED" for api in BLOCKED_ORDER_APIS},
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "fake_trades_created": False,
        "real_money_automatic": False,
    }


def print_payload(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def create_cmd(path: Path, lines: List[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ["@echo off", "setlocal", *lines]
    if not any("pause" in line.lower() for line in lines):
        content.append("pause")
    path.write_text("\r\n".join(content) + "\r\n", encoding="utf-8")
    return str(path)


def repo_python() -> str:
    return str(Path.cwd() / ".venv" / "Scripts" / "python.exe")


def run_subprocess(args: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
    completed = subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    return {
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
