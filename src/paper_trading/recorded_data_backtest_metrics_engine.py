"""
Recorded data backtest metrics engine.

Module AAA in the fast-track v1.0 Testing Edition path.

This module converts paper-only backtest trade ledger rows into paper-only
backtest metrics, including win rate, simulated result totals, equity reference
curve, and max drawdown reference values.

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


EXPECTED_LEDGER_MODES = {
    "event_type": "paper_backtest_trade_ledger_row_created",
    "option_action": "BUY",
    "ledger_mode": "paper_backtest_trade_ledger_only",
    "result_mode": "simulated_paper_reference_result_only",
    "broker_execution_mode": "broker_disabled",
    "order_mode": "orders_not_created",
    "money_mode": "real_money_not_used",
    "output_mode": "paper_backtest_trade_ledger_manifest_only",
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
class BacktestMetricsIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class BacktestEquityPoint:
    equity_point_index: int
    trade_id: str
    exit_timestamp: str
    trade_result: float
    cumulative_result: float
    equity_reference: float
    running_peak_equity_reference: float
    drawdown_reference: float
    drawdown_percent_reference: float


@dataclass(frozen=True)
class BacktestMetricsReport:
    generated_at_utc: str
    trade_ledger_path: str
    output_directory: str
    status: str
    ready_for_future_backtest_report_writer: bool
    min_trades_required: int
    starting_equity_reference: float
    ledger_trade_count: int
    metric_trade_count: int
    winning_trade_count: int
    losing_trade_count: int
    flat_trade_count: int
    win_rate_percent: float
    loss_rate_percent: float
    flat_rate_percent: float
    simulated_gross_result_total: float
    average_trade_result: float
    average_winning_trade_result: float
    average_losing_trade_result: float
    largest_winning_trade_result: float
    largest_losing_trade_result: float
    expectancy_per_trade_reference: float
    final_equity_reference: float
    max_drawdown_reference: float
    max_drawdown_percent_reference: float
    safety_notice: str
    issues: list[BacktestMetricsIssue]
    equity_curve: list[BacktestEquityPoint]


def safety_notice() -> str:
    return (
        "Paper/simulation backtest metrics only. Metrics are simulated reference "
        "values derived from recorded replay trade ledger rows. This module does "
        "not connect to brokers, request live market data, place real orders, use "
        "real money, or prove profitability."
    )


def _issue(severity: str, code: str, count: int, message: str) -> BacktestMetricsIssue:
    return BacktestMetricsIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[BacktestMetricsIssue]) -> str:
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


def _round(value: float) -> float:
    return round(float(value), 10)


def _rate(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return _round((part / total) * 100.0)


def _average(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return _round(sum(values) / len(values))


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _load_ledger(path: Path) -> tuple[Mapping[str, Any] | None, list[BacktestMetricsIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "trade_ledger_missing",
                1,
                f"Backtest trade ledger missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "trade_ledger_invalid_json",
                1,
                f"Backtest trade ledger JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "trade_ledger_invalid_shape",
                1,
                "Backtest trade ledger must be a JSON object.",
            )
        ]

    return payload, []


def _ledger_report_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[BacktestMetricsIssue]:
    if payload is None:
        return []

    issues: list[BacktestMetricsIssue] = []
    status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_backtest_metrics_engine"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "trade_ledger_warn",
                1,
                "Backtest trade ledger status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "trade_ledger_not_pass",
                1,
                f"Backtest trade ledger status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "trade_ledger_not_ready",
                1,
                "Backtest trade ledger is not ready for future metrics engine.",
            )
        )

    forbidden = _forbidden(payload)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "trade_ledger_forbidden_fields",
                len(forbidden),
                "Trade ledger report contains forbidden broker/order/real-money fields.",
            )
        )

    return issues


def _ledger_rows(
    payload: Mapping[str, Any] | None,
) -> tuple[list[Mapping[str, Any]], list[BacktestMetricsIssue]]:
    if payload is None:
        return [], []

    raw_rows = payload.get("ledger_rows")
    if not isinstance(raw_rows, list):
        return [], [
            _issue(
                "fail",
                "ledger_rows_missing",
                1,
                "Backtest trade ledger must include ledger_rows list.",
            )
        ]

    rows: list[Mapping[str, Any]] = []
    invalid_shape = 0
    for row in raw_rows:
        if isinstance(row, Mapping):
            rows.append(row)
        else:
            invalid_shape += 1

    issues: list[BacktestMetricsIssue] = []
    if invalid_shape:
        issues.append(
            _issue(
                "fail",
                "ledger_rows_invalid_shape",
                invalid_shape,
                f"{invalid_shape} ledger rows are not JSON objects.",
            )
        )

    return rows, issues


def _row_issues(row: Mapping[str, Any]) -> list[BacktestMetricsIssue]:
    issues: list[BacktestMetricsIssue] = []

    wrong_modes = [
        key
        for key, expected in EXPECTED_LEDGER_MODES.items()
        if str(row.get(key) or "") != expected
    ]
    if wrong_modes:
        issues.append(
            _issue(
                "fail",
                "ledger_row_wrong_modes",
                len(wrong_modes),
                "Ledger row has wrong safety/mode fields.",
            )
        )

    option_type = str(row.get("option_type") or "")
    decision = str(row.get("decision") or "")
    outcome = str(row.get("outcome") or "")

    if option_type not in {"CE", "PE"}:
        issues.append(
            _issue(
                "fail",
                "ledger_row_invalid_option_type",
                1,
                "Ledger row option type must be CE or PE.",
            )
        )

    if decision not in {"LONG", "SHORT"}:
        issues.append(
            _issue(
                "fail",
                "ledger_row_invalid_decision",
                1,
                "Ledger row decision must be LONG or SHORT.",
            )
        )

    if outcome not in {"WIN", "LOSS", "FLAT"}:
        issues.append(
            _issue(
                "fail",
                "ledger_row_invalid_outcome",
                1,
                "Ledger row outcome must be WIN, LOSS, or FLAT.",
            )
        )

    numeric_fields = {
        "option_points_result": row.get("option_points_result"),
        "quantity_lots": row.get("quantity_lots"),
        "lot_size": row.get("lot_size"),
        "simulated_gross_result": row.get("simulated_gross_result"),
    }
    missing_numeric = [
        key for key, value in numeric_fields.items() if _to_float(value) is None
    ]
    if missing_numeric:
        issues.append(
            _issue(
                "fail",
                "ledger_row_missing_numeric_fields",
                len(missing_numeric),
                "Ledger row must include numeric points, quantity, lot size, and simulated result.",
            )
        )

    if row.get("trade_id") in (None, "") or row.get("exit_timestamp") in (None, ""):
        issues.append(
            _issue(
                "fail",
                "ledger_row_missing_identifiers",
                1,
                "Ledger row must include trade_id and exit_timestamp.",
            )
        )

    forbidden = _forbidden(row)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "ledger_row_forbidden_fields",
                len(forbidden),
                "Ledger row contains forbidden broker/order/real-money fields.",
            )
        )

    return issues


def _equity_curve(
    rows: Sequence[Mapping[str, Any]],
    *,
    starting_equity_reference: float,
) -> list[BacktestEquityPoint]:
    curve: list[BacktestEquityPoint] = []
    cumulative_result = 0.0
    peak = starting_equity_reference

    for index, row in enumerate(rows, start=1):
        trade_result = _to_float(row.get("simulated_gross_result")) or 0.0
        cumulative_result = _round(cumulative_result + trade_result)
        equity_reference = _round(starting_equity_reference + cumulative_result)
        peak = max(peak, equity_reference)
        drawdown = _round(peak - equity_reference)
        drawdown_percent = 0.0 if peak <= 0 else _round((drawdown / peak) * 100.0)

        curve.append(
            BacktestEquityPoint(
                equity_point_index=index,
                trade_id=str(row.get("trade_id") or ""),
                exit_timestamp=str(row.get("exit_timestamp") or ""),
                trade_result=_round(trade_result),
                cumulative_result=cumulative_result,
                equity_reference=equity_reference,
                running_peak_equity_reference=_round(peak),
                drawdown_reference=drawdown,
                drawdown_percent_reference=drawdown_percent,
            )
        )

    return curve


def build_backtest_metrics_report(
    *,
    trade_ledger_path: Path,
    output_dir: Path,
    min_trades: int = 1,
    starting_equity_reference: float = 100000.0,
    allow_warnings: bool = False,
    max_rows: int | None = None,
) -> BacktestMetricsReport:
    min_trades = max(min_trades, 0)
    starting_equity_reference = max(float(starting_equity_reference), 0.0)

    issues: list[BacktestMetricsIssue] = []

    ledger, load_issues = _load_ledger(trade_ledger_path)
    issues.extend(load_issues)
    issues.extend(_ledger_report_issues(ledger, allow_warnings=allow_warnings))

    rows, row_load_issues = _ledger_rows(ledger)
    issues.extend(row_load_issues)

    if max_rows is not None:
        rows = rows[: max(max_rows, 0)]

    valid_rows: list[Mapping[str, Any]] = []
    rejected_rows = 0

    for row in rows:
        row_issues = _row_issues(row)
        if row_issues:
            issues.extend(row_issues)
            rejected_rows += 1
            continue
        valid_rows.append(row)

    if len(valid_rows) < min_trades:
        issues.append(
            _issue(
                "fail",
                "insufficient_backtest_metric_trades",
                min_trades - len(valid_rows),
                (
                    "Backtest metrics trade count below minimum. "
                    f"Required={min_trades}, actual={len(valid_rows)}."
                ),
            )
        )

    if rejected_rows and not valid_rows:
        issues.append(
            _issue(
                "fail",
                "no_valid_backtest_ledger_rows",
                rejected_rows,
                "Ledger rows existed, but none were valid for metrics.",
            )
        )

    results = [_to_float(row.get("simulated_gross_result")) or 0.0 for row in valid_rows]
    wins = [value for value in results if value > 0]
    losses = [value for value in results if value < 0]
    flats = [value for value in results if value == 0]

    curve = _equity_curve(valid_rows, starting_equity_reference=starting_equity_reference)
    max_drawdown = max((point.drawdown_reference for point in curve), default=0.0)
    max_drawdown_percent = max((point.drawdown_percent_reference for point in curve), default=0.0)
    simulated_total = _round(sum(results))
    trade_count = len(valid_rows)

    status = _status(issues)

    return BacktestMetricsReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        trade_ledger_path=str(trade_ledger_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_backtest_report_writer=status in {"pass", "warn"},
        min_trades_required=min_trades,
        starting_equity_reference=_round(starting_equity_reference),
        ledger_trade_count=len(rows),
        metric_trade_count=trade_count,
        winning_trade_count=len(wins),
        losing_trade_count=len(losses),
        flat_trade_count=len(flats),
        win_rate_percent=_rate(len(wins), trade_count),
        loss_rate_percent=_rate(len(losses), trade_count),
        flat_rate_percent=_rate(len(flats), trade_count),
        simulated_gross_result_total=simulated_total,
        average_trade_result=_average(results),
        average_winning_trade_result=_average(wins),
        average_losing_trade_result=_average(losses),
        largest_winning_trade_result=_round(max(wins, default=0.0)),
        largest_losing_trade_result=_round(min(losses, default=0.0)),
        expectancy_per_trade_reference=_average(results),
        final_equity_reference=_round(starting_equity_reference + simulated_total),
        max_drawdown_reference=_round(max_drawdown),
        max_drawdown_percent_reference=_round(max_drawdown_percent),
        safety_notice=safety_notice(),
        issues=issues,
        equity_curve=curve,
    )


def write_backtest_metrics_report(
    report: BacktestMetricsReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_json = output_dir / "backtest_metrics.json"
    equity_curve_jsonl = output_dir / "backtest_equity_curve.jsonl"
    equity_curve_csv = output_dir / "backtest_equity_curve.csv"
    metrics_txt = output_dir / "backtest_metrics.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["equity_curve"] = [asdict(point) for point in report.equity_curve]

    metrics_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with equity_curve_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for point in report.equity_curve:
            handle.write(json.dumps(asdict(point), sort_keys=True))
            handle.write("\n")

    csv_fields = [
        "equity_point_index",
        "trade_id",
        "exit_timestamp",
        "trade_result",
        "cumulative_result",
        "equity_reference",
        "running_peak_equity_reference",
        "drawdown_reference",
        "drawdown_percent_reference",
    ]
    with equity_curve_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for point in report.equity_curve:
            payload = asdict(point)
            writer.writerow({field: payload[field] for field in csv_fields})

    lines = [
        "HQE Recorded Data Backtest Metrics Engine",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future backtest report writer: {report.ready_for_future_backtest_report_writer}",
        f"Metric trades: {report.metric_trade_count}",
        f"Wins: {report.winning_trade_count}",
        f"Losses: {report.losing_trade_count}",
        f"Flat: {report.flat_trade_count}",
        f"Win rate percent: {report.win_rate_percent}",
        f"Loss rate percent: {report.loss_rate_percent}",
        f"Simulated gross result total: {report.simulated_gross_result_total}",
        f"Average trade result: {report.average_trade_result}",
        f"Final equity reference: {report.final_equity_reference}",
        f"Max drawdown reference: {report.max_drawdown_reference}",
        f"Max drawdown percent reference: {report.max_drawdown_percent_reference}",
        "",
        "Important:",
        "- These are simulated paper reference metrics only.",
        "- They are not real broker PnL.",
        "- This report is not a profitability claim.",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Backtest metrics are ready for future report writer.")
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
            f"- {metrics_json}",
            f"- {equity_curve_jsonl}",
            f"- {equity_curve_csv}",
            f"- {metrics_txt}",
            f"- {manifest_json}",
        ]
    )
    metrics_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_backtest_metrics_engine",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_backtest_report_writer": report.ready_for_future_backtest_report_writer,
        "metric_trade_count": report.metric_trade_count,
        "win_rate_percent": report.win_rate_percent,
        "loss_rate_percent": report.loss_rate_percent,
        "simulated_gross_result_total": report.simulated_gross_result_total,
        "final_equity_reference": report.final_equity_reference,
        "max_drawdown_reference": report.max_drawdown_reference,
        "max_drawdown_percent_reference": report.max_drawdown_percent_reference,
        "safety_notice": report.safety_notice,
        "outputs": {
            "backtest_metrics_json": str(metrics_json),
            "backtest_equity_curve_jsonl": str(equity_curve_jsonl),
            "backtest_equity_curve_csv": str(equity_curve_csv),
            "backtest_metrics_txt": str(metrics_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "backtest_metrics_json": metrics_json,
        "backtest_equity_curve_jsonl": equity_curve_jsonl,
        "backtest_equity_curve_csv": equity_curve_csv,
        "backtest_metrics_txt": metrics_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_backtest_metrics_report(
    *,
    trade_ledger_path: Path,
    output_dir: Path,
    min_trades: int = 1,
    starting_equity_reference: float = 100000.0,
    allow_warnings: bool = False,
    max_rows: int | None = None,
) -> tuple[BacktestMetricsReport, dict[str, Path]]:
    report = build_backtest_metrics_report(
        trade_ledger_path=trade_ledger_path,
        output_dir=output_dir,
        min_trades=min_trades,
        starting_equity_reference=starting_equity_reference,
        allow_warnings=allow_warnings,
        max_rows=max_rows,
    )
    outputs = write_backtest_metrics_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper backtest metrics from trade ledger rows."
    )
    parser.add_argument(
        "--trade-ledger",
        default=(
            "reports/paper_trading/"
            "recorded_data_backtest_trade_ledger/"
            "backtest_trade_ledger.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_backtest_metrics_engine",
    )
    parser.add_argument("--min-trades", type=int, default=1)
    parser.add_argument("--starting-equity-reference", type=float, default=100000.0)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-rows", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_backtest_metrics_report(
        trade_ledger_path=Path(args.trade_ledger),
        output_dir=Path(args.output_dir),
        min_trades=args.min_trades,
        starting_equity_reference=args.starting_equity_reference,
        allow_warnings=args.allow_warnings,
        max_rows=args.max_rows,
    )

    print("HQE recorded data backtest metrics engine completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Metrics: "
        f"trades={report.metric_trade_count}, win_rate={report.win_rate_percent}, "
        f"simulated_total={report.simulated_gross_result_total}"
    )
    print(f"Backtest metrics report: {outputs['backtest_metrics_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
