#!/usr/bin/env python3
"""
Module 150 - HQE Paper Signal + No-Trade Reason Engine.

Purpose:
- Read real/local paper signal feed evidence.
- Read actual paper trade rows if present.
- If no trade happened, record WHY no trade happened.
- Never create fake trades.
- Never call broker/order/external APIs.
- Never tune the locked forward validation candidate.

This module is a local evidence/reporting engine only.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

VERSION = "MODULE_150_PAPER_SIGNAL_NO_TRADE_REASON_ENGINE_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "data_only": True,
    "local_evidence_only": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}

BLOCKED_ACTIONS = [
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
    "broker_login_for_ordering",
    "candidate_parameter_tuning",
    "fake_trade_injection",
]

APPROVED_DECISIONS = {
    "PAPER_SIGNAL_APPROVED",
    "PAPER_SIGNAL_READY",
    "SIGNAL_APPROVED",
    "TRADE_PLAN_READY",
    "PAPER_TRADE_PLAN_READY",
    "APPROVED",
    "READY",
}

REJECTED_DECISIONS = {
    "REJECTED",
    "BLOCKED",
    "NO_TRADE",
    "NO_SIGNAL",
    "FILTER_REJECTED",
    "SIGNAL_REJECTED",
    "HOLD",
}

TRUE_VALUES = {"1", "true", "yes", "y", "approved", "pass", "ready", "ok"}
FALSE_VALUES = {"0", "false", "no", "n", "rejected", "blocked", "fail", "hold", ""}


@dataclass(frozen=True)
class SignalAnalysis:
    rows: int
    approved_rows: int
    rejected_rows: int
    unknown_rows: int
    reason_counts: Dict[str, int]
    top_reason: str
    examples: List[Dict[str, str]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _today_iso() -> str:
    return date.today().isoformat()


def _normalize_key(value: str) -> str:
    return str(value or "").replace("\ufeff", "").strip().lower()


def _normalize_value(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []
        rows: List[Dict[str, str]] = []
        for raw in reader:
            normalized = {_normalize_key(k): _normalize_value(v) for k, v in raw.items() if k is not None}
            # Ignore fully blank lines.
            if any(v for v in normalized.values()):
                rows.append(normalized)
        return rows


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_markdown(path: Path, payload: Dict[str, Any]) -> None:
    lines = [
        "# HQE Paper Signal + No-Trade Reason Engine",
        "",
        f"- version: `{payload['version']}`",
        f"- engine_status: `{payload['engine_status']}`",
        f"- engine_decision: `{payload['engine_decision']}`",
        f"- trading_date: `{payload['trading_date']}`",
        f"- day_number: `{payload['day_number']}`",
        f"- actual_paper_trades: `{payload['actual_paper_trades']}`",
        f"- signal_feed_rows: `{payload['signal_feed_rows']}`",
        f"- approved_signal_rows: `{payload['approved_signal_rows']}`",
        f"- rejected_signal_rows: `{payload['rejected_signal_rows']}`",
        f"- no_trade_reason: `{payload['no_trade_reason']}`",
        f"- no_trade_reason_detail: `{payload['no_trade_reason_detail']}`",
        f"- external_api_calls_executed: `{payload['external_api_calls_executed']}`",
        f"- order_api_invoked: `{payload['order_api_invoked']}`",
        f"- fake_trades_created: `{payload['fake_trades_created']}`",
        f"- candidate_tuning: `{payload['candidate_tuning']}`",
        "",
        "## Safety lock",
    ]
    for key, value in payload["safety_lock"].items():
        lines.append(f"- {key}: `{value}`")
    if payload.get("reason_counts"):
        lines.extend(["", "## Reason counts"])
        for key, value in payload["reason_counts"].items():
            lines.append(f"- {key}: `{value}`")
    if payload.get("warnings"):
        lines.extend(["", "## Warnings"])
        for warning in payload["warnings"]:
            lines.append(f"- {warning}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_ledger(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "evaluation_time_utc",
        "version",
        "trading_date",
        "day_number",
        "engine_status",
        "engine_decision",
        "actual_paper_trades",
        "signal_feed_rows",
        "approved_signal_rows",
        "rejected_signal_rows",
        "no_trade_reason",
        "external_api_calls_executed",
        "order_api_invoked",
        "fake_trades_created",
        "candidate_tuning",
    ]
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({field: payload.get(field, "") for field in fields})


def _parse_bool(value: Any) -> Optional[bool]:
    normalized = str(value if value is not None else "").strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return None


def _first_value(row: Dict[str, str], keys: Sequence[str]) -> str:
    for key in keys:
        value = row.get(_normalize_key(key), "")
        if value != "":
            return value
    return ""


def _is_approved_signal(row: Dict[str, str]) -> bool:
    explicit_bool = _first_value(
        row,
        [
            "paper_signal_approved",
            "signal_approved",
            "approved",
            "eligible",
            "is_valid_signal",
            "trade_plan_ready",
        ],
    )
    parsed = _parse_bool(explicit_bool)
    if parsed is True:
        return True
    if parsed is False:
        # A clear false should not be overridden by a vague status.
        return False

    decision = _first_value(
        row,
        [
            "paper_signal_decision",
            "signal_decision",
            "decision",
            "status",
            "candidate_status",
            "trade_plan_status",
        ],
    ).strip().upper()
    return decision in APPROVED_DECISIONS


def _is_rejected_signal(row: Dict[str, str]) -> bool:
    if _is_approved_signal(row):
        return False
    explicit_bool = _first_value(
        row,
        [
            "paper_signal_approved",
            "signal_approved",
            "approved",
            "eligible",
            "is_valid_signal",
            "trade_plan_ready",
        ],
    )
    parsed = _parse_bool(explicit_bool)
    if parsed is False:
        return True
    decision = _first_value(
        row,
        [
            "paper_signal_decision",
            "signal_decision",
            "decision",
            "status",
            "candidate_status",
            "trade_plan_status",
        ],
    ).strip().upper()
    return decision in REJECTED_DECISIONS or "REJECT" in decision or "BLOCK" in decision


def _extract_reason(row: Dict[str, str]) -> str:
    reason = _first_value(
        row,
        [
            "no_trade_reason",
            "rejection_reason",
            "blocked_reason",
            "filter_reason",
            "reason",
            "why_no_trade",
            "decision_reason",
            "notes",
        ],
    )
    reason = reason.strip()
    if reason:
        return reason
    decision = _first_value(row, ["paper_signal_decision", "signal_decision", "decision", "status"])
    if decision:
        return f"signal_status={decision}"
    return "SIGNAL_NOT_APPROVED_BY_LOCKED_FILTERS"


def _safe_example(row: Dict[str, str]) -> Dict[str, str]:
    keep = [
        "datetime",
        "timestamp",
        "symbol",
        "option_type",
        "side",
        "signal_decision",
        "decision",
        "status",
        "no_trade_reason",
        "rejection_reason",
        "blocked_reason",
        "reason",
    ]
    return {key: row[key] for key in keep if key in row and row[key]}


def analyze_signal_rows(rows: Sequence[Dict[str, str]]) -> SignalAnalysis:
    approved = 0
    rejected = 0
    unknown = 0
    reasons: Counter[str] = Counter()
    examples: List[Dict[str, str]] = []

    for row in rows:
        if _is_approved_signal(row):
            approved += 1
        elif _is_rejected_signal(row):
            rejected += 1
            reasons[_extract_reason(row)] += 1
        else:
            unknown += 1
            reasons[_extract_reason(row)] += 1
        if len(examples) < 5:
            examples.append(_safe_example(row))

    top_reason = ""
    if reasons:
        top_reason = reasons.most_common(1)[0][0]

    return SignalAnalysis(
        rows=len(rows),
        approved_rows=approved,
        rejected_rows=rejected,
        unknown_rows=unknown,
        reason_counts=dict(reasons.most_common()),
        top_reason=top_reason,
        examples=examples,
    )


def _discover_signal_feed(workspace: Path, day_number: int) -> Optional[Path]:
    candidates = [
        workspace / f"DAY_{day_number:03d}_FORWARD_SIGNAL_FEED.csv",
        workspace / f"DAY_{day_number:03d}_FORWARD_SIGNALS.csv",
        workspace / f"DAY_{day_number:03d}_PAPER_SIGNAL_FEED.csv",
        workspace / "FORWARD_SIGNAL_FEED.csv",
        workspace / "PAPER_SIGNAL_FEED.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _discover_trade_log(workspace: Path, day_number: int) -> Optional[Path]:
    candidates = [
        workspace / f"DAY_{day_number:03d}_FORWARD_TRADE_LOG.csv",
        workspace / f"DAY_{day_number:03d}_PAPER_TRADE_LOG.csv",
        workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _actual_trade_rows(path: Optional[Path]) -> List[Dict[str, str]]:
    if path is None:
        return []
    rows = _read_csv_rows(path)
    # Do not manufacture rows. Count only rows that have some trade-like evidence.
    trade_like: List[Dict[str, str]] = []
    trade_keys = {
        "entry_time",
        "exit_time",
        "symbol",
        "option_type",
        "side",
        "qty",
        "entry_price",
        "exit_price",
        "net_pnl",
        "pnl",
        "paper_trade_id",
        "trade_id",
    }
    for row in rows:
        if any(row.get(key, "") for key in trade_keys):
            trade_like.append(row)
    return trade_like


def evaluate_paper_signal_no_trade_reason(
    workspace: Path,
    trading_date: Optional[str] = None,
    day_number: int = 1,
    signal_feed: Optional[Path] = None,
    trade_log: Optional[Path] = None,
    write: bool = False,
) -> Dict[str, Any]:
    workspace = Path(workspace)
    trading_date = trading_date or _today_iso()
    signal_feed = Path(signal_feed) if signal_feed else _discover_signal_feed(workspace, day_number)
    trade_log = Path(trade_log) if trade_log else _discover_trade_log(workspace, day_number)

    warnings: List[str] = []
    signal_rows: List[Dict[str, str]] = []
    signal_analysis = SignalAnalysis(0, 0, 0, 0, {}, "", [])
    actual_rows = _actual_trade_rows(trade_log)
    actual_trade_count = len(actual_rows)

    if signal_feed is not None and signal_feed.exists():
        signal_rows = _read_csv_rows(signal_feed)
        signal_analysis = analyze_signal_rows(signal_rows)

    no_trade_reason = ""
    no_trade_reason_detail = ""
    engine_decision = ""

    if actual_trade_count > 0:
        engine_decision = "ACTUAL_PAPER_TRADE_ROWS_PRESENT"
        no_trade_reason = "TRADE_TAKEN_FROM_ACTUAL_PAPER_ROWS"
        no_trade_reason_detail = "Actual paper trade row evidence exists; no no-trade reason is needed."
    elif signal_feed is None:
        engine_decision = "NO_TRADE_REASON_RECORDED"
        no_trade_reason = "MISSING_SIGNAL_FEED"
        no_trade_reason_detail = "No local paper signal feed file was found for the day. No trade was created."
        warnings.append("Signal feed missing; report records no-trade reason without creating fake trades.")
    elif signal_analysis.rows == 0:
        engine_decision = "NO_TRADE_REASON_RECORDED"
        no_trade_reason = "EMPTY_SIGNAL_FEED"
        no_trade_reason_detail = "Signal feed exists but contains no usable signal rows."
    elif signal_analysis.approved_rows > 0:
        engine_decision = "PAPER_SIGNAL_PRESENT_AWAITING_ACTUAL_PAPER_TRADE_ROW"
        no_trade_reason = "APPROVED_PAPER_SIGNAL_PRESENT_BUT_NO_ACTUAL_PAPER_TRADE_ROW"
        no_trade_reason_detail = (
            "Approved paper signal rows exist, but no actual paper trade rows were found. "
            "The engine does not create fake trades or orders."
        )
        warnings.append("Approved signal present without paper trade row; manual/local workflow review may be needed.")
    else:
        engine_decision = "NO_TRADE_REASON_RECORDED"
        no_trade_reason = signal_analysis.top_reason or "ALL_SIGNALS_REJECTED_BY_LOCKED_FILTERS"
        no_trade_reason_detail = "No approved signal rows were found; locked validation filters rejected/blocked all rows."

    payload: Dict[str, Any] = {
        "version": VERSION,
        "evaluation_time_utc": _utc_now(),
        "workspace": str(workspace),
        "trading_date": trading_date,
        "day_number": int(day_number),
        "engine_status": "PASS",
        "engine_decision": engine_decision,
        "signal_feed_path": str(signal_feed) if signal_feed else "",
        "trade_log_path": str(trade_log) if trade_log else "",
        "signal_feed_rows": signal_analysis.rows,
        "approved_signal_rows": signal_analysis.approved_rows,
        "rejected_signal_rows": signal_analysis.rejected_rows,
        "unknown_signal_rows": signal_analysis.unknown_rows,
        "reason_counts": signal_analysis.reason_counts,
        "signal_examples": signal_analysis.examples,
        "actual_paper_trades": actual_trade_count,
        "no_trade_reason": no_trade_reason,
        "no_trade_reason_detail": no_trade_reason_detail,
        "watch_window": {
            "market_session_start": "09:15",
            "market_session_end": "15:30",
            "timezone": "Asia/Kolkata",
        },
        "locked_validation_candidate_unchanged": True,
        "external_api_calls_executed": False,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "fake_trades_created": False,
        "candidate_tuning": False,
        "profitability_claim": False,
        "safety_lock": dict(SAFETY_LOCK),
        "warnings": warnings,
    }

    if write:
        json_path = workspace / f"DAY_{day_number:03d}_PAPER_SIGNAL_NO_TRADE_REASON.json"
        md_path = workspace / f"DAY_{day_number:03d}_PAPER_SIGNAL_NO_TRADE_REASON.md"
        ledger_path = workspace / "PAPER_SIGNAL_NO_TRADE_REASON_LEDGER.csv"
        _write_json(json_path, payload)
        _write_markdown(md_path, payload)
        _append_ledger(ledger_path, payload)
        payload["evidence_files"] = {
            "json": str(json_path),
            "markdown": str(md_path),
            "ledger": str(ledger_path),
        }
        _write_json(json_path, payload)
        _write_markdown(md_path, payload)

    return payload


def guard_check() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "blocked_actions": {name: "HARD_BLOCKED" for name in BLOCKED_ACTIONS},
        "external_api_calls_executed": False,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "fake_trades_created": False,
        "candidate_tuning": False,
        "safety_lock": dict(SAFETY_LOCK),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HQE Module 150 Paper Signal + No-Trade Reason Engine")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Forward validation workspace folder")
    parser.add_argument("--trading-date", default=None, help="Trading date YYYY-MM-DD")
    parser.add_argument("--day-number", type=int, default=1, help="Forward validation day number")
    parser.add_argument("--signal-feed", default=None, help="Optional explicit signal feed CSV path")
    parser.add_argument("--trade-log", default=None, help="Optional explicit actual paper trade CSV path")
    parser.add_argument("--write", action="store_true", help="Write JSON/Markdown/ledger evidence files")
    parser.add_argument("--guard-check", action="store_true", help="Show hard safety guards")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.guard_check:
        print(json.dumps(guard_check(), indent=2, sort_keys=True))
        return 0

    payload = evaluate_paper_signal_no_trade_reason(
        workspace=Path(args.workspace),
        trading_date=args.trading_date,
        day_number=args.day_number,
        signal_feed=Path(args.signal_feed) if args.signal_feed else None,
        trade_log=Path(args.trade_log) if args.trade_log else None,
        write=args.write,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
