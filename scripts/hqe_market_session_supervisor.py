#!/usr/bin/env python3
"""
HQE Module 149: Market Session Supervisor 09:15-15:30

Purpose:
- Local-only market session gate for forward paper validation.
- Decides whether HQE is in pre-market wait, market watch active, post-market report due,
  or non-trading day closed state.
- Writes local evidence files when requested.

Safety:
- Paper/simulation only.
- No broker execution.
- No real orders.
- No auto trading.
- No option selling.
- No external API calls.
- No fake trades.
- No candidate tuning during validation.
- No profitability claim.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

VERSION = "MODULE_149_MARKET_SESSION_SUPERVISOR_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_SESSION_START = "09:15"
DEFAULT_SESSION_END = "15:30"
IST = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "data_only": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
    "order_api_hard_blocked": True,
}

BLOCKED_ACTIONS: List[str] = [
    "broker_execution",
    "real_order_placement",
    "auto_trading",
    "option_selling",
    "candidate_tuning",
    "fake_trade_creation",
    "external_api_call_from_supervisor",
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

LOCAL_ALLOWED_ACTIONS: Dict[str, List[str]] = {
    "PRE_MARKET_WAIT": [
        "local_login_check",
        "local_data_only_preflight",
        "local_workspace_evidence_write",
    ],
    "MARKET_WATCH_ACTIVE": [
        "local_heartbeat_write",
        "future_data_only_market_watch",
        "paper_only_signal_evaluation",
        "paper_only_no_trade_reason_capture",
    ],
    "POST_MARKET_REPORT_DUE": [
        "local_report_generation",
        "local_day_close_evidence_write",
        "local_no_trade_reason_report",
    ],
    "MARKET_CLOSED_NON_TRADING_DAY": [
        "local_closed_day_status_write",
        "local_operator_message",
    ],
}


@dataclass(frozen=True)
class MarketSessionConfig:
    market_symbol: str = "NSE:NIFTY50-INDEX"
    market_session_start: str = DEFAULT_SESSION_START
    market_session_end: str = DEFAULT_SESSION_END
    timezone_name: str = "Asia/Kolkata"
    trading_days: str = "MONDAY_TO_FRIDAY_LOCAL_ONLY"
    holiday_calendar_source: str = "NOT_CONNECTED_LOCAL_WEEKDAY_ONLY"
    module_version: str = VERSION


def parse_hhmm(value: str) -> time:
    try:
        hour_str, minute_str = value.split(":", 1)
        hour = int(hour_str)
        minute = int(minute_str)
    except Exception as exc:  # pragma: no cover - defensive formatting path
        raise ValueError(f"Invalid HH:MM time value: {value!r}") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid HH:MM time value: {value!r}")
    return time(hour=hour, minute=minute)


def parse_now(value: Optional[str]) -> datetime:
    """Parse an optional ISO timestamp and return timezone-aware IST datetime.

    If no timestamp is supplied, local current time in IST is used. A naive timestamp is
    assumed to already be in IST. A timestamp with Z/offset is converted to IST.
    """
    if not value:
        return datetime.now(tz=IST)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Invalid --now ISO timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=IST)
    return parsed.astimezone(IST)


def is_local_trading_weekday(moment_ist: datetime) -> bool:
    return moment_ist.weekday() < 5


def decide_session_phase(moment_ist: datetime, session_start: str = DEFAULT_SESSION_START, session_end: str = DEFAULT_SESSION_END) -> str:
    start = parse_hhmm(session_start)
    end = parse_hhmm(session_end)
    if start >= end:
        raise ValueError("market_session_start must be earlier than market_session_end")

    if not is_local_trading_weekday(moment_ist):
        return "MARKET_CLOSED_NON_TRADING_DAY"

    current = moment_ist.time().replace(second=0, microsecond=0)
    if current < start:
        return "PRE_MARKET_WAIT"
    if start <= current <= end:
        return "MARKET_WATCH_ACTIVE"
    return "POST_MARKET_REPORT_DUE"


def build_supervisor_result(
    workspace: Path,
    now_value: Optional[str] = None,
    session_start: str = DEFAULT_SESSION_START,
    session_end: str = DEFAULT_SESSION_END,
) -> Dict[str, Any]:
    now_ist = parse_now(now_value)
    phase = decide_session_phase(now_ist, session_start=session_start, session_end=session_end)

    trading_weekday = is_local_trading_weekday(now_ist)
    watch_active = phase == "MARKET_WATCH_ACTIVE"
    pre_market = phase == "PRE_MARKET_WAIT"
    post_market = phase == "POST_MARKET_REPORT_DUE"
    non_trading_day = phase == "MARKET_CLOSED_NON_TRADING_DAY"

    result: Dict[str, Any] = {
        "version": VERSION,
        "supervisor_status": "PASS",
        "workspace": str(workspace),
        "market_symbol": "NSE:NIFTY50-INDEX",
        "timezone": "Asia/Kolkata",
        "now_ist": now_ist.isoformat(),
        "trading_date": now_ist.date().isoformat(),
        "weekday": now_ist.strftime("%A"),
        "trading_weekday_local_only": trading_weekday,
        "holiday_calendar_source": "NOT_CONNECTED_LOCAL_WEEKDAY_ONLY",
        "market_session_start": session_start,
        "market_session_end": session_end,
        "session_phase": phase,
        "watch_window_active": watch_active,
        "pre_market_wait": pre_market,
        "post_market_report_due": post_market,
        "non_trading_day_closed": non_trading_day,
        "should_watch_market": watch_active,
        "should_generate_daily_report": post_market,
        "should_generate_closed_day_status": non_trading_day,
        "observed_session_day_ledger_update_performed": False,
        "valid_trade_day_counter_update_performed": False,
        "actual_trade_rows_created": 0,
        "external_api_calls_executed": False,
        "broker_connection_started": False,
        "order_api_invoked": False,
        "paper_signal_execution_invoked": False,
        "allowed_local_actions": LOCAL_ALLOWED_ACTIONS[phase],
        "blocked_actions": BLOCKED_ACTIONS,
        "config": asdict(MarketSessionConfig(market_session_start=session_start, market_session_end=session_end)),
        "safety_lock": dict(SAFETY_LOCK),
        "decision": phase,
        "next_module_dependency": "MODULE_150_PAPER_SIGNAL_AND_NO_TRADE_REASON_ENGINE",
        "warnings": [],
    }

    if non_trading_day:
        result["warnings"].append("Local weekday-only calendar says market is closed. Exchange holidays are not checked because supervisor is local-only.")
    if pre_market:
        result["warnings"].append("Market watch is not active yet; wait until 09:15 IST.")
    if post_market:
        result["warnings"].append("Market watch window ended; daily paper report/no-trade reason workflow is due.")

    return result


def evidence_paths(workspace: Path) -> Dict[str, Path]:
    return {
        "json": workspace / "MARKET_SESSION_SUPERVISOR_STATUS.json",
        "markdown": workspace / "MARKET_SESSION_SUPERVISOR_STATUS.md",
        "ledger": workspace / "MARKET_SESSION_SUPERVISOR_LEDGER.csv",
    }


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: Dict[str, Any]) -> None:
    lines = [
        "# HQE Market Session Supervisor",
        "",
        f"- version: `{payload['version']}`",
        f"- supervisor_status: `{payload['supervisor_status']}`",
        f"- decision: `{payload['decision']}`",
        f"- trading_date: `{payload['trading_date']}`",
        f"- now_ist: `{payload['now_ist']}`",
        f"- session: `{payload['market_session_start']} - {payload['market_session_end']} IST`",
        f"- watch_window_active: `{payload['watch_window_active']}`",
        f"- should_watch_market: `{payload['should_watch_market']}`",
        f"- should_generate_daily_report: `{payload['should_generate_daily_report']}`",
        f"- external_api_calls_executed: `{payload['external_api_calls_executed']}`",
        f"- order_api_invoked: `{payload['order_api_invoked']}`",
        "",
        "## Safety Lock",
    ]
    for key, value in payload["safety_lock"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Blocked Actions",
    ])
    for action in payload["blocked_actions"]:
        lines.append(f"- `{action}`")
    lines.extend([
        "",
        "## Notes",
        "This module is local-only. It does not connect to Fyers, does not place orders, does not create fake trades, and does not claim profitability.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_ledger(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "trading_date",
        "now_ist",
        "supervisor_status",
        "decision",
        "watch_window_active",
        "should_watch_market",
        "should_generate_daily_report",
        "external_api_calls_executed",
        "order_api_invoked",
        "paper_only",
        "no_real_orders",
        "no_auto_trading",
        "no_fake_trades",
        "no_candidate_tuning_during_validation",
    ]
    write_header = not path.exists() or path.stat().st_size == 0
    row = {
        "trading_date": payload["trading_date"],
        "now_ist": payload["now_ist"],
        "supervisor_status": payload["supervisor_status"],
        "decision": payload["decision"],
        "watch_window_active": payload["watch_window_active"],
        "should_watch_market": payload["should_watch_market"],
        "should_generate_daily_report": payload["should_generate_daily_report"],
        "external_api_calls_executed": payload["external_api_calls_executed"],
        "order_api_invoked": payload["order_api_invoked"],
        "paper_only": payload["safety_lock"]["paper_only"],
        "no_real_orders": payload["safety_lock"]["no_real_orders"],
        "no_auto_trading": payload["safety_lock"]["no_auto_trading"],
        "no_fake_trades": payload["safety_lock"]["no_fake_trades"],
        "no_candidate_tuning_during_validation": payload["safety_lock"]["no_candidate_tuning_during_validation"],
    }
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def write_evidence(workspace: Path, payload: Dict[str, Any]) -> Dict[str, str]:
    paths = evidence_paths(workspace)
    write_json(paths["json"], payload)
    write_markdown(paths["markdown"], payload)
    append_ledger(paths["ledger"], payload)
    return {key: str(value) for key, value in paths.items()}


def run_supervisor(
    workspace: Path = DEFAULT_WORKSPACE,
    now_value: Optional[str] = None,
    write: bool = False,
    session_start: str = DEFAULT_SESSION_START,
    session_end: str = DEFAULT_SESSION_END,
) -> Dict[str, Any]:
    payload = build_supervisor_result(
        workspace=workspace,
        now_value=now_value,
        session_start=session_start,
        session_end=session_end,
    )
    if write:
        payload["evidence_files"] = write_evidence(workspace, payload)
    return payload


def hard_block_action(action_name: str) -> None:
    if action_name in BLOCKED_ACTIONS or "order" in action_name.lower() or "trade" in action_name.lower():
        raise PermissionError(f"ACTION_BLOCKED_BY_MODULE_149_SESSION_SUPERVISOR:{action_name}")
    raise PermissionError(f"UNKNOWN_ACTION_BLOCKED_BY_DEFAULT:{action_name}")


def build_guard_check() -> Dict[str, Any]:
    blocked: Dict[str, str] = {}
    for action in BLOCKED_ACTIONS:
        try:
            hard_block_action(action)
        except PermissionError as exc:
            blocked[action] = str(exc)
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "blocked_actions": blocked,
        "external_api_calls_executed": False,
        "order_api_invoked": False,
        "safety_lock": dict(SAFETY_LOCK),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HQE Module 149 Market Session Supervisor")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Forward validation workspace path")
    parser.add_argument("--now", default=None, help="Optional ISO timestamp. Naive timestamps are treated as IST.")
    parser.add_argument("--write", action="store_true", help="Write local evidence files to workspace")
    parser.add_argument("--session-start", default=DEFAULT_SESSION_START, help="Market session start HH:MM IST")
    parser.add_argument("--session-end", default=DEFAULT_SESSION_END, help="Market session end HH:MM IST")
    parser.add_argument("--guard-check", action="store_true", help="Print hard-block guard check and exit")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_arg_parser().parse_args(list(argv) if argv is not None else None)
    if args.guard_check:
        print(json.dumps(build_guard_check(), indent=2, sort_keys=True))
        return 0
    payload = run_supervisor(
        workspace=Path(args.workspace),
        now_value=args.now,
        write=args.write,
        session_start=args.session_start,
        session_end=args.session_end,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

