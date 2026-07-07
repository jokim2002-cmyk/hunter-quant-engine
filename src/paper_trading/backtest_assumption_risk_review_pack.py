"""
Backtest Assumption Risk Review Pack

Builds a risk/assumption review over the real recorded-data paper backtest
result review pack.

This module intentionally does not approve live trading or claim profitability.
It labels deterministic option pricing, high trade frequency, single-dataset
scope, exit-rule assumptions, and missing real execution/slippage as review
risks before any future tuning work.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_OUTPUT_DIR = Path("reports/paper_trading/backtest_assumption_risk_review_pack")

DEFAULT_RESULT_REVIEW_PATH = Path(
    "reports/paper_trading/real_recorded_backtest_result_review_pack/"
    "real_recorded_backtest_result_review_pack.json"
)
DEFAULT_LEDGER_PATH = Path(
    "reports/paper_trading/recorded_data_backtest_trade_ledger/backtest_trade_ledger.json"
)
DEFAULT_METRICS_PATH = Path(
    "reports/paper_trading/recorded_data_backtest_metrics_engine/backtest_metrics.json"
)

HIGH_TRADE_FREQUENCY_RATIO = 0.75
HIGH_MAX_HOLDING_EXIT_RATIO = 0.50
LARGE_DRAWDOWN_REFERENCE_PERCENT = 10.0


@dataclass(frozen=True)
class AssumptionRiskIssue:
    """One risk review finding."""

    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class AssumptionRiskItem:
    """One assumption/risk row."""

    category: str
    risk_level: str
    status: str
    assumption: str
    evidence: str
    review_action: str


@dataclass(frozen=True)
class AssumptionRiskReport:
    """Backtest assumption risk review report."""

    generated_at_utc: str
    status: str
    accepted_for_future_tuning_plan: bool
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    output_directory: str
    safety_notice: str
    no_profitability_claim_notice: str
    live_trading_rejection_notice: str
    result_review_path: str
    ledger_path: str
    metrics_path: str
    result_review_status: str | None
    ledger_trade_count: int
    metric_trade_count: int
    ce_trade_count: int
    pe_trade_count: int
    winning_trade_count: int
    losing_trade_count: int
    flat_trade_count: int
    win_rate_percent: float
    simulated_gross_result_total: float
    final_equity_reference: float
    max_drawdown_percent_reference: float
    max_drawdown_reference: float
    expectancy_per_trade_reference: float
    target_exit_count: int
    stop_loss_exit_count: int
    max_holding_exit_count: int
    other_exit_count: int
    trade_frequency_reference_percent: float
    target_exit_percent: float
    stop_loss_exit_percent: float
    max_holding_exit_percent: float
    high_risk_item_count: int
    medium_risk_item_count: int
    low_risk_item_count: int
    issues: list[AssumptionRiskIssue]
    risk_items: list[AssumptionRiskItem]


def safety_notice() -> str:
    return (
        "Paper/simulation assumption review only. This pack reviews recorded-data "
        "paper backtest assumptions and risks. It does not connect to brokers, "
        "request live market data, place real orders, use real money, approve live "
        "trading, or prove profitability."
    )


def no_profitability_claim_notice() -> str:
    return (
        "This is not a profitability claim. Simulated totals, win rate, drawdown, "
        "expectancy, and final equity are paper/simulation reference values only."
    )


def live_trading_rejection_notice() -> str:
    return (
        "This review does not approve live trading, broker execution, real-money "
        "deployment, or production execution. Future work must remain paper-only "
        "until separate live-readiness, risk, slippage, cost, and compliance gates "
        "exist and pass."
    )


def _issue(severity: str, code: str, count: int, message: str) -> AssumptionRiskIssue:
    return AssumptionRiskIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _risk_item(
    *,
    category: str,
    risk_level: str,
    status: str,
    assumption: str,
    evidence: str,
    review_action: str,
) -> AssumptionRiskItem:
    return AssumptionRiskItem(
        category=category,
        risk_level=risk_level,
        status=status,
        assumption=assumption,
        evidence=evidence,
        review_action=review_action,
    )


def _status_from_issues(issues: Sequence[AssumptionRiskIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _load_json(path: Path, name: str) -> tuple[Mapping[str, Any] | None, list[AssumptionRiskIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                f"{name}_missing",
                1,
                f"Required {name} JSON missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                f"{name}_invalid_json",
                1,
                f"Required {name} JSON is invalid: {path}; {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                f"{name}_invalid_shape",
                1,
                f"Required {name} JSON is not an object: {path}",
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


def _rows(payload: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if payload is None:
        return []
    rows = payload.get("ledger_rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, Mapping)]


def _percent(part: int | float, total: int | float) -> float:
    if total <= 0:
        return 0.0
    return round((float(part) / float(total)) * 100.0, 10)


def _count_exit(rows: Sequence[Mapping[str, Any]], reason: str) -> int:
    return sum(1 for row in rows if str(row.get("exit_reason") or "") == reason)


def _build_risk_items(
    *,
    result_review: Mapping[str, Any] | None,
    rows: Sequence[Mapping[str, Any]],
    ledger_trade_count: int,
    metric_trade_count: int,
    ce_trade_count: int,
    pe_trade_count: int,
    win_rate_percent: float,
    simulated_gross_result_total: float,
    max_drawdown_percent_reference: float,
    target_exit_count: int,
    stop_loss_exit_count: int,
    max_holding_exit_count: int,
    other_exit_count: int,
    trade_frequency_reference_percent: float,
    target_exit_percent: float,
    stop_loss_exit_percent: float,
    max_holding_exit_percent: float,
) -> list[AssumptionRiskItem]:
    items: list[AssumptionRiskItem] = []

    deterministic_warning = ""
    if result_review is not None:
        deterministic_warning = str(result_review.get("deterministic_pricing_warning") or "")

    items.append(
        _risk_item(
            category="deterministic_option_reference_pricing",
            risk_level="high",
            status="review_required",
            assumption=(
                "Option entry/exit prices are deterministic paper reference prices, "
                "not real option-chain fills."
            ),
            evidence=deterministic_warning
            or "Result review warning was unavailable, so deterministic pricing must be assumed as a high risk.",
            review_action=(
                "Do not claim profitability. Before any live-readiness work, add real "
                "option-chain replay, bid/ask, slippage, spread, and cost modelling."
            ),
        )
    )

    items.append(
        _risk_item(
            category="real_execution_absent",
            risk_level="high",
            status="blocked_for_live_use",
            assumption="No real broker execution, no live quote request, and no real orders are used.",
            evidence="Paper-only ledger rows must remain broker_disabled, orders_not_created, real_money_not_used.",
            review_action=(
                "Keep output as pipeline evidence only. Real execution requires separate "
                "broker, compliance, risk, kill-switch, and paper-forward gates."
            ),
        )
    )

    trade_frequency_level = "high" if trade_frequency_reference_percent >= HIGH_TRADE_FREQUENCY_RATIO * 100 else "medium"
    items.append(
        _risk_item(
            category="trade_frequency",
            risk_level=trade_frequency_level,
            status="review_required",
            assumption="The strategy/paper adapter may generate very frequent trades.",
            evidence=(
                f"Ledger trades={ledger_trade_count}, metric trades={metric_trade_count}, "
                f"reference frequency={trade_frequency_reference_percent}%."
            ),
            review_action=(
                "Review overtrading risk, duplicate-signal filtering, cooldown rules, "
                "session filters, and transaction-cost sensitivity before tuning acceptance."
            ),
        )
    )

    max_holding_level = "high" if max_holding_exit_percent >= HIGH_MAX_HOLDING_EXIT_RATIO * 100 else "medium"
    items.append(
        _risk_item(
            category="exit_rule_distribution",
            risk_level=max_holding_level,
            status="review_required",
            assumption="A large share of trades may exit by max-holding rather than target/stop.",
            evidence=(
                f"target={target_exit_count} ({target_exit_percent}%), "
                f"stop_loss={stop_loss_exit_count} ({stop_loss_exit_percent}%), "
                f"max_holding={max_holding_exit_count} ({max_holding_exit_percent}%), "
                f"other={other_exit_count}."
            ),
            review_action=(
                "Review target/stop/max-holding assumptions, holding window, and whether "
                "exit logic is realistic for option-buy execution."
            ),
        )
    )

    drawdown_level = "high" if max_drawdown_percent_reference >= LARGE_DRAWDOWN_REFERENCE_PERCENT else "medium"
    items.append(
        _risk_item(
            category="drawdown_reference",
            risk_level=drawdown_level,
            status="review_required",
            assumption="Drawdown is only a paper reference based on simulated ledger values.",
            evidence=f"max_drawdown_percent_reference={max_drawdown_percent_reference}%.",
            review_action=(
                "Use as risk evidence only. Add costs, slippage, option spread, and "
                "walk-forward validation before tuning acceptance."
            ),
        )
    )

    items.append(
        _risk_item(
            category="single_recorded_dataset_scope",
            risk_level="high",
            status="review_required",
            assumption="Result is based on the currently available recorded dataset scope.",
            evidence=(
                "The review uses the latest recorded replay outputs. It is not multi-market, "
                "multi-year, or walk-forward validated evidence."
            ),
            review_action=(
                "Run additional datasets, date ranges, market regimes, and out-of-sample "
                "replays before treating the result as robust."
            ),
        )
    )

    items.append(
        _risk_item(
            category="paper_result_interpretation",
            risk_level="high",
            status="profitability_claim_forbidden",
            assumption="Positive simulated totals are paper references only.",
            evidence=(
                f"simulated_gross_result_total={simulated_gross_result_total}, "
                f"win_rate_reference={win_rate_percent}%."
            ),
            review_action=(
                "Do not market, publish, or use the result as a profitability claim. "
                "Only use it to guide controlled paper-only tuning review."
            ),
        )
    )

    items.append(
        _risk_item(
            category="option_buy_direction_mapping",
            risk_level="low",
            status="passed" if ce_trade_count + pe_trade_count == ledger_trade_count else "review_required",
            assumption="LONG maps to CE BUY and SHORT maps to PE BUY only.",
            evidence=f"CE BUY count={ce_trade_count}, PE BUY count={pe_trade_count}, ledger trades={ledger_trade_count}.",
            review_action="Keep direction mapping locked. Do not add option selling or futures execution.",
        )
    )

    return items


def build_assumption_risk_report(
    *,
    result_review_path: Path = DEFAULT_RESULT_REVIEW_PATH,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    metrics_path: Path = DEFAULT_METRICS_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    min_trades: int = 1,
) -> AssumptionRiskReport:
    issues: list[AssumptionRiskIssue] = []

    result_review, loaded_issues = _load_json(result_review_path, "result_review")
    issues.extend(loaded_issues)

    ledger, loaded_issues = _load_json(ledger_path, "ledger")
    issues.extend(loaded_issues)

    metrics, loaded_issues = _load_json(metrics_path, "metrics")
    issues.extend(loaded_issues)

    result_review_status = _status(result_review)

    if result_review_status != "pass":
        issues.append(
            _issue(
                "fail",
                "result_review_not_pass",
                1,
                f"Result review status is not pass: {result_review_status or 'missing'}.",
            )
        )

    ledger_trade_count = _as_int(
        (result_review or {}).get("ledger_trade_count")
        if result_review is not None
        else (ledger or {}).get("ledger_trade_count")
    )
    metric_trade_count = _as_int(
        (result_review or {}).get("metric_trade_count")
        if result_review is not None
        else (metrics or {}).get("metric_trade_count")
    )

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

    rows = _rows(ledger)

    winning_trade_count = _as_int((result_review or {}).get("winning_trade_count"))
    losing_trade_count = _as_int((result_review or {}).get("losing_trade_count"))
    flat_trade_count = _as_int((result_review or {}).get("flat_trade_count"))
    ce_trade_count = _as_int((result_review or {}).get("ce_trade_count"))
    pe_trade_count = _as_int((result_review or {}).get("pe_trade_count"))

    win_rate_percent = _as_float((result_review or {}).get("win_rate_percent"))
    simulated_gross_result_total = _as_float(
        (result_review or {}).get("simulated_gross_result_total")
    )
    final_equity_reference = _as_float((result_review or {}).get("final_equity_reference"))
    max_drawdown_percent_reference = _as_float(
        (result_review or {}).get("max_drawdown_percent_reference")
    )
    max_drawdown_reference = _as_float((result_review or {}).get("max_drawdown_reference"))
    expectancy_per_trade_reference = _as_float(
        (result_review or {}).get("expectancy_per_trade_reference")
    )

    target_exit_count = _as_int((result_review or {}).get("target_exit_count")) or _count_exit(
        rows, "target_points_reached"
    )
    stop_loss_exit_count = _as_int((result_review or {}).get("stop_loss_exit_count")) or _count_exit(
        rows, "stop_loss_points_reached"
    )
    max_holding_exit_count = _as_int(
        (result_review or {}).get("max_holding_exit_count")
    ) or _count_exit(rows, "max_holding_bars_reached")
    other_exit_count = _as_int((result_review or {}).get("other_exit_count"))

    total_exit_count = target_exit_count + stop_loss_exit_count + max_holding_exit_count + other_exit_count

    trade_frequency_reference_percent = _percent(ledger_trade_count, max(len(rows), ledger_trade_count))
    target_exit_percent = _percent(target_exit_count, total_exit_count)
    stop_loss_exit_percent = _percent(stop_loss_exit_count, total_exit_count)
    max_holding_exit_percent = _percent(max_holding_exit_count, total_exit_count)

    risk_items = _build_risk_items(
        result_review=result_review,
        rows=rows,
        ledger_trade_count=ledger_trade_count,
        metric_trade_count=metric_trade_count,
        ce_trade_count=ce_trade_count,
        pe_trade_count=pe_trade_count,
        win_rate_percent=win_rate_percent,
        simulated_gross_result_total=simulated_gross_result_total,
        max_drawdown_percent_reference=max_drawdown_percent_reference,
        target_exit_count=target_exit_count,
        stop_loss_exit_count=stop_loss_exit_count,
        max_holding_exit_count=max_holding_exit_count,
        other_exit_count=other_exit_count,
        trade_frequency_reference_percent=trade_frequency_reference_percent,
        target_exit_percent=target_exit_percent,
        stop_loss_exit_percent=stop_loss_exit_percent,
        max_holding_exit_percent=max_holding_exit_percent,
    )

    high_risk_item_count = sum(1 for item in risk_items if item.risk_level == "high")
    medium_risk_item_count = sum(1 for item in risk_items if item.risk_level == "medium")
    low_risk_item_count = sum(1 for item in risk_items if item.risk_level == "low")

    if not risk_items:
        issues.append(
            _issue(
                "fail",
                "no_risk_items_created",
                1,
                "No assumption risk items were created.",
            )
        )

    status = _status_from_issues(issues)

    return AssumptionRiskReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        accepted_for_future_tuning_plan=status in {"pass", "warn"},
        ready_for_live_or_real_money=False,
        profitability_claim_allowed=False,
        output_directory=str(output_dir),
        safety_notice=safety_notice(),
        no_profitability_claim_notice=no_profitability_claim_notice(),
        live_trading_rejection_notice=live_trading_rejection_notice(),
        result_review_path=str(result_review_path),
        ledger_path=str(ledger_path),
        metrics_path=str(metrics_path),
        result_review_status=result_review_status,
        ledger_trade_count=ledger_trade_count,
        metric_trade_count=metric_trade_count,
        ce_trade_count=ce_trade_count,
        pe_trade_count=pe_trade_count,
        winning_trade_count=winning_trade_count,
        losing_trade_count=losing_trade_count,
        flat_trade_count=flat_trade_count,
        win_rate_percent=win_rate_percent,
        simulated_gross_result_total=simulated_gross_result_total,
        final_equity_reference=final_equity_reference,
        max_drawdown_percent_reference=max_drawdown_percent_reference,
        max_drawdown_reference=max_drawdown_reference,
        expectancy_per_trade_reference=expectancy_per_trade_reference,
        target_exit_count=target_exit_count,
        stop_loss_exit_count=stop_loss_exit_count,
        max_holding_exit_count=max_holding_exit_count,
        other_exit_count=other_exit_count,
        trade_frequency_reference_percent=trade_frequency_reference_percent,
        target_exit_percent=target_exit_percent,
        stop_loss_exit_percent=stop_loss_exit_percent,
        max_holding_exit_percent=max_holding_exit_percent,
        high_risk_item_count=high_risk_item_count,
        medium_risk_item_count=medium_risk_item_count,
        low_risk_item_count=low_risk_item_count,
        issues=issues,
        risk_items=risk_items,
    )


def _report_to_dict(report: AssumptionRiskReport) -> dict[str, Any]:
    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["risk_items"] = [asdict(item) for item in report.risk_items]
    return data


def write_assumption_risk_report(
    report: AssumptionRiskReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    risk_json = output_dir / "backtest_assumption_risk_review_pack.json"
    risk_txt = output_dir / "backtest_assumption_risk_review_pack.txt"
    risk_csv = output_dir / "backtest_assumption_risk_items.csv"
    summary_csv = output_dir / "backtest_assumption_risk_summary.csv"
    manifest_json = output_dir / "manifest.json"

    risk_json.write_text(
        json.dumps(_report_to_dict(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Backtest Assumption Risk Review Pack",
        "",
        report.safety_notice,
        "",
        report.no_profitability_claim_notice,
        "",
        report.live_trading_rejection_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        f"Accepted for future tuning plan: {report.accepted_for_future_tuning_plan}",
        f"Ready for live or real money: {report.ready_for_live_or_real_money}",
        f"Profitability claim allowed: {report.profitability_claim_allowed}",
        "",
        "Paper Result Context:",
        f"- Result review status: {report.result_review_status}",
        f"- Ledger trades: {report.ledger_trade_count}",
        f"- Metric trades: {report.metric_trade_count}",
        f"- CE BUY paper trades: {report.ce_trade_count}",
        f"- PE BUY paper trades: {report.pe_trade_count}",
        f"- Winning trades: {report.winning_trade_count}",
        f"- Losing trades: {report.losing_trade_count}",
        f"- Flat trades: {report.flat_trade_count}",
        f"- Win rate reference: {report.win_rate_percent}",
        f"- Simulated gross result reference: {report.simulated_gross_result_total}",
        f"- Final equity reference: {report.final_equity_reference}",
        f"- Max drawdown percent reference: {report.max_drawdown_percent_reference}",
        "",
        "Exit Context:",
        f"- Target exits: {report.target_exit_count} ({report.target_exit_percent}%)",
        f"- Stop loss exits: {report.stop_loss_exit_count} ({report.stop_loss_exit_percent}%)",
        f"- Max holding exits: {report.max_holding_exit_count} ({report.max_holding_exit_percent}%)",
        f"- Other exits: {report.other_exit_count}",
        "",
        "Risk Item Counts:",
        f"- High: {report.high_risk_item_count}",
        f"- Medium: {report.medium_risk_item_count}",
        f"- Low: {report.low_risk_item_count}",
        "",
        "Risk Items:",
    ]

    for item in report.risk_items:
        lines.extend(
            [
                f"- [{item.risk_level.upper()}] {item.category}",
                f"  Status: {item.status}",
                f"  Assumption: {item.assumption}",
                f"  Evidence: {item.evidence}",
                f"  Review action: {item.review_action}",
            ]
        )

    lines.append("")
    lines.append("Issues:")

    if report.issues:
        for issue in report.issues:
            lines.append(f"- {issue.severity.upper()} {issue.code} ({issue.count}): {issue.message}")
    else:
        lines.append("- PASS: Assumption risk review completed without blocking issues.")

    lines.extend(
        [
            "",
            "Decision:",
            (
                "- Future tuning plan may proceed under paper/simulation-only constraints."
                if report.accepted_for_future_tuning_plan
                else "- Future tuning plan is blocked until issues are fixed."
            ),
            "- Live or real-money usage remains rejected.",
            "- Profitability claim remains forbidden.",
            "",
            "This is not a profitability claim.",
        ]
    )

    risk_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with risk_csv.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=[
                "category",
                "risk_level",
                "status",
                "assumption",
                "evidence",
                "review_action",
            ],
        )
        writer.writeheader()
        for item in report.risk_items:
            writer.writerow(asdict(item))

    with summary_csv.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=[
                "status",
                "accepted_for_future_tuning_plan",
                "ready_for_live_or_real_money",
                "profitability_claim_allowed",
                "ledger_trade_count",
                "metric_trade_count",
                "win_rate_percent",
                "simulated_gross_result_total",
                "max_drawdown_percent_reference",
                "high_risk_item_count",
                "medium_risk_item_count",
                "low_risk_item_count",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "status": report.status,
                "accepted_for_future_tuning_plan": report.accepted_for_future_tuning_plan,
                "ready_for_live_or_real_money": report.ready_for_live_or_real_money,
                "profitability_claim_allowed": report.profitability_claim_allowed,
                "ledger_trade_count": report.ledger_trade_count,
                "metric_trade_count": report.metric_trade_count,
                "win_rate_percent": report.win_rate_percent,
                "simulated_gross_result_total": report.simulated_gross_result_total,
                "max_drawdown_percent_reference": report.max_drawdown_percent_reference,
                "high_risk_item_count": report.high_risk_item_count,
                "medium_risk_item_count": report.medium_risk_item_count,
                "low_risk_item_count": report.low_risk_item_count,
            }
        )

    manifest = {
        "report_type": "backtest_assumption_risk_review_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted_for_future_tuning_plan": report.accepted_for_future_tuning_plan,
        "ready_for_live_or_real_money": report.ready_for_live_or_real_money,
        "profitability_claim_allowed": report.profitability_claim_allowed,
        "safety_notice": report.safety_notice,
        "outputs": {
            "risk_json": str(risk_json),
            "risk_txt": str(risk_txt),
            "risk_csv": str(risk_csv),
            "summary_csv": str(summary_csv),
            "manifest_json": str(manifest_json),
        },
    }

    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "risk_json": risk_json,
        "risk_txt": risk_txt,
        "risk_csv": risk_csv,
        "summary_csv": summary_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_assumption_risk_report(
    *,
    result_review_path: Path = DEFAULT_RESULT_REVIEW_PATH,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    metrics_path: Path = DEFAULT_METRICS_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    min_trades: int = 1,
) -> tuple[AssumptionRiskReport, dict[str, Path]]:
    report = build_assumption_risk_report(
        result_review_path=result_review_path,
        ledger_path=ledger_path,
        metrics_path=metrics_path,
        output_dir=output_dir,
        min_trades=min_trades,
    )
    outputs = write_assumption_risk_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a paper-only backtest assumption risk review pack."
    )
    parser.add_argument("--result-review", default=str(DEFAULT_RESULT_REVIEW_PATH))
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER_PATH))
    parser.add_argument("--metrics", default=str(DEFAULT_METRICS_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-trades", type=int, default=1)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_assumption_risk_report(
        result_review_path=Path(args.result_review),
        ledger_path=Path(args.ledger),
        metrics_path=Path(args.metrics),
        output_dir=Path(args.output_dir),
        min_trades=args.min_trades,
    )

    print("HQE backtest assumption risk review pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(report.live_trading_rejection_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for future tuning plan: {report.accepted_for_future_tuning_plan}")
    print(f"Ready for live or real money: {report.ready_for_live_or_real_money}")
    print(f"Profitability claim allowed: {report.profitability_claim_allowed}")
    print(f"High risk items: {report.high_risk_item_count}")
    print(f"Medium risk items: {report.medium_risk_item_count}")
    print(f"Low risk items: {report.low_risk_item_count}")
    print(f"Risk report: {outputs['risk_txt']}")
    print("This is not a profitability claim.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
