"""
Recorded data backtest report writer.

Module BBB in the fast-track v1.0 Testing Edition path.

This module packages paper-only backtest metrics and paper-only trade ledger
rows into a readable backtest report bundle.

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
class BacktestReportWriterIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class BacktestReportSummary:
    metric_trade_count: int
    winning_trade_count: int
    losing_trade_count: int
    flat_trade_count: int
    win_rate_percent: float
    loss_rate_percent: float
    flat_rate_percent: float
    simulated_gross_result_total: float
    average_trade_result: float
    largest_winning_trade_result: float
    largest_losing_trade_result: float
    final_equity_reference: float
    max_drawdown_reference: float
    max_drawdown_percent_reference: float


@dataclass(frozen=True)
class BacktestReportWriterReport:
    generated_at_utc: str
    metrics_path: str
    trade_ledger_path: str
    output_directory: str
    status: str
    ready_for_future_one_command_backtest_runner: bool
    min_trades_required: int
    report_title: str
    strategy_scope: str
    safety_notice: str
    summary: BacktestReportSummary
    issue_count: int
    issues: list[BacktestReportWriterIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation backtest report only. Metrics and trade rows are "
        "simulated reference values derived from recorded replay data. This "
        "module does not connect to brokers, request live market data, place "
        "real orders, use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> BacktestReportWriterIssue:
    return BacktestReportWriterIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[BacktestReportWriterIssue]) -> str:
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


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _load_json_object(
    path: Path,
    *,
    missing_code: str,
    invalid_code: str,
) -> tuple[Mapping[str, Any] | None, list[BacktestReportWriterIssue]]:
    if not path.exists():
        return None, [_issue("fail", missing_code, 1, f"Required JSON file missing: {path}")]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [_issue("fail", invalid_code, 1, f"JSON parse failed: {exc}")]

    if not isinstance(payload, Mapping):
        return None, [_issue("fail", invalid_code, 1, "JSON payload must be an object.")]

    return payload, []


def _metrics_issues(
    metrics: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[BacktestReportWriterIssue]:
    if metrics is None:
        return []

    issues: list[BacktestReportWriterIssue] = []
    status = str(metrics.get("status") or "unknown").lower()
    ready = bool(metrics.get("ready_for_future_backtest_report_writer"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "backtest_metrics_warn",
                1,
                "Backtest metrics status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "backtest_metrics_not_pass",
                1,
                f"Backtest metrics status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "backtest_metrics_not_ready",
                1,
                "Backtest metrics are not ready for future report writer.",
            )
        )

    forbidden = _forbidden(metrics)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "backtest_metrics_forbidden_fields",
                len(forbidden),
                "Backtest metrics contain forbidden broker/order/real-money fields.",
            )
        )

    required_numeric = [
        "metric_trade_count",
        "winning_trade_count",
        "losing_trade_count",
        "flat_trade_count",
        "win_rate_percent",
        "simulated_gross_result_total",
        "final_equity_reference",
        "max_drawdown_reference",
    ]
    missing_numeric = [
        key for key in required_numeric if _to_float(metrics.get(key)) is None
    ]
    if missing_numeric:
        issues.append(
            _issue(
                "fail",
                "backtest_metrics_missing_numeric_fields",
                len(missing_numeric),
                "Backtest metrics are missing required numeric summary fields.",
            )
        )

    return issues


def _ledger_issues(
    ledger: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[BacktestReportWriterIssue]:
    if ledger is None:
        return []

    issues: list[BacktestReportWriterIssue] = []
    status = str(ledger.get("status") or "unknown").lower()
    ready = bool(ledger.get("ready_for_future_backtest_metrics_engine"))

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
                "Backtest trade ledger is not ready for metrics engine.",
            )
        )

    forbidden = _forbidden(ledger)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "trade_ledger_forbidden_fields",
                len(forbidden),
                "Trade ledger contains forbidden broker/order/real-money fields.",
            )
        )

    rows = ledger.get("ledger_rows")
    if not isinstance(rows, list):
        issues.append(
            _issue(
                "fail",
                "trade_ledger_rows_missing",
                1,
                "Backtest trade ledger must include ledger_rows list.",
            )
        )

    return issues


def _summary_from_metrics(metrics: Mapping[str, Any] | None) -> BacktestReportSummary:
    metrics = metrics or {}
    return BacktestReportSummary(
        metric_trade_count=_to_int(metrics.get("metric_trade_count")) or 0,
        winning_trade_count=_to_int(metrics.get("winning_trade_count")) or 0,
        losing_trade_count=_to_int(metrics.get("losing_trade_count")) or 0,
        flat_trade_count=_to_int(metrics.get("flat_trade_count")) or 0,
        win_rate_percent=_round(_to_float(metrics.get("win_rate_percent")) or 0.0),
        loss_rate_percent=_round(_to_float(metrics.get("loss_rate_percent")) or 0.0),
        flat_rate_percent=_round(_to_float(metrics.get("flat_rate_percent")) or 0.0),
        simulated_gross_result_total=_round(
            _to_float(metrics.get("simulated_gross_result_total")) or 0.0
        ),
        average_trade_result=_round(_to_float(metrics.get("average_trade_result")) or 0.0),
        largest_winning_trade_result=_round(
            _to_float(metrics.get("largest_winning_trade_result")) or 0.0
        ),
        largest_losing_trade_result=_round(
            _to_float(metrics.get("largest_losing_trade_result")) or 0.0
        ),
        final_equity_reference=_round(_to_float(metrics.get("final_equity_reference")) or 0.0),
        max_drawdown_reference=_round(_to_float(metrics.get("max_drawdown_reference")) or 0.0),
        max_drawdown_percent_reference=_round(
            _to_float(metrics.get("max_drawdown_percent_reference")) or 0.0
        ),
    )


def _ledger_count(ledger: Mapping[str, Any] | None) -> int:
    if ledger is None:
        return 0
    rows = ledger.get("ledger_rows")
    if not isinstance(rows, list):
        return 0
    return len(rows)


def _top_ledger_rows(ledger: Mapping[str, Any] | None, limit: int) -> list[Mapping[str, Any]]:
    if ledger is None:
        return []
    rows = ledger.get("ledger_rows")
    if not isinstance(rows, list):
        return []
    valid_rows = [row for row in rows if isinstance(row, Mapping)]
    return valid_rows[: max(limit, 0)]


def build_backtest_report_writer_report(
    *,
    metrics_path: Path,
    trade_ledger_path: Path,
    output_dir: Path,
    min_trades: int = 1,
    report_title: str = "HQE Recorded Data Paper Backtest Report",
    allow_warnings: bool = False,
) -> BacktestReportWriterReport:
    min_trades = max(min_trades, 0)

    issues: list[BacktestReportWriterIssue] = []

    metrics, metrics_load_issues = _load_json_object(
        metrics_path,
        missing_code="backtest_metrics_missing",
        invalid_code="backtest_metrics_invalid_json",
    )
    ledger, ledger_load_issues = _load_json_object(
        trade_ledger_path,
        missing_code="trade_ledger_missing",
        invalid_code="trade_ledger_invalid_json",
    )

    issues.extend(metrics_load_issues)
    issues.extend(ledger_load_issues)
    issues.extend(_metrics_issues(metrics, allow_warnings=allow_warnings))
    issues.extend(_ledger_issues(ledger, allow_warnings=allow_warnings))

    summary = _summary_from_metrics(metrics)
    ledger_count = _ledger_count(ledger)

    if summary.metric_trade_count < min_trades:
        issues.append(
            _issue(
                "fail",
                "insufficient_metric_trades",
                min_trades - summary.metric_trade_count,
                (
                    "Backtest report metric trade count below minimum. "
                    f"Required={min_trades}, actual={summary.metric_trade_count}."
                ),
            )
        )

    if ledger_count < min_trades:
        issues.append(
            _issue(
                "fail",
                "insufficient_ledger_trades",
                min_trades - ledger_count,
                (
                    "Backtest report ledger trade count below minimum. "
                    f"Required={min_trades}, actual={ledger_count}."
                ),
            )
        )

    if metrics is not None and ledger is not None and ledger_count != summary.metric_trade_count:
        issues.append(
            _issue(
                "fail",
                "metric_ledger_trade_count_mismatch",
                1,
                (
                    "Metric trade count does not match ledger row count. "
                    f"metrics={summary.metric_trade_count}, ledger={ledger_count}."
                ),
            )
        )

    status = _status(issues)

    return BacktestReportWriterReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        metrics_path=str(metrics_path),
        trade_ledger_path=str(trade_ledger_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_one_command_backtest_runner=status in {"pass", "warn"},
        min_trades_required=min_trades,
        report_title=report_title,
        strategy_scope="NIFTY option-buy paper backtest: LONG=CE BUY, SHORT=PE BUY, NEUTRAL=no trade",
        safety_notice=safety_notice(),
        summary=summary,
        issue_count=len(issues),
        issues=issues,
    )


def write_backtest_report_writer_report(
    report: BacktestReportWriterReport,
    output_dir: Path,
    *,
    ledger_rows: Sequence[Mapping[str, Any]] | None = None,
    max_preview_rows: int = 20,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    report_json = output_dir / "backtest_report.json"
    report_txt = output_dir / "backtest_report.txt"
    summary_csv = output_dir / "backtest_report_summary.csv"
    preview_jsonl = output_dir / "backtest_report_trade_preview.jsonl"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["summary"] = asdict(report.summary)
    data["issues"] = [asdict(issue) for issue in report.issues]

    report_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        for key, value in asdict(report.summary).items():
            writer.writerow([key, value])
        writer.writerow(["status", report.status])
        writer.writerow(["ready_for_future_one_command_backtest_runner", report.ready_for_future_one_command_backtest_runner])
        writer.writerow(["strategy_scope", report.strategy_scope])

    preview_rows = list(ledger_rows or [])[: max(max_preview_rows, 0)]
    with preview_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for row in preview_rows:
            handle.write(json.dumps(dict(row), sort_keys=True))
            handle.write("\n")

    lines = [
        report.report_title,
        "",
        report.safety_notice,
        "",
        "Strategy scope:",
        report.strategy_scope,
        "",
        f"Status: {report.status}",
        f"Ready for future one-command backtest runner: {report.ready_for_future_one_command_backtest_runner}",
        "",
        "Summary:",
        f"- Trades: {report.summary.metric_trade_count}",
        f"- Wins: {report.summary.winning_trade_count}",
        f"- Losses: {report.summary.losing_trade_count}",
        f"- Flat: {report.summary.flat_trade_count}",
        f"- Win rate percent: {report.summary.win_rate_percent}",
        f"- Loss rate percent: {report.summary.loss_rate_percent}",
        f"- Simulated gross result total: {report.summary.simulated_gross_result_total}",
        f"- Average trade result: {report.summary.average_trade_result}",
        f"- Largest winning trade result: {report.summary.largest_winning_trade_result}",
        f"- Largest losing trade result: {report.summary.largest_losing_trade_result}",
        f"- Final equity reference: {report.summary.final_equity_reference}",
        f"- Max drawdown reference: {report.summary.max_drawdown_reference}",
        f"- Max drawdown percent reference: {report.summary.max_drawdown_percent_reference}",
        "",
        "Important:",
        "- This is a paper/simulation report only.",
        "- These are simulated reference values, not broker PnL.",
        "- This report is not a profitability claim.",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Backtest report bundle is ready for future one-command runner.")
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
            f"- {report_json}",
            f"- {report_txt}",
            f"- {summary_csv}",
            f"- {preview_jsonl}",
            f"- {manifest_json}",
        ]
    )
    report_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_backtest_report_writer",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_one_command_backtest_runner": report.ready_for_future_one_command_backtest_runner,
        "metric_trade_count": report.summary.metric_trade_count,
        "simulated_gross_result_total": report.summary.simulated_gross_result_total,
        "max_drawdown_reference": report.summary.max_drawdown_reference,
        "safety_notice": report.safety_notice,
        "outputs": {
            "backtest_report_json": str(report_json),
            "backtest_report_txt": str(report_txt),
            "backtest_report_summary_csv": str(summary_csv),
            "backtest_report_trade_preview_jsonl": str(preview_jsonl),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "backtest_report_json": report_json,
        "backtest_report_txt": report_txt,
        "backtest_report_summary_csv": summary_csv,
        "backtest_report_trade_preview_jsonl": preview_jsonl,
        "manifest_json": manifest_json,
    }


def build_and_write_backtest_report_writer_report(
    *,
    metrics_path: Path,
    trade_ledger_path: Path,
    output_dir: Path,
    min_trades: int = 1,
    report_title: str = "HQE Recorded Data Paper Backtest Report",
    allow_warnings: bool = False,
    max_preview_rows: int = 20,
) -> tuple[BacktestReportWriterReport, dict[str, Path]]:
    report = build_backtest_report_writer_report(
        metrics_path=metrics_path,
        trade_ledger_path=trade_ledger_path,
        output_dir=output_dir,
        min_trades=min_trades,
        report_title=report_title,
        allow_warnings=allow_warnings,
    )

    ledger_payload, _ = _load_json_object(
        trade_ledger_path,
        missing_code="trade_ledger_missing",
        invalid_code="trade_ledger_invalid_json",
    )
    ledger_rows = _top_ledger_rows(ledger_payload, max_preview_rows)

    outputs = write_backtest_report_writer_report(
        report,
        output_dir,
        ledger_rows=ledger_rows,
        max_preview_rows=max_preview_rows,
    )
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build readable paper backtest report from metrics and ledger."
    )
    parser.add_argument(
        "--metrics",
        default=(
            "reports/paper_trading/"
            "recorded_data_backtest_metrics_engine/"
            "backtest_metrics.json"
        ),
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
        default="reports/paper_trading/recorded_data_backtest_report_writer",
    )
    parser.add_argument("--min-trades", type=int, default=1)
    parser.add_argument("--report-title", default="HQE Recorded Data Paper Backtest Report")
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-preview-rows", type=int, default=20)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_backtest_report_writer_report(
        metrics_path=Path(args.metrics),
        trade_ledger_path=Path(args.trade_ledger),
        output_dir=Path(args.output_dir),
        min_trades=args.min_trades,
        report_title=args.report_title,
        allow_warnings=args.allow_warnings,
        max_preview_rows=args.max_preview_rows,
    )

    print("HQE recorded data backtest report writer completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Report summary: "
        f"trades={report.summary.metric_trade_count}, "
        f"win_rate={report.summary.win_rate_percent}, "
        f"simulated_total={report.summary.simulated_gross_result_total}"
    )
    print(f"Backtest report: {outputs['backtest_report_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
