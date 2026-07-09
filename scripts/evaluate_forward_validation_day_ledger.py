from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SAFETY_LOCK = {
    "paper_only": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api": True,
    "no_profitability_claim": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
}

DEFAULT_MIN_TRADES = 30
DEFAULT_MIN_VALID_TRADE_DAYS = 30
DEFAULT_MIN_EXPIRY_WEEKS = 4

DAY_LEDGER_NAME = "FORWARD_VALIDATION_DAY_LEDGER.csv"
MASTER_LEDGER_NAME = "FORWARD_VALIDATION_MASTER_LEDGER.csv"
JSON_OUT_NAME = "FORWARD_VALIDATION_DAY_LEDGER_EVALUATION.json"
MD_OUT_NAME = "FORWARD_VALIDATION_DAY_LEDGER_EVALUATION.md"


def _normalize_key(value: str) -> str:
    return str(value or "").replace("\ufeff", "").strip().lower()


def _normalize_row(row: dict[str, Any]) -> dict[str, str]:
    return {_normalize_key(k): str(v or "").strip() for k, v in row.items()}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [_normalize_row(row) for row in reader]


def first_value(row: dict[str, str], names: Iterable[str], default: str = "") -> str:
    for name in names:
        key = _normalize_key(name)
        if key in row and str(row[key]).strip() != "":
            return str(row[key]).strip()
    return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        text = str(value or "").strip()
        if text == "":
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value or "").strip().replace(",", "")
        if text == "":
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def yes_no_true(value: Any) -> bool:
    return str(value or "").strip().upper() in {"YES", "Y", "TRUE", "1", "OK", "PASS"}


def no_false(value: Any) -> bool:
    return str(value or "").strip().upper() in {"NO", "N", "FALSE", "0", ""}


def parse_date_token(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    # Common ISO date/datetime formats used by HQE evidence files.
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:19], fmt).date().isoformat()
        except ValueError:
            continue
    # Safe fallback: keep first ISO-like token if present.
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        return text[:10]
    return text


def expiry_week(value: str) -> str:
    day = parse_date_token(value)
    if not day or len(day) < 10:
        return ""
    try:
        d = datetime.strptime(day[:10], "%Y-%m-%d").date()
        year, week, _ = d.isocalendar()
        return f"{year}-W{week:02d}"
    except ValueError:
        return ""


def discover_day_trade_logs(workspace: Path) -> list[Path]:
    patterns = (
        "DAY_*_FORWARD_TRADE_LOG.csv",
        "DAY_*_PAPER_TRADE_LOG.csv",
        "DAY_*_TRADE_LOG.csv",
    )
    found: list[Path] = []
    for pattern in patterns:
        found.extend(sorted(workspace.glob(pattern)))
    # De-duplicate while preserving order.
    unique: list[Path] = []
    seen: set[Path] = set()
    for p in found:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def load_actual_trade_rows(workspace: Path) -> tuple[list[dict[str, str]], str]:
    master_path = workspace / MASTER_LEDGER_NAME
    master_rows = read_csv_rows(master_path)
    if master_rows:
        return master_rows, MASTER_LEDGER_NAME

    day_rows: list[dict[str, str]] = []
    sources: list[str] = []
    for path in discover_day_trade_logs(workspace):
        rows = read_csv_rows(path)
        if rows:
            day_rows.extend(rows)
            sources.append(path.name)
    if day_rows:
        return day_rows, ",".join(sources)
    return [], "NONE"


def trade_net_value(row: dict[str, str]) -> float:
    return to_float(
        first_value(
            row,
            (
                "net",
                "net_pnl",
                "net_profit",
                "net_reward",
                "estimated_net_reward",
                "actual_net",
                "pnl",
            ),
            "0",
        )
    )


@dataclass(frozen=True)
class DayLedgerEvaluation:
    evaluator_version: str
    workspace: str
    evaluation_status: str
    decision: str
    observed_session_days: int
    valid_paper_trade_days: int
    actual_paper_trades: int
    distinct_expiry_weeks: int
    cumulative_forward_net: float
    minimum_trades_required: int
    minimum_valid_trade_days_required: int
    minimum_expiry_weeks_required: int
    day_ledger_rows: int
    actual_trade_rows_source: str
    safety_lock: dict[str, bool]
    warnings: list[str]


