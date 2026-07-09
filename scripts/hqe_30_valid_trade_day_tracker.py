#!/usr/bin/env python3
"""
HQE Module 151: 30 Valid Trade-Day Validation Tracker.

Local/paper-only tracker for forward validation progress:
- observed session days count from FORWARD_VALIDATION_DAY_LEDGER.csv;
- valid paper trade days count only from actual paper trade rows grouped by date;
- no-trade days are observed but do NOT count toward the 30 valid trade-day target;
- expiry weeks are derived only from actual trade rows;
- no broker execution, no order API, no external API, no fake trades, no tuning.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

VERSION = "MODULE_151_30_VALID_TRADE_DAY_TRACKER_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_VALID_TRADE_DAY_TARGET = 30
DEFAULT_MIN_TRADES_REQUIRED = 30
DEFAULT_MIN_EXPIRY_WEEKS_REQUIRED = 4

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "data_only": True,
    "local_only": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
    "real_money_requires_future_manual_review": True,
}

ORDER_API_INVOKED = False
BROKER_EXECUTION_INVOKED = False
EXTERNAL_API_CALLS_EXECUTED = False
FAKE_TRADES_CREATED = False
CANDIDATE_TUNING = False

DATE_FIELDS = (
    "trading_date",
    "date",
    "day_date",
    "session_date",
    "trade_date",
    "entry_date",
    "entry_time",
    "entry_datetime",
    "datetime",
    "timestamp",
    "created_at",
)

TRADE_COUNT_FIELDS = (
    "trade_count",
    "actual_paper_trades",
    "paper_trade_count",
    "completed_trades",
    "trades",
)

NET_FIELDS = (
    "net_pnl",
    "net",
    "net_profit",
    "pnl",
    "paper_net",
    "estimated_net",
    "realized_net",
)

EXPIRY_FIELDS = (
    "expiry_date",
    "expiry",
    "option_expiry",
    "contract_expiry",
    "instrument_expiry",
)

MASTER_LEDGER_NAMES = (
    "FORWARD_VALIDATION_MASTER_LEDGER.csv",
    "FORWARD_PAPER_MASTER_LEDGER.csv",
    "FORWARD_MASTER_LEDGER.csv",
)

DAY_LEDGER_NAME = "FORWARD_VALIDATION_DAY_LEDGER.csv"
DAY_TRADE_LOG_PATTERN = "DAY_*_FORWARD_TRADE_LOG.csv"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_key(value: Any) -> str:
    text = str(value or "").replace("\ufeff", "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _normalize_row(row: Dict[str, Any]) -> Dict[str, str]:
    return {_normalize_key(k): str(v or "").strip() for k, v in row.items()}


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []
        rows: List[Dict[str, str]] = []
        for row in reader:
            normalized = _normalize_row(row)
            if any(str(value).strip() for value in normalized.values()):
                rows.append(normalized)
        return rows


def _first_value(row: Dict[str, str], fields: Sequence[str]) -> str:
    for field in fields:
        key = _normalize_key(field)
        value = row.get(key, "")
        if str(value).strip():
            return str(value).strip()
    return ""


def _parse_int(value: Any, default: int = 0) -> int:
    try:
        text = str(value or "").strip()
        if not text:
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _parse_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value or "").replace(",", "").strip()
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def _parse_boolish(value: Any, default: Optional[bool] = None) -> Optional[bool]:
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "pass", "ok"}:
        return True
    if text in {"0", "false", "no", "n", "fail"}:
        return False
    return default


def extract_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    # Prefer YYYY-MM-DD even when a full timestamp is supplied.
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if match:
        return match.group(1)
    # Support compact YYYYMMDD when needed.
    compact = re.search(r"(20\d{6})", text)
    if compact:
        raw = compact.group(1)
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    return text[:10] if len(text) >= 10 else text


def extract_row_date(row: Dict[str, str]) -> str:
    return extract_date(_first_value(row, DATE_FIELDS))


def expiry_week(value: Any) -> str:
    date_text = extract_date(value)
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", date_text or ""):
        return ""
    try:
        dt = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return ""
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _find_existing_master_ledger(workspace: Path) -> Optional[Path]:
    for name in MASTER_LEDGER_NAMES:
        candidate = workspace / name
        if candidate.exists():
            return candidate
    return None


def _read_actual_trade_rows(workspace: Path) -> Tuple[List[Dict[str, str]], str, List[str]]:
    warnings: List[str] = []
    master = _find_existing_master_ledger(workspace)
    if master is not None:
        master_rows = read_csv_rows(master)
        if master_rows:
            return master_rows, master.name, warnings
        warnings.append(f"MASTER_LEDGER_EMPTY:{master.name}")

    day_log_rows: List[Dict[str, str]] = []
    day_logs = sorted(workspace.glob(DAY_TRADE_LOG_PATTERN))
    for path in day_logs:
        rows = read_csv_rows(path)
        for row in rows:
            row.setdefault("source_file", path.name)
        day_log_rows.extend(rows)
    if day_log_rows:
        return day_log_rows, DAY_TRADE_LOG_PATTERN, warnings
    return [], "NONE", warnings


def _sum_trade_net(rows: Iterable[Dict[str, str]]) -> float:
    total = 0.0
    for row in rows:
        total += _parse_float(_first_value(row, NET_FIELDS), 0.0)
    return round(total, 4)


@dataclass(frozen=True)
class TrackerThresholds:
    valid_trade_day_target: int = DEFAULT_VALID_TRADE_DAY_TARGET
    minimum_trades_required: int = DEFAULT_MIN_TRADES_REQUIRED
    minimum_expiry_weeks_required: int = DEFAULT_MIN_EXPIRY_WEEKS_REQUIRED


def evaluate_workspace(
    workspace: Path,
    thresholds: TrackerThresholds = TrackerThresholds(),
    write: bool = False,
) -> Dict[str, Any]:
    workspace = Path(workspace)
    warnings: List[str] = []

    day_ledger_path = workspace / DAY_LEDGER_NAME
    day_rows = read_csv_rows(day_ledger_path)
    if not day_ledger_path.exists():
        warnings.append(f"DAY_LEDGER_MISSING:{day_ledger_path.name}")
    if not day_rows:
        warnings.append("DAY_LEDGER_EMPTY")

    observed_dates: Set[str] = set()
    day_ledger_positive_dates: Set[str] = set()
    no_trade_observed_dates: Set[str] = set()
    day_ledger_trade_count_total = 0
    unsafe_day_rows = 0

    for row in day_rows:
        date_text = extract_row_date(row)
        if date_text:
            observed_dates.add(date_text)

        trade_count = _parse_int(_first_value(row, TRADE_COUNT_FIELDS), 0)
        day_ledger_trade_count_total += max(0, trade_count)
        if trade_count > 0 and date_text:
            day_ledger_positive_dates.add(date_text)
        if trade_count <= 0 and date_text:
            no_trade_observed_dates.add(date_text)

        safety_ok = _parse_boolish(row.get("safety_ok", row.get("paper_only", "")), default=True)
        manual_override = _parse_boolish(row.get("manual_override", ""), default=False)
        candidate_tuning = _parse_boolish(row.get("candidate_tuning", ""), default=False)
        if safety_ok is False or manual_override is True or candidate_tuning is True:
            unsafe_day_rows += 1

    if unsafe_day_rows:
        warnings.append(f"UNSAFE_DAY_LEDGER_ROWS:{unsafe_day_rows}")

    actual_trade_rows, actual_trade_rows_source, trade_row_warnings = _read_actual_trade_rows(workspace)
    warnings.extend(trade_row_warnings)

    actual_trade_dates: Set[str] = set()
    trade_rows_missing_date = 0
    expiry_weeks: Set[str] = set()
    for row in actual_trade_rows:
        date_text = extract_row_date(row)
        if date_text:
            actual_trade_dates.add(date_text)
        else:
            trade_rows_missing_date += 1
        expiry_text = _first_value(row, EXPIRY_FIELDS)
        week = expiry_week(expiry_text)
        if week:
            expiry_weeks.add(week)

    if trade_rows_missing_date:
        warnings.append(f"TRADE_ROWS_MISSING_DATE:{trade_rows_missing_date}")

    missing_actual_for_positive_days = sorted(day_ledger_positive_dates - actual_trade_dates)
    actual_dates_not_in_day_ledger = sorted(actual_trade_dates - observed_dates)
    if missing_actual_for_positive_days:
        warnings.append("DAY_LEDGER_POSITIVE_WITHOUT_ACTUAL_TRADE_ROWS:" + ",".join(missing_actual_for_positive_days))
    if actual_dates_not_in_day_ledger:
        warnings.append("ACTUAL_TRADE_ROWS_WITHOUT_DAY_LEDGER:" + ",".join(actual_dates_not_in_day_ledger))

    # Strict no-fake rule: target progress is based on actual paper trade row dates.
    valid_trade_dates = actual_trade_dates
    valid_paper_trade_days = len(valid_trade_dates)
    observed_session_days = len(observed_dates)
    actual_paper_trades = len(actual_trade_rows)
    distinct_expiry_weeks = len(expiry_weeks)
    remaining_valid_trade_days = max(0, thresholds.valid_trade_day_target - valid_paper_trade_days)
    progress_percent = round((valid_paper_trade_days / thresholds.valid_trade_day_target) * 100, 2) if thresholds.valid_trade_day_target else 0.0

    if valid_paper_trade_days < thresholds.valid_trade_day_target:
        decision = "HOLD_MORE_VALID_TRADE_DAYS_REQUIRED"
    elif actual_paper_trades < thresholds.minimum_trades_required:
        decision = "HOLD_MORE_ACTUAL_PAPER_TRADES_REQUIRED"
    elif distinct_expiry_weeks < thresholds.minimum_expiry_weeks_required:
        decision = "HOLD_MORE_EXPIRY_WEEKS_REQUIRED"
    else:
        decision = "VALID_TRADE_DAY_SAMPLE_COMPLETE_MANUAL_REVIEW_REQUIRED"

    payload: Dict[str, Any] = {
        "tracker_status": "PASS",
        "tracker_version": VERSION,
        "workspace": str(workspace),
        "evaluated_at_utc": _now_utc(),
        "target_valid_trade_days": thresholds.valid_trade_day_target,
        "minimum_trades_required": thresholds.minimum_trades_required,
        "minimum_expiry_weeks_required": thresholds.minimum_expiry_weeks_required,
        "observed_session_days": observed_session_days,
        "valid_paper_trade_days": valid_paper_trade_days,
        "no_trade_observed_days": len(no_trade_observed_dates),
        "remaining_valid_trade_days": remaining_valid_trade_days,
        "valid_trade_day_progress_percent": progress_percent,
        "actual_paper_trades": actual_paper_trades,
        "actual_trade_rows_source": actual_trade_rows_source,
        "day_ledger_rows": len(day_rows),
        "day_ledger_trade_count_total": day_ledger_trade_count_total,
        "day_ledger_positive_trade_days": len(day_ledger_positive_dates),
        "distinct_expiry_weeks": distinct_expiry_weeks,
        "valid_trade_dates": sorted(valid_trade_dates),
        "observed_session_dates": sorted(observed_dates),
        "no_trade_observed_dates": sorted(no_trade_observed_dates),
        "expiry_weeks": sorted(expiry_weeks),
        "cumulative_forward_net": _sum_trade_net(actual_trade_rows),
        "decision": decision,
        "real_money_automatic": False,
        "manual_review_required_before_real_money": True,
        "paper_only_validation_continues": decision != "VALID_TRADE_DAY_SAMPLE_COMPLETE_MANUAL_REVIEW_REQUIRED",
        "external_api_calls_executed": EXTERNAL_API_CALLS_EXECUTED,
        "order_api_invoked": ORDER_API_INVOKED,
        "broker_execution_invoked": BROKER_EXECUTION_INVOKED,
        "fake_trades_created": FAKE_TRADES_CREATED,
        "candidate_tuning": CANDIDATE_TUNING,
        "safety_lock": SAFETY_LOCK.copy(),
        "warnings": warnings,
    }

    if write:
        write_outputs(workspace, payload)

    return payload


def write_outputs(workspace: Path, payload: Dict[str, Any]) -> Dict[str, str]:
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    json_path = workspace / "FORWARD_VALIDATION_30_VALID_TRADE_DAY_TRACKER.json"
    md_path = workspace / "FORWARD_VALIDATION_30_VALID_TRADE_DAY_TRACKER.md"
    ledger_path = workspace / "FORWARD_VALIDATION_30_VALID_TRADE_DAY_TRACKER_LEDGER.csv"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    md_lines = [
        "# HQE 30 Valid Trade-Day Validation Tracker",
        "",
        f"- tracker_status: {payload['tracker_status']}",
        f"- decision: {payload['decision']}",
        f"- observed_session_days: {payload['observed_session_days']}",
        f"- valid_paper_trade_days: {payload['valid_paper_trade_days']} / {payload['target_valid_trade_days']}",
        f"- remaining_valid_trade_days: {payload['remaining_valid_trade_days']}",
        f"- no_trade_observed_days: {payload['no_trade_observed_days']}",
        f"- actual_paper_trades: {payload['actual_paper_trades']}",
        f"- distinct_expiry_weeks: {payload['distinct_expiry_weeks']} / {payload['minimum_expiry_weeks_required']}",
        f"- cumulative_forward_net: {payload['cumulative_forward_net']}",
        "- real_money_automatic: false",
        "- manual_review_required_before_real_money: true",
        "- safety: paper-only, local-only/data-only, no broker execution, no real orders, no auto trading, no option selling, no fake trades, no candidate tuning, no profitability claim.",
        "",
        "## Rule",
        "Observed no-trade days are recorded as evidence, but they do not count toward the 30 valid paper trade-day target.",
    ]
    if payload.get("warnings"):
        md_lines.extend(["", "## Warnings"])
        for warning in payload["warnings"]:
            md_lines.append(f"- {warning}")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    row = {
        "evaluated_at_utc": payload["evaluated_at_utc"],
        "tracker_status": payload["tracker_status"],
        "decision": payload["decision"],
        "observed_session_days": payload["observed_session_days"],
        "valid_paper_trade_days": payload["valid_paper_trade_days"],
        "target_valid_trade_days": payload["target_valid_trade_days"],
        "remaining_valid_trade_days": payload["remaining_valid_trade_days"],
        "no_trade_observed_days": payload["no_trade_observed_days"],
        "actual_paper_trades": payload["actual_paper_trades"],
        "distinct_expiry_weeks": payload["distinct_expiry_weeks"],
        "cumulative_forward_net": payload["cumulative_forward_net"],
        "real_money_automatic": "NO",
        "manual_review_required_before_real_money": "YES",
    }
    ledger_exists = ledger_path.exists()
    with ledger_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        if not ledger_exists:
            writer.writeheader()
        writer.writerow(row)

    return {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}


def guard_check() -> Dict[str, Any]:
    return {
        "guard_check_status": "PASS",
        "version": VERSION,
        "external_api_calls_executed": EXTERNAL_API_CALLS_EXECUTED,
        "order_api_invoked": ORDER_API_INVOKED,
        "broker_execution_invoked": BROKER_EXECUTION_INVOKED,
        "fake_trades_created": FAKE_TRADES_CREATED,
        "candidate_tuning": CANDIDATE_TUNING,
        "real_money_automatic": False,
        "safety_lock": SAFETY_LOCK.copy(),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HQE 30 valid trade-day validation tracker")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Forward validation workspace folder")
    parser.add_argument("--target-valid-days", type=int, default=DEFAULT_VALID_TRADE_DAY_TARGET)
    parser.add_argument("--minimum-trades", type=int, default=DEFAULT_MIN_TRADES_REQUIRED)
    parser.add_argument("--minimum-expiry-weeks", type=int, default=DEFAULT_MIN_EXPIRY_WEEKS_REQUIRED)
    parser.add_argument("--write", action="store_true", help="Write JSON/MD/CSV evidence files")
    parser.add_argument("--guard-check", action="store_true", help="Print safety guard status only")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.guard_check:
        print(json.dumps(guard_check(), indent=2, sort_keys=True))
        return 0

    thresholds = TrackerThresholds(
        valid_trade_day_target=args.target_valid_days,
        minimum_trades_required=args.minimum_trades,
        minimum_expiry_weeks_required=args.minimum_expiry_weeks,
    )
    payload = evaluate_workspace(Path(args.workspace), thresholds=thresholds, write=args.write)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("tracker_status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
