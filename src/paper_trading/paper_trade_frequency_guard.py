"""
Paper Trade Frequency Guard

Creates a guarded paper backtest ledger from the baseline recorded-data paper
ledger.

Purpose:
- prevent one trade on every candle
- enforce one-position-at-a-time behavior
- enforce cooldown after exit
- skip duplicate same-direction trades until direction changes
- apply max trades per day

This is paper/simulation only. It does not connect to brokers, request live
market data, place real orders, use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_LEDGER_PATH = Path(
    "reports/paper_trading/recorded_data_backtest_trade_ledger/backtest_trade_ledger.json"
)
DEFAULT_OUTPUT_DIR = Path("reports/paper_trading/paper_trade_frequency_guard")

SAFE_BROKER_MODE = "broker_disabled"
SAFE_ORDER_MODE = "orders_not_created"
SAFE_MONEY_MODE = "real_money_not_used"


@dataclass(frozen=True)
class GuardIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class GuardSummary:
    generated_at_utc: str
    status: str
    accepted_for_future_paper_comparison: bool
    output_directory: str
    safety_notice: str
    no_profitability_claim_notice: str
    baseline_ledger_path: str
    baseline_trade_count: int
    guarded_trade_count: int
    skipped_trade_count: int
    reduction_percent: float
    cooldown_bars_after_exit: int
    bar_minutes: int
    max_trades_per_day: int
    require_direction_change: bool
    starting_equity_reference: float
    guarded_final_equity_reference: float
    guarded_simulated_gross_result_total: float
    guarded_win_count: int
    guarded_loss_count: int
    guarded_flat_count: int
    guarded_win_rate_percent: float
    guarded_max_drawdown_reference: float
    guarded_max_drawdown_percent_reference: float
    long_ce_buy_count: int
    short_pe_buy_count: int
    invalid_mapping_count: int
    unsafe_broker_rows: int
    unsafe_order_rows: int
    unsafe_money_rows: int
    skip_reason_counts: dict[str, int]
    issues: list[GuardIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation frequency guard only. This guard filters existing "
        "recorded-data paper ledger rows to reduce overtrading. It does not "
        "connect to brokers, request live market data, place real orders, use "
        "real money, approve live trading, or prove profitability."
    )


def no_profitability_claim_notice() -> str:
    return (
        "This is not a profitability claim. Guarded results are paper/simulation "
        "reference values only and are intended for controlled comparison."
    )


def _issue(severity: str, code: str, count: int, message: str) -> GuardIssue:
    return GuardIssue(severity=severity, code=code, count=count, message=message)


def _status_from_issues(issues: Sequence[GuardIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _load_json(path: Path) -> tuple[Mapping[str, Any] | None, list[GuardIssue]]:
    if not path.exists():
        return None, [_issue("fail", "ledger_missing", 1, f"Ledger JSON missing: {path}")]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [_issue("fail", "ledger_invalid_json", 1, f"Ledger JSON invalid: {exc}")]

    if not isinstance(payload, Mapping):
        return None, [_issue("fail", "ledger_invalid_shape", 1, "Ledger JSON is not an object.")]

    return payload, []


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return 0
    return 0


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return 0.0
    return 0.0


def _parse_time(value: Any) -> datetime | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            if parsed.tzinfo is not None:
                parsed = parsed.replace(tzinfo=None)
            return parsed
        except ValueError:
            pass

    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def _rows(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []

    raw_rows = payload.get("ledger_rows")
    if not isinstance(raw_rows, list):
        return []

    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        if isinstance(row, Mapping):
            rows.append(dict(row))

    return rows


def _safe_row(row: Mapping[str, Any]) -> bool:
    return (
        str(row.get("broker_execution_mode") or "") == SAFE_BROKER_MODE
        and str(row.get("order_mode") or "") == SAFE_ORDER_MODE
        and str(row.get("money_mode") or "") == SAFE_MONEY_MODE
    )


def _valid_mapping(row: Mapping[str, Any]) -> bool:
    decision = str(row.get("decision") or "")
    option_type = str(row.get("option_type") or "")
    action = str(row.get("option_action") or "")

    if decision == "LONG":
        return option_type == "CE" and action == "BUY"
    if decision == "SHORT":
        return option_type == "PE" and action == "BUY"
    return False


def _day_key(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")


def _increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _max_drawdown(equity_curve: Sequence[float]) -> tuple[float, float]:
    if not equity_curve:
        return 0.0, 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        dd = peak - value
        if dd > max_dd:
            max_dd = dd

    pct = 0.0 if peak <= 0 else (max_dd / peak) * 100.0
    return max_dd, pct


def apply_frequency_guard(
    rows: Sequence[Mapping[str, Any]],
    *,
    cooldown_bars_after_exit: int = 3,
    bar_minutes: int = 5,
    max_trades_per_day: int = 6,
    require_direction_change: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    accepted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    skip_reason_counts: dict[str, int] = {}

    next_allowed_entry: datetime | None = None
    day_trade_counts: dict[str, int] = {}
    last_accepted_direction: str | None = None

    cooldown_minutes = max(cooldown_bars_after_exit, 0) * max(bar_minutes, 1)

    ordered_rows = sorted(
        [dict(row) for row in rows],
        key=lambda row: _as_int(row.get("ledger_row_index")),
    )

    for row in ordered_rows:
        reason = ""

        entry_time = _parse_time(row.get("entry_timestamp"))
        exit_time = _parse_time(row.get("exit_timestamp"))
        decision = str(row.get("decision") or "")

        if entry_time is None or exit_time is None:
            reason = "invalid_timestamp"
        elif not _safe_row(row):
            reason = "unsafe_execution_fields"
        elif not _valid_mapping(row):
            reason = "invalid_direction_mapping"
        elif next_allowed_entry is not None and entry_time < next_allowed_entry:
            reason = "cooldown_or_position_open"
        elif require_direction_change and last_accepted_direction == decision:
            reason = "duplicate_same_direction"
        else:
            day = _day_key(entry_time)
            current_day_count = day_trade_counts.get(day, 0)
            if current_day_count >= max_trades_per_day:
                reason = "daily_trade_cap_reached"

        if reason:
            skipped_row = dict(row)
            skipped_row["frequency_guard_skip_reason"] = reason
            skipped.append(skipped_row)
            _increment(skip_reason_counts, reason)
            continue

        guarded_row = dict(row)
        guarded_row["frequency_guard_status"] = "accepted"
        guarded_row["frequency_guard_cooldown_bars_after_exit"] = cooldown_bars_after_exit
        guarded_row["frequency_guard_max_trades_per_day"] = max_trades_per_day
        guarded_row["frequency_guard_require_direction_change"] = require_direction_change
        guarded_row["guarded_trade_index"] = len(accepted) + 1
        accepted.append(guarded_row)

        day_trade_counts[_day_key(entry_time)] = day_trade_counts.get(_day_key(entry_time), 0) + 1
        next_allowed_entry = exit_time + timedelta(minutes=cooldown_minutes)
        last_accepted_direction = decision

    return accepted, skipped, skip_reason_counts


def build_guard_summary(
    *,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    cooldown_bars_after_exit: int = 3,
    bar_minutes: int = 5,
    max_trades_per_day: int = 6,
    require_direction_change: bool = True,
    starting_equity_reference: float = 100000.0,
) -> tuple[GuardSummary, list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[GuardIssue] = []

    ledger, load_issues = _load_json(ledger_path)
    issues.extend(load_issues)

    if ledger is not None and str(ledger.get("status") or "").lower() != "pass":
        issues.append(
            _issue(
                "fail",
                "baseline_ledger_not_pass",
                1,
                f"Baseline ledger status is not pass: {ledger.get('status')}",
            )
        )

    rows = _rows(ledger)

    if not rows:
        issues.append(_issue("fail", "baseline_rows_missing", 1, "Baseline ledger rows missing."))

    accepted, skipped, skip_reason_counts = apply_frequency_guard(
        rows,
        cooldown_bars_after_exit=cooldown_bars_after_exit,
        bar_minutes=bar_minutes,
        max_trades_per_day=max_trades_per_day,
        require_direction_change=require_direction_change,
    )

    if not accepted:
        issues.append(_issue("fail", "no_guarded_trades", 1, "Frequency guard accepted zero trades."))

    baseline_count = len(rows)
    guarded_count = len(accepted)
    skipped_count = len(skipped)
    reduction_percent = 0.0 if baseline_count == 0 else round((skipped_count / baseline_count) * 100.0, 10)

    unsafe_broker = sum(1 for row in accepted if str(row.get("broker_execution_mode") or "") != SAFE_BROKER_MODE)
    unsafe_order = sum(1 for row in accepted if str(row.get("order_mode") or "") != SAFE_ORDER_MODE)
    unsafe_money = sum(1 for row in accepted if str(row.get("money_mode") or "") != SAFE_MONEY_MODE)
    invalid_mapping = sum(1 for row in accepted if not _valid_mapping(row))

    if unsafe_broker:
        issues.append(_issue("fail", "unsafe_broker_rows", unsafe_broker, "Guarded rows contain unsafe broker mode."))
    if unsafe_order:
        issues.append(_issue("fail", "unsafe_order_rows", unsafe_order, "Guarded rows contain unsafe order mode."))
    if unsafe_money:
        issues.append(_issue("fail", "unsafe_money_rows", unsafe_money, "Guarded rows contain unsafe money mode."))
    if invalid_mapping:
        issues.append(_issue("fail", "invalid_mapping_rows", invalid_mapping, "Guarded rows violate LONG->CE BUY or SHORT->PE BUY."))

    results = [_as_float(row.get("simulated_gross_result")) for row in accepted]
    total = sum(results)
    final_equity = starting_equity_reference + total

    equity = starting_equity_reference
    equity_curve = [equity]
    for value in results:
        equity += value
        equity_curve.append(equity)

    max_dd, max_dd_pct = _max_drawdown(equity_curve)

    win_count = sum(1 for value in results if value > 0)
    loss_count = sum(1 for value in results if value < 0)
    flat_count = sum(1 for value in results if value == 0)
    win_rate = 0.0 if guarded_count == 0 else round((win_count / guarded_count) * 100.0, 10)

    long_ce = sum(
        1
        for row in accepted
        if str(row.get("decision") or "") == "LONG"
        and str(row.get("option_type") or "") == "CE"
        and str(row.get("option_action") or "") == "BUY"
    )
    short_pe = sum(
        1
        for row in accepted
        if str(row.get("decision") or "") == "SHORT"
        and str(row.get("option_type") or "") == "PE"
        and str(row.get("option_action") or "") == "BUY"
    )

    status = _status_from_issues(issues)

    summary = GuardSummary(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        accepted_for_future_paper_comparison=status in {"pass", "warn"},
        output_directory=str(output_dir),
        safety_notice=safety_notice(),
        no_profitability_claim_notice=no_profitability_claim_notice(),
        baseline_ledger_path=str(ledger_path),
        baseline_trade_count=baseline_count,
        guarded_trade_count=guarded_count,
        skipped_trade_count=skipped_count,
        reduction_percent=reduction_percent,
        cooldown_bars_after_exit=cooldown_bars_after_exit,
        bar_minutes=bar_minutes,
        max_trades_per_day=max_trades_per_day,
        require_direction_change=require_direction_change,
        starting_equity_reference=starting_equity_reference,
        guarded_final_equity_reference=final_equity,
        guarded_simulated_gross_result_total=total,
        guarded_win_count=win_count,
        guarded_loss_count=loss_count,
        guarded_flat_count=flat_count,
        guarded_win_rate_percent=win_rate,
        guarded_max_drawdown_reference=max_dd,
        guarded_max_drawdown_percent_reference=max_dd_pct,
        long_ce_buy_count=long_ce,
        short_pe_buy_count=short_pe,
        invalid_mapping_count=invalid_mapping,
        unsafe_broker_rows=unsafe_broker,
        unsafe_order_rows=unsafe_order,
        unsafe_money_rows=unsafe_money,
        skip_reason_counts=skip_reason_counts,
        issues=issues,
    )

    return summary, accepted, skipped


def _summary_to_dict(summary: GuardSummary) -> dict[str, Any]:
    data = asdict(summary)
    data["issues"] = [asdict(issue) for issue in summary.issues]
    return data


def write_guard_outputs(
    summary: GuardSummary,
    accepted: Sequence[Mapping[str, Any]],
    skipped: Sequence[Mapping[str, Any]],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_json = output_dir / "paper_trade_frequency_guard.json"
    summary_txt = output_dir / "paper_trade_frequency_guard.txt"
    guarded_ledger_json = output_dir / "guarded_trade_ledger.json"
    guarded_rows_csv = output_dir / "guarded_trade_rows.csv"
    skipped_rows_csv = output_dir / "skipped_trade_rows.csv"
    manifest_json = output_dir / "manifest.json"

    summary_json.write_text(
        json.dumps(_summary_to_dict(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    guarded_payload = {
        "generated_at_utc": summary.generated_at_utc,
        "status": summary.status,
        "safety_notice": summary.safety_notice,
        "no_profitability_claim_notice": summary.no_profitability_claim_notice,
        "baseline_trade_count": summary.baseline_trade_count,
        "guarded_trade_count": summary.guarded_trade_count,
        "skipped_trade_count": summary.skipped_trade_count,
        "reduction_percent": summary.reduction_percent,
        "guarded_simulated_gross_result_total": summary.guarded_simulated_gross_result_total,
        "guarded_win_rate_percent": summary.guarded_win_rate_percent,
        "guarded_rows": list(accepted),
    }

    guarded_ledger_json.write_text(
        json.dumps(guarded_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Paper Trade Frequency Guard",
        "",
        summary.safety_notice,
        "",
        summary.no_profitability_claim_notice,
        "",
        f"Generated at UTC: {summary.generated_at_utc}",
        f"Status: {summary.status}",
        f"Accepted for future paper comparison: {summary.accepted_for_future_paper_comparison}",
        "",
        "Trade Frequency Fix:",
        f"- Baseline trades: {summary.baseline_trade_count}",
        f"- Guarded trades: {summary.guarded_trade_count}",
        f"- Skipped trades: {summary.skipped_trade_count}",
        f"- Reduction percent: {summary.reduction_percent}",
        f"- Cooldown bars after exit: {summary.cooldown_bars_after_exit}",
        f"- Max trades per day: {summary.max_trades_per_day}",
        f"- Require direction change: {summary.require_direction_change}",
        "",
        "Guarded Paper Result Reference:",
        f"- Guarded simulated total: {summary.guarded_simulated_gross_result_total}",
        f"- Guarded final equity reference: {summary.guarded_final_equity_reference}",
        f"- Guarded win count: {summary.guarded_win_count}",
        f"- Guarded loss count: {summary.guarded_loss_count}",
        f"- Guarded flat count: {summary.guarded_flat_count}",
        f"- Guarded win rate percent: {summary.guarded_win_rate_percent}",
        f"- Guarded max drawdown percent: {summary.guarded_max_drawdown_percent_reference}",
        "",
        "Safety:",
        f"- Unsafe broker rows: {summary.unsafe_broker_rows}",
        f"- Unsafe order rows: {summary.unsafe_order_rows}",
        f"- Unsafe money rows: {summary.unsafe_money_rows}",
        f"- Invalid mapping rows: {summary.invalid_mapping_count}",
        "",
        "Skip Reasons:",
    ]

    if summary.skip_reason_counts:
        for reason, count in sorted(summary.skip_reason_counts.items()):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("Issues:")
    if summary.issues:
        for issue in summary.issues:
            lines.append(f"- {issue.severity.upper()} {issue.code} ({issue.count}): {issue.message}")
    else:
        lines.append("- PASS: Frequency guard completed.")

    lines.extend(
        [
            "",
            "This is not a profitability claim.",
        ]
    )

    summary_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if accepted:
        fieldnames = sorted({key for row in accepted for key in row.keys()})
        with guarded_rows_csv.open("w", encoding="utf-8", newline="") as file_handle:
            writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in accepted:
                writer.writerow(dict(row))
    else:
        guarded_rows_csv.write_text("", encoding="utf-8")

    if skipped:
        fieldnames = sorted({key for row in skipped for key in row.keys()})
        with skipped_rows_csv.open("w", encoding="utf-8", newline="") as file_handle:
            writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in skipped:
                writer.writerow(dict(row))
    else:
        skipped_rows_csv.write_text("", encoding="utf-8")

    manifest = {
        "report_type": "paper_trade_frequency_guard",
        "generated_at_utc": summary.generated_at_utc,
        "status": summary.status,
        "baseline_trade_count": summary.baseline_trade_count,
        "guarded_trade_count": summary.guarded_trade_count,
        "skipped_trade_count": summary.skipped_trade_count,
        "safety_notice": summary.safety_notice,
        "outputs": {
            "summary_json": str(summary_json),
            "summary_txt": str(summary_txt),
            "guarded_ledger_json": str(guarded_ledger_json),
            "guarded_rows_csv": str(guarded_rows_csv),
            "skipped_rows_csv": str(skipped_rows_csv),
            "manifest_json": str(manifest_json),
        },
    }

    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "summary_json": summary_json,
        "summary_txt": summary_txt,
        "guarded_ledger_json": guarded_ledger_json,
        "guarded_rows_csv": guarded_rows_csv,
        "skipped_rows_csv": skipped_rows_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_guard(
    *,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    cooldown_bars_after_exit: int = 3,
    bar_minutes: int = 5,
    max_trades_per_day: int = 6,
    require_direction_change: bool = True,
    starting_equity_reference: float = 100000.0,
) -> tuple[GuardSummary, dict[str, Path]]:
    summary, accepted, skipped = build_guard_summary(
        ledger_path=ledger_path,
        output_dir=output_dir,
        cooldown_bars_after_exit=cooldown_bars_after_exit,
        bar_minutes=bar_minutes,
        max_trades_per_day=max_trades_per_day,
        require_direction_change=require_direction_change,
        starting_equity_reference=starting_equity_reference,
    )
    outputs = write_guard_outputs(summary, accepted, skipped, output_dir)
    return summary, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply paper trade frequency guard.")
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--cooldown-bars-after-exit", type=int, default=3)
    parser.add_argument("--bar-minutes", type=int, default=5)
    parser.add_argument("--max-trades-per-day", type=int, default=6)
    parser.add_argument(
        "--allow-same-direction",
        action="store_true",
        help="Disable duplicate same-direction filter.",
    )
    parser.add_argument("--starting-equity-reference", type=float, default=100000.0)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    summary, outputs = build_and_write_guard(
        ledger_path=Path(args.ledger),
        output_dir=Path(args.output_dir),
        cooldown_bars_after_exit=args.cooldown_bars_after_exit,
        bar_minutes=args.bar_minutes,
        max_trades_per_day=args.max_trades_per_day,
        require_direction_change=not args.allow_same_direction,
        starting_equity_reference=args.starting_equity_reference,
    )

    print("HQE paper trade frequency guard completed.")
    print(summary.safety_notice)
    print(summary.no_profitability_claim_notice)
    print(f"Status: {summary.status}")
    print(f"Baseline trades: {summary.baseline_trade_count}")
    print(f"Guarded trades: {summary.guarded_trade_count}")
    print(f"Skipped trades: {summary.skipped_trade_count}")
    print(f"Reduction percent: {summary.reduction_percent}")
    print(f"Guarded simulated total reference: {summary.guarded_simulated_gross_result_total}")
    print(f"Guarded win rate reference: {summary.guarded_win_rate_percent}")
    print(f"Guard report: {outputs['summary_txt']}")
    print("This is not a profitability claim.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
