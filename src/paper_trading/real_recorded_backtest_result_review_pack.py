"""
Real Recorded Backtest Result Review Pack

Reviews the latest recorded-data paper backtest outputs and produces a
safe result-review pack.

This module does not claim profitability. It explicitly labels all metrics as
paper/simulation reference values, highlights deterministic option reference
pricing assumptions, and checks that broker/order/money safety fields remain
disabled.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_OUTPUT_DIR = Path("reports/paper_trading/real_recorded_backtest_result_review_pack")

DEFAULT_READINESS_PATH = Path(
    "reports/paper_trading/recorded_data_backtest_readiness_gate/backtest_readiness_gate.json"
)
DEFAULT_ACCEPTANCE_PATH = Path(
    "reports/paper_trading/recorded_data_backtest_acceptance_gate/backtest_acceptance_gate.json"
)
DEFAULT_RUNNER_PATH = Path(
    "reports/paper_trading/recorded_data_one_command_backtest_runner/one_command_backtest_runner.json"
)
DEFAULT_LEDGER_PATH = Path(
    "reports/paper_trading/recorded_data_backtest_trade_ledger/backtest_trade_ledger.json"
)
DEFAULT_METRICS_PATH = Path(
    "reports/paper_trading/recorded_data_backtest_metrics_engine/backtest_metrics.json"
)
DEFAULT_REPORT_PATH = Path(
    "reports/paper_trading/recorded_data_backtest_report_writer/backtest_report.json"
)

SAFE_BROKER_MODE = "broker_disabled"
SAFE_ORDER_MODE = "orders_not_created"
SAFE_MONEY_MODE = "real_money_not_used"


@dataclass(frozen=True)
class ResultReviewIssue:
    """One review finding."""

    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class ResultReviewChecklistItem:
    """One review checklist row."""

    item: str
    status: str
    detail: str


@dataclass(frozen=True)
class ResultReviewReport:
    """Recorded backtest result review report."""

    generated_at_utc: str
    status: str
    accepted_for_future_tuning_review: bool
    output_directory: str
    safety_notice: str
    no_profitability_claim_notice: str
    deterministic_pricing_warning: str
    readiness_report_path: str
    acceptance_report_path: str
    runner_report_path: str
    ledger_report_path: str
    metrics_report_path: str
    backtest_report_path: str
    readiness_status: str | None
    acceptance_status: str | None
    runner_status: str | None
    ledger_status: str | None
    metrics_status: str | None
    report_status: str | None
    ledger_trade_count: int
    metric_trade_count: int
    winning_trade_count: int
    losing_trade_count: int
    flat_trade_count: int
    ce_trade_count: int
    pe_trade_count: int
    win_rate_percent: float
    loss_rate_percent: float
    flat_rate_percent: float
    simulated_gross_result_total: float
    starting_equity_reference: float
    final_equity_reference: float
    max_drawdown_reference: float
    max_drawdown_percent_reference: float
    expectancy_per_trade_reference: float
    largest_winning_trade_result: float
    largest_losing_trade_result: float
    safe_broker_disabled_count: int
    safe_orders_not_created_count: int
    safe_real_money_not_used_count: int
    unsafe_broker_mode_count: int
    unsafe_order_mode_count: int
    unsafe_money_mode_count: int
    long_ce_buy_count: int
    short_pe_buy_count: int
    invalid_direction_mapping_count: int
    target_exit_count: int
    stop_loss_exit_count: int
    max_holding_exit_count: int
    other_exit_count: int
    issues: list[ResultReviewIssue]
    checklist: list[ResultReviewChecklistItem]


def safety_notice() -> str:
    return (
        "Paper/simulation result review only. This review reads recorded-data "
        "paper backtest evidence. It does not connect to brokers, request live "
        "market data, place real orders, use real money, or prove profitability."
    )


def no_profitability_claim_notice() -> str:
    return (
        "This is not a profitability claim. Reported totals, equity references, "
        "drawdown references, win rate, and expectancy are paper/simulation "
        "reference values only."
    )


def deterministic_pricing_warning() -> str:
    return (
        "Important assumption warning: option prices in this run are deterministic "
        "paper reference prices derived by the simulator, not real option-chain "
        "fills, not live quotes, and not broker executions. Treat results as "
        "pipeline evidence and tuning input, not trading performance proof."
    )


def _issue(severity: str, code: str, count: int, message: str) -> ResultReviewIssue:
    return ResultReviewIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status_from_issues(issues: Sequence[ResultReviewIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _load_json(path: Path, report_name: str) -> tuple[Mapping[str, Any] | None, list[ResultReviewIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                f"{report_name}_missing",
                1,
                f"Required {report_name} JSON missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                f"{report_name}_invalid_json",
                1,
                f"Required {report_name} JSON is invalid: {path}; {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                f"{report_name}_invalid_shape",
                1,
                f"Required {report_name} JSON is not an object: {path}",
            )
        ]

    return payload, []


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0
        try:
            return int(float(text))
        except ValueError:
            return 0
    return 0


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0
    return 0.0


def _status(payload: Mapping[str, Any] | None) -> str | None:
    if payload is None:
        return None
    value = payload.get("status")
    if value is None:
        return None
    return str(value).strip().lower()


def _ready(payload: Mapping[str, Any] | None, key: str) -> bool:
    if payload is None:
        return False
    return bool(payload.get(key))


def _rows(payload: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if payload is None:
        return []
    rows = payload.get("ledger_rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, Mapping)]


def _count_rows(rows: Sequence[Mapping[str, Any]], key: str, expected: str) -> int:
    return sum(1 for row in rows if str(row.get(key) or "") == expected)


def _count_direction_mapping(rows: Sequence[Mapping[str, Any]], decision: str, option_type: str) -> int:
    return sum(
        1
        for row in rows
        if str(row.get("decision") or "") == decision
        and str(row.get("option_type") or "") == option_type
        and str(row.get("option_action") or "") == "BUY"
    )


def _count_exit(rows: Sequence[Mapping[str, Any]], reason: str) -> int:
    return sum(1 for row in rows if str(row.get("exit_reason") or "") == reason)


def _invalid_direction_mapping_count(rows: Sequence[Mapping[str, Any]]) -> int:
    invalid = 0
    for row in rows:
        decision = str(row.get("decision") or "")
        option_type = str(row.get("option_type") or "")
        action = str(row.get("option_action") or "")

        if decision == "LONG" and not (option_type == "CE" and action == "BUY"):
            invalid += 1
        elif decision == "SHORT" and not (option_type == "PE" and action == "BUY"):
            invalid += 1
    return invalid


def _build_checklist(report: ResultReviewReport) -> list[ResultReviewChecklistItem]:
    return [
        ResultReviewChecklistItem(
            item="Recorded backtest readiness gate",
            status="pass" if report.readiness_status == "pass" else "fail",
            detail=f"status={report.readiness_status}",
        ),
        ResultReviewChecklistItem(
            item="Backtest acceptance gate",
            status="pass" if report.acceptance_status == "pass" else "fail",
            detail=f"status={report.acceptance_status}",
        ),
        ResultReviewChecklistItem(
            item="One-command runner",
            status="pass" if report.runner_status == "pass" else "fail",
            detail=f"status={report.runner_status}",
        ),
        ResultReviewChecklistItem(
            item="Trade ledger",
            status="pass" if report.ledger_status == "pass" else "fail",
            detail=f"status={report.ledger_status}, trades={report.ledger_trade_count}",
        ),
        ResultReviewChecklistItem(
            item="Metrics engine",
            status="pass" if report.metrics_status == "pass" else "fail",
            detail=f"status={report.metrics_status}, metric_trades={report.metric_trade_count}",
        ),
        ResultReviewChecklistItem(
            item="Paper safety fields",
            status="pass"
            if (
                report.unsafe_broker_mode_count == 0
                and report.unsafe_order_mode_count == 0
                and report.unsafe_money_mode_count == 0
            )
            else "fail",
            detail=(
                "unsafe_broker="
                f"{report.unsafe_broker_mode_count}, unsafe_orders={report.unsafe_order_mode_count}, "
                f"unsafe_money={report.unsafe_money_mode_count}"
            ),
        ),
        ResultReviewChecklistItem(
            item="Option-buy direction mapping",
            status="pass" if report.invalid_direction_mapping_count == 0 else "fail",
            detail=(
                f"LONG->CE BUY={report.long_ce_buy_count}, "
                f"SHORT->PE BUY={report.short_pe_buy_count}, "
                f"invalid={report.invalid_direction_mapping_count}"
            ),
        ),
        ResultReviewChecklistItem(
            item="Profitability claim guard",
            status="pass",
            detail="Report explicitly says paper/simulation only and not profitability proof.",
        ),
    ]


def build_result_review_report(
    *,
    readiness_path: Path = DEFAULT_READINESS_PATH,
    acceptance_path: Path = DEFAULT_ACCEPTANCE_PATH,
    runner_path: Path = DEFAULT_RUNNER_PATH,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    metrics_path: Path = DEFAULT_METRICS_PATH,
    backtest_report_path: Path = DEFAULT_REPORT_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    min_trades: int = 1,
) -> ResultReviewReport:
    issues: list[ResultReviewIssue] = []

    readiness, loaded_issues = _load_json(readiness_path, "readiness_report")
    issues.extend(loaded_issues)

    acceptance, loaded_issues = _load_json(acceptance_path, "acceptance_report")
    issues.extend(loaded_issues)

    runner, loaded_issues = _load_json(runner_path, "runner_report")
    issues.extend(loaded_issues)

    ledger, loaded_issues = _load_json(ledger_path, "ledger_report")
    issues.extend(loaded_issues)

    metrics, loaded_issues = _load_json(metrics_path, "metrics_report")
    issues.extend(loaded_issues)

    backtest_report, loaded_issues = _load_json(backtest_report_path, "backtest_report")
    issues.extend(loaded_issues)

    readiness_status = _status(readiness)
    acceptance_status = _status(acceptance)
    runner_status = _status(runner)
    ledger_status = _status(ledger)
    metrics_status = _status(metrics)
    report_status = _status(backtest_report)

    expected_pass = {
        "readiness_report": readiness_status,
        "acceptance_report": acceptance_status,
        "runner_report": runner_status,
        "ledger_report": ledger_status,
        "metrics_report": metrics_status,
        "backtest_report": report_status,
    }

    for name, status in expected_pass.items():
        if status != "pass":
            issues.append(
                _issue(
                    "fail",
                    f"{name}_not_pass",
                    1,
                    f"{name} status is not pass: {status or 'missing'}.",
                )
            )

    if not _ready(readiness, "ready_for_future_v1_testing_release_gate"):
        issues.append(
            _issue(
                "fail",
                "readiness_gate_not_ready",
                1,
                "Backtest readiness gate is not ready for future v1 testing release gate.",
            )
        )

    rows = _rows(ledger)

    ledger_trade_count = _as_int(ledger.get("ledger_trade_count") if ledger else None)
    metric_trade_count = _as_int(metrics.get("metric_trade_count") if metrics else None)
    winning_trade_count = _as_int(metrics.get("winning_trade_count") if metrics else None)
    losing_trade_count = _as_int(metrics.get("losing_trade_count") if metrics else None)
    flat_trade_count = _as_int(metrics.get("flat_trade_count") if metrics else None)

    ce_trade_count = _as_int(ledger.get("ce_trade_count") if ledger else None)
    pe_trade_count = _as_int(ledger.get("pe_trade_count") if ledger else None)

    if ledger_trade_count < min_trades:
        issues.append(
            _issue(
                "fail",
                "insufficient_ledger_trades",
                max(min_trades - ledger_trade_count, 1),
                f"Ledger trade count below minimum. Required={min_trades}, actual={ledger_trade_count}.",
            )
        )

    if metric_trade_count < min_trades:
        issues.append(
            _issue(
                "fail",
                "insufficient_metric_trades",
                max(min_trades - metric_trade_count, 1),
                f"Metric trade count below minimum. Required={min_trades}, actual={metric_trade_count}.",
            )
        )

    if rows and ledger_trade_count != len(rows):
        issues.append(
            _issue(
                "warn",
                "ledger_row_count_mismatch",
                abs(ledger_trade_count - len(rows)),
                f"Ledger trade count {ledger_trade_count} differs from ledger row count {len(rows)}.",
            )
        )

    safe_broker_disabled_count = _count_rows(rows, "broker_execution_mode", SAFE_BROKER_MODE)
    safe_orders_not_created_count = _count_rows(rows, "order_mode", SAFE_ORDER_MODE)
    safe_real_money_not_used_count = _count_rows(rows, "money_mode", SAFE_MONEY_MODE)

    unsafe_broker_mode_count = max(len(rows) - safe_broker_disabled_count, 0)
    unsafe_order_mode_count = max(len(rows) - safe_orders_not_created_count, 0)
    unsafe_money_mode_count = max(len(rows) - safe_real_money_not_used_count, 0)

    if unsafe_broker_mode_count:
        issues.append(
            _issue(
                "fail",
                "unsafe_broker_mode_rows",
                unsafe_broker_mode_count,
                f"{unsafe_broker_mode_count} ledger rows are not broker_disabled.",
            )
        )

    if unsafe_order_mode_count:
        issues.append(
            _issue(
                "fail",
                "unsafe_order_mode_rows",
                unsafe_order_mode_count,
                f"{unsafe_order_mode_count} ledger rows are not orders_not_created.",
            )
        )

    if unsafe_money_mode_count:
        issues.append(
            _issue(
                "fail",
                "unsafe_money_mode_rows",
                unsafe_money_mode_count,
                f"{unsafe_money_mode_count} ledger rows are not real_money_not_used.",
            )
        )

    invalid_direction_mapping_count = _invalid_direction_mapping_count(rows)

    if invalid_direction_mapping_count:
        issues.append(
            _issue(
                "fail",
                "invalid_option_buy_direction_mapping",
                invalid_direction_mapping_count,
                (
                    f"{invalid_direction_mapping_count} rows violate LONG->CE BUY "
                    "or SHORT->PE BUY mapping."
                ),
            )
        )

    report_stub = ResultReviewReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status="fail",
        accepted_for_future_tuning_review=False,
        output_directory=str(output_dir),
        safety_notice=safety_notice(),
        no_profitability_claim_notice=no_profitability_claim_notice(),
        deterministic_pricing_warning=deterministic_pricing_warning(),
        readiness_report_path=str(readiness_path),
        acceptance_report_path=str(acceptance_path),
        runner_report_path=str(runner_path),
        ledger_report_path=str(ledger_path),
        metrics_report_path=str(metrics_path),
        backtest_report_path=str(backtest_report_path),
        readiness_status=readiness_status,
        acceptance_status=acceptance_status,
        runner_status=runner_status,
        ledger_status=ledger_status,
        metrics_status=metrics_status,
        report_status=report_status,
        ledger_trade_count=ledger_trade_count,
        metric_trade_count=metric_trade_count,
        winning_trade_count=winning_trade_count,
        losing_trade_count=losing_trade_count,
        flat_trade_count=flat_trade_count,
        ce_trade_count=ce_trade_count,
        pe_trade_count=pe_trade_count,
        win_rate_percent=_as_float(metrics.get("win_rate_percent") if metrics else None),
        loss_rate_percent=_as_float(metrics.get("loss_rate_percent") if metrics else None),
        flat_rate_percent=_as_float(metrics.get("flat_rate_percent") if metrics else None),
        simulated_gross_result_total=_as_float(
            metrics.get("simulated_gross_result_total") if metrics else None
        ),
        starting_equity_reference=_as_float(
            metrics.get("starting_equity_reference") if metrics else None
        ),
        final_equity_reference=_as_float(
            metrics.get("final_equity_reference") if metrics else None
        ),
        max_drawdown_reference=_as_float(
            metrics.get("max_drawdown_reference") if metrics else None
        ),
        max_drawdown_percent_reference=_as_float(
            metrics.get("max_drawdown_percent_reference") if metrics else None
        ),
        expectancy_per_trade_reference=_as_float(
            metrics.get("expectancy_per_trade_reference") if metrics else None
        ),
        largest_winning_trade_result=_as_float(
            metrics.get("largest_winning_trade_result") if metrics else None
        ),
        largest_losing_trade_result=_as_float(
            metrics.get("largest_losing_trade_result") if metrics else None
        ),
        safe_broker_disabled_count=safe_broker_disabled_count,
        safe_orders_not_created_count=safe_orders_not_created_count,
        safe_real_money_not_used_count=safe_real_money_not_used_count,
        unsafe_broker_mode_count=unsafe_broker_mode_count,
        unsafe_order_mode_count=unsafe_order_mode_count,
        unsafe_money_mode_count=unsafe_money_mode_count,
        long_ce_buy_count=_count_direction_mapping(rows, "LONG", "CE"),
        short_pe_buy_count=_count_direction_mapping(rows, "SHORT", "PE"),
        invalid_direction_mapping_count=invalid_direction_mapping_count,
        target_exit_count=_count_exit(rows, "target_points_reached"),
        stop_loss_exit_count=_count_exit(rows, "stop_loss_points_reached"),
        max_holding_exit_count=_count_exit(rows, "max_holding_bars_reached"),
        other_exit_count=sum(
            1
            for row in rows
            if str(row.get("exit_reason") or "")
            not in {
                "target_points_reached",
                "stop_loss_points_reached",
                "max_holding_bars_reached",
            }
        ),
        issues=issues,
        checklist=[],
    )

    checklist = _build_checklist(report_stub)
    final_issues = list(issues)

    for item in checklist:
        if item.status == "fail":
            final_issues.append(
                _issue(
                    "fail",
                    f"checklist_{item.item.lower().replace(' ', '_').replace('-', '_')}_failed",
                    1,
                    item.detail,
                )
            )

    status = _status_from_issues(final_issues)

    return ResultReviewReport(
        **{
            **asdict(report_stub),
            "status": status,
            "accepted_for_future_tuning_review": status in {"pass", "warn"},
            "issues": final_issues,
            "checklist": checklist,
        }
    )


def _report_to_dict(report: ResultReviewReport) -> dict[str, Any]:
    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["checklist"] = [asdict(item) for item in report.checklist]
    return data


def write_result_review_report(report: ResultReviewReport, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    review_json = output_dir / "real_recorded_backtest_result_review_pack.json"
    review_txt = output_dir / "real_recorded_backtest_result_review_pack.txt"
    checklist_csv = output_dir / "real_recorded_backtest_result_review_checklist.csv"
    summary_csv = output_dir / "real_recorded_backtest_result_review_summary.csv"
    manifest_json = output_dir / "manifest.json"

    review_json.write_text(
        json.dumps(_report_to_dict(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Real Recorded Backtest Result Review Pack",
        "",
        report.safety_notice,
        "",
        report.no_profitability_claim_notice,
        "",
        report.deterministic_pricing_warning,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        f"Accepted for future tuning review: {report.accepted_for_future_tuning_review}",
        "",
        "Pipeline Status:",
        f"- Readiness gate: {report.readiness_status}",
        f"- Acceptance gate: {report.acceptance_status}",
        f"- One-command runner: {report.runner_status}",
        f"- Ledger: {report.ledger_status}",
        f"- Metrics: {report.metrics_status}",
        f"- Report writer: {report.report_status}",
        "",
        "Paper Backtest Summary:",
        f"- Ledger trades: {report.ledger_trade_count}",
        f"- Metric trades: {report.metric_trade_count}",
        f"- CE BUY paper trades: {report.ce_trade_count}",
        f"- PE BUY paper trades: {report.pe_trade_count}",
        f"- Winning trades: {report.winning_trade_count}",
        f"- Losing trades: {report.losing_trade_count}",
        f"- Flat trades: {report.flat_trade_count}",
        f"- Win rate percent reference: {report.win_rate_percent}",
        f"- Simulated gross result total reference: {report.simulated_gross_result_total}",
        f"- Final equity reference: {report.final_equity_reference}",
        f"- Max drawdown percent reference: {report.max_drawdown_percent_reference}",
        "",
        "Exit Breakdown:",
        f"- Target exits: {report.target_exit_count}",
        f"- Stop loss exits: {report.stop_loss_exit_count}",
        f"- Max holding exits: {report.max_holding_exit_count}",
        f"- Other exits: {report.other_exit_count}",
        "",
        "Safety Counts:",
        f"- broker_disabled rows: {report.safe_broker_disabled_count}",
        f"- orders_not_created rows: {report.safe_orders_not_created_count}",
        f"- real_money_not_used rows: {report.safe_real_money_not_used_count}",
        f"- unsafe broker rows: {report.unsafe_broker_mode_count}",
        f"- unsafe order rows: {report.unsafe_order_mode_count}",
        f"- unsafe money rows: {report.unsafe_money_mode_count}",
        "",
        "Direction Mapping:",
        f"- LONG -> CE BUY rows: {report.long_ce_buy_count}",
        f"- SHORT -> PE BUY rows: {report.short_pe_buy_count}",
        f"- Invalid direction mapping rows: {report.invalid_direction_mapping_count}",
        "",
        "Checklist:",
    ]

    for item in report.checklist:
        lines.append(f"- {item.status.upper()} {item.item}: {item.detail}")

    lines.append("")
    lines.append("Issues:")

    if report.issues:
        for issue in report.issues:
            lines.append(f"- {issue.severity.upper()} {issue.code} ({issue.count}): {issue.message}")
    else:
        lines.append("- PASS: Review pack checks passed.")

    lines.extend(
        [
            "",
            "Decision:",
            (
                "- Ready for future tuning review: YES"
                if report.accepted_for_future_tuning_review
                else "- Ready for future tuning review: NO"
            ),
            "",
            "This is not a profitability claim.",
        ]
    )

    review_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with checklist_csv.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=["item", "status", "detail"])
        writer.writeheader()
        for item in report.checklist:
            writer.writerow(asdict(item))

    with summary_csv.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=[
                "status",
                "accepted_for_future_tuning_review",
                "ledger_trade_count",
                "metric_trade_count",
                "ce_trade_count",
                "pe_trade_count",
                "winning_trade_count",
                "losing_trade_count",
                "flat_trade_count",
                "win_rate_percent",
                "simulated_gross_result_total",
                "final_equity_reference",
                "max_drawdown_percent_reference",
                "profitability_claim_allowed",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "status": report.status,
                "accepted_for_future_tuning_review": report.accepted_for_future_tuning_review,
                "ledger_trade_count": report.ledger_trade_count,
                "metric_trade_count": report.metric_trade_count,
                "ce_trade_count": report.ce_trade_count,
                "pe_trade_count": report.pe_trade_count,
                "winning_trade_count": report.winning_trade_count,
                "losing_trade_count": report.losing_trade_count,
                "flat_trade_count": report.flat_trade_count,
                "win_rate_percent": report.win_rate_percent,
                "simulated_gross_result_total": report.simulated_gross_result_total,
                "final_equity_reference": report.final_equity_reference,
                "max_drawdown_percent_reference": report.max_drawdown_percent_reference,
                "profitability_claim_allowed": False,
            }
        )

    manifest = {
        "report_type": "real_recorded_backtest_result_review_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted_for_future_tuning_review": report.accepted_for_future_tuning_review,
        "profitability_claim_allowed": False,
        "safety_notice": report.safety_notice,
        "deterministic_pricing_warning": report.deterministic_pricing_warning,
        "outputs": {
            "review_json": str(review_json),
            "review_txt": str(review_txt),
            "checklist_csv": str(checklist_csv),
            "summary_csv": str(summary_csv),
            "manifest_json": str(manifest_json),
        },
    }

    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "review_json": review_json,
        "review_txt": review_txt,
        "checklist_csv": checklist_csv,
        "summary_csv": summary_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_result_review_report(
    *,
    readiness_path: Path = DEFAULT_READINESS_PATH,
    acceptance_path: Path = DEFAULT_ACCEPTANCE_PATH,
    runner_path: Path = DEFAULT_RUNNER_PATH,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    metrics_path: Path = DEFAULT_METRICS_PATH,
    backtest_report_path: Path = DEFAULT_REPORT_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    min_trades: int = 1,
) -> tuple[ResultReviewReport, dict[str, Path]]:
    report = build_result_review_report(
        readiness_path=readiness_path,
        acceptance_path=acceptance_path,
        runner_path=runner_path,
        ledger_path=ledger_path,
        metrics_path=metrics_path,
        backtest_report_path=backtest_report_path,
        output_dir=output_dir,
        min_trades=min_trades,
    )
    outputs = write_result_review_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a safe review pack for recorded-data paper backtest results."
    )
    parser.add_argument("--readiness", default=str(DEFAULT_READINESS_PATH))
    parser.add_argument("--acceptance", default=str(DEFAULT_ACCEPTANCE_PATH))
    parser.add_argument("--runner", default=str(DEFAULT_RUNNER_PATH))
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER_PATH))
    parser.add_argument("--metrics", default=str(DEFAULT_METRICS_PATH))
    parser.add_argument("--backtest-report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-trades", type=int, default=1)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_result_review_report(
        readiness_path=Path(args.readiness),
        acceptance_path=Path(args.acceptance),
        runner_path=Path(args.runner),
        ledger_path=Path(args.ledger),
        metrics_path=Path(args.metrics),
        backtest_report_path=Path(args.backtest_report),
        output_dir=Path(args.output_dir),
        min_trades=args.min_trades,
    )

    print("HQE real recorded backtest result review pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(report.deterministic_pricing_warning)
    print(f"Status: {report.status}")
    print(f"Accepted for future tuning review: {report.accepted_for_future_tuning_review}")
    print(f"Ledger trades: {report.ledger_trade_count}")
    print(f"Metric trades: {report.metric_trade_count}")
    print(f"Win rate reference: {report.win_rate_percent}")
    print(f"Simulated gross result reference: {report.simulated_gross_result_total}")
    print(f"Review report: {outputs['review_txt']}")
    print("This is not a profitability claim.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