def evaluate_workspace(
    workspace: str | Path,
    *,
    min_trades: int = DEFAULT_MIN_TRADES,
    min_valid_trade_days: int = DEFAULT_MIN_VALID_TRADE_DAYS,
    min_expiry_weeks: int = DEFAULT_MIN_EXPIRY_WEEKS,
) -> DayLedgerEvaluation:
    workspace_path = Path(workspace).expanduser().resolve()
    warnings: list[str] = []

    day_rows = read_csv_rows(workspace_path / DAY_LEDGER_NAME)
    if not day_rows:
        warnings.append(f"Missing or empty {DAY_LEDGER_NAME}")

    observed_dates: set[str] = set()
    valid_trade_dates: set[str] = set()
    ledger_trade_count_sum = 0

    for row in day_rows:
        trading_date = parse_date_token(
            first_value(row, ("trading_date", "date", "session_date", "day_date"))
        )
        if trading_date:
            observed_dates.add(trading_date)

        trade_count = to_int(first_value(row, ("trade_count", "paper_trade_count", "trades"), "0"))
        ledger_trade_count_sum += max(0, trade_count)
        if trading_date and trade_count > 0:
            valid_trade_dates.add(trading_date)

        safety_value = first_value(row, ("safety_ok", "safety", "paper_safety_ok"), "YES")
        if not yes_no_true(safety_value):
            warnings.append(f"Safety flag not OK for {trading_date or 'unknown-date'}")

        candidate_tuning = first_value(row, ("candidate_tuning", "candidate_tuned", "tuning"), "NO")
        if not no_false(candidate_tuning):
            warnings.append(f"Candidate tuning flag present for {trading_date or 'unknown-date'}")

        manual_override = first_value(row, ("manual_override", "override"), "NO")
        if not no_false(manual_override):
            warnings.append(f"Manual override flag present for {trading_date or 'unknown-date'}")

    actual_trade_rows, trade_source = load_actual_trade_rows(workspace_path)
    actual_paper_trades = len(actual_trade_rows)
    if ledger_trade_count_sum and actual_paper_trades < ledger_trade_count_sum:
        warnings.append(
            "Day ledger trade_count is greater than actual loaded trade rows; "
            "actual_paper_trades still uses only real master/day trade rows."
        )

    expiry_weeks: set[str] = set()
    for row in actual_trade_rows:
        expiry_value = first_value(
            row,
            ("expiry", "expiry_date", "option_expiry", "contract_expiry", "instrument_expiry"),
        )
        week = expiry_week(expiry_value)
        if week:
            expiry_weeks.add(week)

    cumulative_forward_net = round(sum(trade_net_value(row) for row in actual_trade_rows), 2)

    min_sample_ok = (
        actual_paper_trades >= min_trades
        and len(valid_trade_dates) >= min_valid_trade_days
        and len(expiry_weeks) >= min_expiry_weeks
    )
    if min_sample_ok:
        decision = "MINIMUM_FORWARD_SAMPLE_READY_FOR_MANUAL_REVIEW_ONLY"
    else:
        decision = "HOLD_MORE_DATA_REQUIRED"

    return DayLedgerEvaluation(
        evaluator_version="MODULE_146_DAY_LEDGER_INTEGRATION_V1",
        workspace=str(workspace_path),
        evaluation_status="PASS" if workspace_path.exists() else "WORKSPACE_NOT_FOUND",
        decision=decision,
        observed_session_days=len(observed_dates),
        valid_paper_trade_days=len(valid_trade_dates),
        actual_paper_trades=actual_paper_trades,
        distinct_expiry_weeks=len(expiry_weeks),
        cumulative_forward_net=cumulative_forward_net,
        minimum_trades_required=min_trades,
        minimum_valid_trade_days_required=min_valid_trade_days,
        minimum_expiry_weeks_required=min_expiry_weeks,
        day_ledger_rows=len(day_rows),
        actual_trade_rows_source=trade_source,
        safety_lock=dict(SAFETY_LOCK),
        warnings=warnings,
    )


def render_markdown(result: DayLedgerEvaluation) -> str:
    data = asdict(result)
    warnings = data["warnings"] or ["None"]
    safety_lines = [f"- {key}: {value}" for key, value in data["safety_lock"].items()]
    warning_lines = [f"- {warning}" for warning in warnings]
    return "\n".join(
        [
            "# Forward Validation Day-Ledger Evaluation",
            "",
            f"- evaluator_version: {result.evaluator_version}",
            f"- evaluation_status: {result.evaluation_status}",
            f"- decision: {result.decision}",
            f"- workspace: {result.workspace}",
            "",
            "## Counters",
            "",
            f"- observed_session_days: {result.observed_session_days}",
            f"- valid_paper_trade_days: {result.valid_paper_trade_days}",
            f"- actual_paper_trades: {result.actual_paper_trades}",
            f"- distinct_expiry_weeks: {result.distinct_expiry_weeks}",
            f"- cumulative_forward_net: {result.cumulative_forward_net}",
            "",
            "## Minimum Requirements",
            "",
            f"- minimum_trades_required: {result.minimum_trades_required}",
            f"- minimum_valid_trade_days_required: {result.minimum_valid_trade_days_required}",
            f"- minimum_expiry_weeks_required: {result.minimum_expiry_weeks_required}",
            "",
            "## Safety Lock",
            "",
            *safety_lines,
            "",
            "## Warnings",
            "",
            *warning_lines,
            "",
            "Note: This is not a profitability claim. Real money remains blocked unless a future separate manual review and explicit approval happens.",
            "",
        ]
    )


def write_outputs(workspace: str | Path, result: DayLedgerEvaluation) -> tuple[Path, Path]:
    workspace_path = Path(workspace).expanduser().resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    json_path = workspace_path / JSON_OUT_NAME
    md_path = workspace_path / MD_OUT_NAME
    json_path.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE forward validation day-ledger evaluator integration")
    parser.add_argument("--workspace", required=True, help="Forward validation active workspace folder")
    parser.add_argument("--min-trades", type=int, default=DEFAULT_MIN_TRADES)
    parser.add_argument("--min-valid-trade-days", type=int, default=DEFAULT_MIN_VALID_TRADE_DAYS)
    parser.add_argument("--min-expiry-weeks", type=int, default=DEFAULT_MIN_EXPIRY_WEEKS)
    parser.add_argument("--write", action="store_true", help="Write JSON and Markdown evaluation files")
    args = parser.parse_args()

    result = evaluate_workspace(
        args.workspace,
        min_trades=args.min_trades,
        min_valid_trade_days=args.min_valid_trade_days,
        min_expiry_weeks=args.min_expiry_weeks,
    )
    if args.write:
        write_outputs(args.workspace, result)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0 if result.evaluation_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

