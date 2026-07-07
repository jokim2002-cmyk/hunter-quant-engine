"""
Recorded data backtest trade ledger.

Module ZZ in the fast-track v1.0 Testing Edition path.

This module converts paper fill/exit lifecycle references into paper-only
backtest ledger rows.

It calculates simulated paper reference amounts from:
option_points_result * quantity_lots * lot_size

This module does not connect to brokers, request live market data, place real
orders, use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPECTED_LIFECYCLE_MODES = {
    "event_type": "paper_option_fill_exit_lifecycle_created",
    "option_action": "BUY",
    "lifecycle_mode": "paper_fill_exit_lifecycle_only",
    "fill_mode": "paper_fills_simulated_from_recorded_replay_references",
    "broker_execution_mode": "broker_disabled",
    "order_mode": "orders_not_created",
    "account_pnl_mode": "account_pnl_not_calculated",
    "output_mode": "paper_fill_exit_manifest_only",
}

FORBIDDEN_KEYS = {
    "broker",
    "broker_order_id",
    "exchange_order_id",
    "live_order",
    "order",
    "order_id",
    "orders",
    "real_money",
}


@dataclass(frozen=True)
class BacktestTradeLedgerIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class BacktestTradeLedgerRow:
    ledger_row_index: int
    event_type: str
    trade_id: str
    source_paper_fill_exit_id: str
    source_paper_trade_plan_id: str
    source_decision_event_index: int | None
    underlying_symbol: str
    decision: str
    option_type: str
    option_action: str
    entry_timestamp: str
    exit_timestamp: str
    entry_option_price_reference: float
    exit_option_price_reference: float
    option_points_result: float
    quantity_lots: int
    lot_size: int
    simulated_gross_result: float
    outcome: str
    exit_reason: str
    holding_bars: int
    ledger_mode: str
    result_mode: str
    broker_execution_mode: str
    order_mode: str
    money_mode: str
    output_mode: str


@dataclass(frozen=True)
class BacktestTradeLedgerReport:
    generated_at_utc: str
    fill_exit_report_path: str
    output_directory: str
    status: str
    ready_for_future_backtest_metrics_engine: bool
    min_trades_required: int
    paper_fill_exit_lifecycle_count: int
    ledger_trade_count: int
    ce_trade_count: int
    pe_trade_count: int
    winning_trade_count: int
    losing_trade_count: int
    flat_trade_count: int
    gross_option_points_result: float
    simulated_gross_result_total: float
    safety_notice: str
    issues: list[BacktestTradeLedgerIssue]
    ledger_rows: list[BacktestTradeLedgerRow]


def safety_notice() -> str:
    return (
        "Paper/simulation backtest trade ledger only. Results are simulated "
        "paper reference amounts derived from recorded replay lifecycle data. "
        "This module does not connect to brokers, request live market data, "
        "place real orders, use real money, or prove profitability."
    )


def _issue(severity: str, code: str, count: int, message: str) -> BacktestTradeLedgerIssue:
    return BacktestTradeLedgerIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[BacktestTradeLedgerIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _load_json_object(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[BacktestTradeLedgerIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "fill_exit_report_missing",
                1,
                f"Paper fill/exit simulator report missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "fill_exit_report_invalid_json",
                1,
                f"Paper fill/exit simulator report JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "fill_exit_report_invalid_shape",
                1,
                "Paper fill/exit simulator report must be a JSON object.",
            )
        ]

    return payload, []


def _fill_exit_report_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[BacktestTradeLedgerIssue]:
    if payload is None:
        return []

    issues: list[BacktestTradeLedgerIssue] = []
    status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_backtest_ledger"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "fill_exit_report_warn",
                1,
                "Paper fill/exit simulator status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "fill_exit_report_not_pass",
                1,
                f"Paper fill/exit simulator status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "fill_exit_report_not_ready",
                1,
                "Paper fill/exit simulator is not ready for future backtest ledger.",
            )
        )

    forbidden = _forbidden(payload)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "fill_exit_report_forbidden_fields",
                len(forbidden),
                "Paper fill/exit report contains forbidden broker/order/real-money fields.",
            )
        )

    return issues


def _lifecycles(
    payload: Mapping[str, Any] | None,
) -> tuple[list[Mapping[str, Any]], list[BacktestTradeLedgerIssue]]:
    if payload is None:
        return [], []

    raw_lifecycles = payload.get("paper_fill_exit_lifecycles")
    if not isinstance(raw_lifecycles, list):
        return [], [
            _issue(
                "fail",
                "paper_fill_exit_lifecycles_missing",
                1,
                "Paper fill/exit simulator report must include paper_fill_exit_lifecycles list.",
            )
        ]

    lifecycles: list[Mapping[str, Any]] = []
    invalid_shape = 0
    for lifecycle in raw_lifecycles:
        if isinstance(lifecycle, Mapping):
            lifecycles.append(lifecycle)
        else:
            invalid_shape += 1

    issues: list[BacktestTradeLedgerIssue] = []
    if invalid_shape:
        issues.append(
            _issue(
                "fail",
                "paper_fill_exit_lifecycles_invalid_shape",
                invalid_shape,
                f"{invalid_shape} fill/exit lifecycles are not JSON objects.",
            )
        )

    return lifecycles, issues


def _lifecycle_issues(lifecycle: Mapping[str, Any]) -> list[BacktestTradeLedgerIssue]:
    issues: list[BacktestTradeLedgerIssue] = []

    wrong_modes = [
        key
        for key, expected in EXPECTED_LIFECYCLE_MODES.items()
        if str(lifecycle.get(key) or "") != expected
    ]
    if wrong_modes:
        issues.append(
            _issue(
                "fail",
                "paper_fill_exit_lifecycle_wrong_modes",
                len(wrong_modes),
                "Paper fill/exit lifecycle has wrong safety/mode fields.",
            )
        )

    decision = str(lifecycle.get("decision") or "")
    option_type = str(lifecycle.get("option_type") or "")
    option_action = str(lifecycle.get("option_action") or "")

    if decision not in {"LONG", "SHORT"}:
        issues.append(
            _issue(
                "fail",
                "paper_fill_exit_lifecycle_invalid_decision",
                1,
                "Lifecycle decision must be LONG or SHORT.",
            )
        )

    if decision == "LONG" and option_type != "CE":
        issues.append(
            _issue(
                "fail",
                "paper_fill_exit_lifecycle_wrong_option_type",
                1,
                "LONG lifecycle must use CE.",
            )
        )

    if decision == "SHORT" and option_type != "PE":
        issues.append(
            _issue(
                "fail",
                "paper_fill_exit_lifecycle_wrong_option_type",
                1,
                "SHORT lifecycle must use PE.",
            )
        )

    if option_action != "BUY":
        issues.append(
            _issue(
                "fail",
                "paper_fill_exit_lifecycle_wrong_action",
                1,
                "Lifecycle option action must be BUY only.",
            )
        )

    required_numeric = {
        "entry_option_price_reference": lifecycle.get("entry_option_price_reference"),
        "exit_option_price_reference": lifecycle.get("exit_option_price_reference"),
        "option_points_result": lifecycle.get("option_points_result"),
        "quantity_lots": lifecycle.get("quantity_lots"),
        "lot_size": lifecycle.get("lot_size"),
    }

    missing_numeric = [
        key for key, value in required_numeric.items() if _to_float(value) is None
    ]
    if missing_numeric:
        issues.append(
            _issue(
                "fail",
                "paper_fill_exit_lifecycle_missing_numeric_fields",
                len(missing_numeric),
                "Lifecycle must include numeric entry, exit, points, quantity, and lot size fields.",
            )
        )

    if lifecycle.get("entry_timestamp") in (None, "") or lifecycle.get("exit_timestamp") in (None, ""):
        issues.append(
            _issue(
                "fail",
                "paper_fill_exit_lifecycle_missing_timestamps",
                1,
                "Lifecycle must include entry and exit timestamps.",
            )
        )

    forbidden = _forbidden(lifecycle)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_fill_exit_lifecycle_forbidden_fields",
                len(forbidden),
                "Lifecycle contains forbidden broker/order/real-money fields.",
            )
        )

    return issues


def _outcome(points_result: float) -> str:
    if points_result > 0:
        return "WIN"
    if points_result < 0:
        return "LOSS"
    return "FLAT"


def _ledger_row(index: int, lifecycle: Mapping[str, Any]) -> BacktestTradeLedgerRow:
    option_points_result = _to_float(lifecycle.get("option_points_result"))
    quantity_lots = _to_int(lifecycle.get("quantity_lots"))
    lot_size = _to_int(lifecycle.get("lot_size"))

    if option_points_result is None or quantity_lots is None or lot_size is None:
        raise ValueError("Ledger row requires option points result, quantity lots, and lot size.")

    simulated_gross_result = option_points_result * quantity_lots * lot_size

    return BacktestTradeLedgerRow(
        ledger_row_index=index,
        event_type="paper_backtest_trade_ledger_row_created",
        trade_id=f"PAPER-BACKTEST-TRADE-{index:06d}",
        source_paper_fill_exit_id=str(lifecycle.get("paper_fill_exit_id") or ""),
        source_paper_trade_plan_id=str(lifecycle.get("source_paper_trade_plan_id") or ""),
        source_decision_event_index=_to_int(lifecycle.get("source_decision_event_index")),
        underlying_symbol=str(lifecycle.get("underlying_symbol") or "NIFTY"),
        decision=str(lifecycle.get("decision") or ""),
        option_type=str(lifecycle.get("option_type") or ""),
        option_action="BUY",
        entry_timestamp=str(lifecycle.get("entry_timestamp") or ""),
        exit_timestamp=str(lifecycle.get("exit_timestamp") or ""),
        entry_option_price_reference=_to_float(lifecycle.get("entry_option_price_reference")) or 0.0,
        exit_option_price_reference=_to_float(lifecycle.get("exit_option_price_reference")) or 0.0,
        option_points_result=option_points_result,
        quantity_lots=max(quantity_lots, 1),
        lot_size=max(lot_size, 1),
        simulated_gross_result=simulated_gross_result,
        outcome=_outcome(option_points_result),
        exit_reason=str(lifecycle.get("exit_reason") or ""),
        holding_bars=max(_to_int(lifecycle.get("holding_bars")) or 0, 0),
        ledger_mode="paper_backtest_trade_ledger_only",
        result_mode="simulated_paper_reference_result_only",
        broker_execution_mode="broker_disabled",
        order_mode="orders_not_created",
        money_mode="real_money_not_used",
        output_mode="paper_backtest_trade_ledger_manifest_only",
    )


def build_backtest_trade_ledger_report(
    *,
    fill_exit_report_path: Path,
    output_dir: Path,
    min_trades: int = 1,
    allow_warnings: bool = False,
    max_lifecycles: int | None = None,
) -> BacktestTradeLedgerReport:
    min_trades = max(min_trades, 0)
    issues: list[BacktestTradeLedgerIssue] = []

    fill_exit_report, load_issues = _load_json_object(fill_exit_report_path)
    issues.extend(load_issues)
    issues.extend(_fill_exit_report_issues(fill_exit_report, allow_warnings=allow_warnings))

    lifecycles, lifecycle_load_issues = _lifecycles(fill_exit_report)
    issues.extend(lifecycle_load_issues)

    if max_lifecycles is not None:
        lifecycles = lifecycles[: max(max_lifecycles, 0)]

    ledger_rows: list[BacktestTradeLedgerRow] = []
    rejected_lifecycle_count = 0

    for lifecycle in lifecycles:
        lifecycle_issues = _lifecycle_issues(lifecycle)
        if lifecycle_issues:
            issues.extend(lifecycle_issues)
            rejected_lifecycle_count += 1
            continue

        ledger_rows.append(_ledger_row(len(ledger_rows) + 1, lifecycle))

    if len(ledger_rows) < min_trades:
        issues.append(
            _issue(
                "fail",
                "insufficient_backtest_ledger_trades",
                min_trades - len(ledger_rows),
                (
                    "Backtest trade ledger row count below minimum. "
                    f"Required={min_trades}, actual={len(ledger_rows)}."
                ),
            )
        )

    if rejected_lifecycle_count and not ledger_rows:
        issues.append(
            _issue(
                "fail",
                "no_valid_paper_fill_exit_lifecycles",
                rejected_lifecycle_count,
                "Fill/exit lifecycles existed, but none were valid for backtest ledger.",
            )
        )

    status = _status(issues)

    return BacktestTradeLedgerReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        fill_exit_report_path=str(fill_exit_report_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_backtest_metrics_engine=status in {"pass", "warn"},
        min_trades_required=min_trades,
        paper_fill_exit_lifecycle_count=len(lifecycles),
        ledger_trade_count=len(ledger_rows),
        ce_trade_count=sum(1 for row in ledger_rows if row.option_type == "CE"),
        pe_trade_count=sum(1 for row in ledger_rows if row.option_type == "PE"),
        winning_trade_count=sum(1 for row in ledger_rows if row.outcome == "WIN"),
        losing_trade_count=sum(1 for row in ledger_rows if row.outcome == "LOSS"),
        flat_trade_count=sum(1 for row in ledger_rows if row.outcome == "FLAT"),
        gross_option_points_result=sum(row.option_points_result for row in ledger_rows),
        simulated_gross_result_total=sum(row.simulated_gross_result for row in ledger_rows),
        safety_notice=safety_notice(),
        issues=issues,
        ledger_rows=ledger_rows,
    )


def write_backtest_trade_ledger_report(
    report: BacktestTradeLedgerReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    ledger_json = output_dir / "backtest_trade_ledger.json"
    ledger_rows_jsonl = output_dir / "backtest_trade_ledger_rows.jsonl"
    ledger_rows_csv = output_dir / "backtest_trade_ledger_rows.csv"
    ledger_txt = output_dir / "backtest_trade_ledger.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["ledger_rows"] = [asdict(row) for row in report.ledger_rows]

    ledger_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with ledger_rows_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for row in report.ledger_rows:
            handle.write(json.dumps(asdict(row), sort_keys=True))
            handle.write("\n")

    csv_fields = [
        "ledger_row_index",
        "trade_id",
        "underlying_symbol",
        "decision",
        "option_type",
        "option_action",
        "entry_timestamp",
        "exit_timestamp",
        "entry_option_price_reference",
        "exit_option_price_reference",
        "option_points_result",
        "quantity_lots",
        "lot_size",
        "simulated_gross_result",
        "outcome",
        "exit_reason",
        "holding_bars",
    ]
    with ledger_rows_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for row in report.ledger_rows:
            payload = asdict(row)
            writer.writerow({field: payload[field] for field in csv_fields})

    lines = [
        "HQE Recorded Data Backtest Trade Ledger",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future backtest metrics engine: {report.ready_for_future_backtest_metrics_engine}",
        f"Ledger trades: {report.ledger_trade_count}",
        f"CE trades: {report.ce_trade_count}",
        f"PE trades: {report.pe_trade_count}",
        f"Winning trades: {report.winning_trade_count}",
        f"Losing trades: {report.losing_trade_count}",
        f"Flat trades: {report.flat_trade_count}",
        f"Gross option points result: {report.gross_option_points_result}",
        f"Simulated gross result total: {report.simulated_gross_result_total}",
        "",
        "Result formula:",
        "simulated_gross_result = option_points_result * quantity_lots * lot_size",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Backtest trade ledger is ready for future metrics engine.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: "
                f"{issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {ledger_json}",
            f"- {ledger_rows_jsonl}",
            f"- {ledger_rows_csv}",
            f"- {ledger_txt}",
            f"- {manifest_json}",
            "",
            "This ledger is paper/simulation only.",
            "This ledger does not use real money or create broker orders.",
            "This report is not a profitability claim.",
        ]
    )
    ledger_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_backtest_trade_ledger",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_backtest_metrics_engine": report.ready_for_future_backtest_metrics_engine,
        "ledger_trade_count": report.ledger_trade_count,
        "ce_trade_count": report.ce_trade_count,
        "pe_trade_count": report.pe_trade_count,
        "winning_trade_count": report.winning_trade_count,
        "losing_trade_count": report.losing_trade_count,
        "flat_trade_count": report.flat_trade_count,
        "gross_option_points_result": report.gross_option_points_result,
        "simulated_gross_result_total": report.simulated_gross_result_total,
        "safety_notice": report.safety_notice,
        "outputs": {
            "backtest_trade_ledger_json": str(ledger_json),
            "backtest_trade_ledger_rows_jsonl": str(ledger_rows_jsonl),
            "backtest_trade_ledger_rows_csv": str(ledger_rows_csv),
            "backtest_trade_ledger_txt": str(ledger_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "backtest_trade_ledger_json": ledger_json,
        "backtest_trade_ledger_rows_jsonl": ledger_rows_jsonl,
        "backtest_trade_ledger_rows_csv": ledger_rows_csv,
        "backtest_trade_ledger_txt": ledger_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_backtest_trade_ledger_report(
    *,
    fill_exit_report_path: Path,
    output_dir: Path,
    min_trades: int = 1,
    allow_warnings: bool = False,
    max_lifecycles: int | None = None,
) -> tuple[BacktestTradeLedgerReport, dict[str, Path]]:
    report = build_backtest_trade_ledger_report(
        fill_exit_report_path=fill_exit_report_path,
        output_dir=output_dir,
        min_trades=min_trades,
        allow_warnings=allow_warnings,
        max_lifecycles=max_lifecycles,
    )
    outputs = write_backtest_trade_ledger_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper backtest trade ledger from fill/exit lifecycle records."
    )
    parser.add_argument(
        "--fill-exit-report",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_fill_exit_simulator/"
            "paper_fill_exit_simulator.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_backtest_trade_ledger",
    )
    parser.add_argument("--min-trades", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-lifecycles", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_backtest_trade_ledger_report(
        fill_exit_report_path=Path(args.fill_exit_report),
        output_dir=Path(args.output_dir),
        min_trades=args.min_trades,
        allow_warnings=args.allow_warnings,
        max_lifecycles=args.max_lifecycles,
    )

    print("HQE recorded data backtest trade ledger completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Ledger trades: "
        f"total={report.ledger_trade_count}, wins={report.winning_trade_count}, "
        f"losses={report.losing_trade_count}, flat={report.flat_trade_count}"
    )
    print(f"Backtest trade ledger report: {outputs['backtest_trade_ledger_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
