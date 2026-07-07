"""
Paper Tuning Candidate Readiness Pack

Creates a paper-only tuning candidate readiness pack from the recorded
backtest result review and assumption risk review.

This module does not change strategy logic, run optimization, approve live
trading, connect to brokers, use live data, place orders, use real money, or
claim profitability. It only defines safe future tuning lanes.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_OUTPUT_DIR = Path("reports/paper_trading/paper_tuning_candidate_readiness_pack")

DEFAULT_RESULT_REVIEW_PATH = Path(
    "reports/paper_trading/real_recorded_backtest_result_review_pack/"
    "real_recorded_backtest_result_review_pack.json"
)
DEFAULT_RISK_REVIEW_PATH = Path(
    "reports/paper_trading/backtest_assumption_risk_review_pack/"
    "backtest_assumption_risk_review_pack.json"
)

MANDATORY_CANDIDATE_IDS = {
    "option_reference_pricing_reality_check",
    "slippage_and_cost_sensitivity",
    "signal_cooldown_and_duplicate_filter",
    "exit_rule_sensitivity",
    "session_and_trade_frequency_filter",
    "multi_dataset_replay_validation",
}


@dataclass(frozen=True)
class TuningReadinessIssue:
    """One tuning-readiness issue."""

    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class TuningCandidate:
    """One paper-only tuning candidate lane."""

    candidate_id: str
    title: str
    priority: str
    status: str
    source_risk_category: str
    hypothesis: str
    paper_only_action: str
    acceptance_evidence_required: str
    blocked_live_usage_reason: str


@dataclass(frozen=True)
class TuningReadinessReport:
    """Paper tuning candidate readiness report."""

    generated_at_utc: str
    status: str
    accepted_for_future_paper_tuning_sprint: bool
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    optimization_executed: bool
    strategy_logic_changed: bool
    output_directory: str
    safety_notice: str
    no_profitability_claim_notice: str
    live_trading_rejection_notice: str
    result_review_path: str
    risk_review_path: str
    result_review_status: str | None
    risk_review_status: str | None
    result_review_accepted_for_future_tuning_review: bool
    risk_review_accepted_for_future_tuning_plan: bool
    ledger_trade_count: int
    metric_trade_count: int
    win_rate_percent: float
    simulated_gross_result_total: float
    max_drawdown_percent_reference: float
    high_risk_item_count: int
    medium_risk_item_count: int
    low_risk_item_count: int
    candidate_count: int
    high_priority_candidate_count: int
    medium_priority_candidate_count: int
    low_priority_candidate_count: int
    issues: list[TuningReadinessIssue]
    candidates: list[TuningCandidate]


def safety_notice() -> str:
    return (
        "Paper/simulation tuning readiness only. This pack defines future tuning "
        "candidate lanes from recorded-data paper backtest evidence. It does not "
        "change strategy logic, run optimization, connect to brokers, request live "
        "market data, place real orders, use real money, approve live trading, or "
        "prove profitability."
    )


def no_profitability_claim_notice() -> str:
    return (
        "This is not a profitability claim. Any simulated totals, win rate, "
        "drawdown, expectancy, or final equity references remain paper/simulation "
        "evidence only."
    )


def live_trading_rejection_notice() -> str:
    return (
        "Live trading and real-money usage remain blocked. Future work from this "
        "pack must stay paper-only until separate live-readiness, cost, slippage, "
        "risk, compliance, monitoring, and broker-safety gates exist and pass."
    )


def _issue(severity: str, code: str, count: int, message: str) -> TuningReadinessIssue:
    return TuningReadinessIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _candidate(
    *,
    candidate_id: str,
    title: str,
    priority: str,
    source_risk_category: str,
    hypothesis: str,
    paper_only_action: str,
    acceptance_evidence_required: str,
    blocked_live_usage_reason: str,
) -> TuningCandidate:
    return TuningCandidate(
        candidate_id=candidate_id,
        title=title,
        priority=priority,
        status="paper_candidate_ready",
        source_risk_category=source_risk_category,
        hypothesis=hypothesis,
        paper_only_action=paper_only_action,
        acceptance_evidence_required=acceptance_evidence_required,
        blocked_live_usage_reason=blocked_live_usage_reason,
    )


def _status_from_issues(issues: Sequence[TuningReadinessIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _load_json(path: Path, name: str) -> tuple[Mapping[str, Any] | None, list[TuningReadinessIssue]]:
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


def _risk_items(payload: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if payload is None:
        return []
    items = payload.get("risk_items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, Mapping)]


def _risk_categories(payload: Mapping[str, Any] | None) -> set[str]:
    return {str(item.get("category") or "") for item in _risk_items(payload)}


def _build_candidates(risk_review: Mapping[str, Any] | None) -> list[TuningCandidate]:
    categories = _risk_categories(risk_review)

    candidates: list[TuningCandidate] = [
        _candidate(
            candidate_id="option_reference_pricing_reality_check",
            title="Option reference pricing reality check",
            priority="high",
            source_risk_category="deterministic_option_reference_pricing",
            hypothesis=(
                "Replacing deterministic paper option reference prices with option-chain "
                "replay assumptions may materially change paper result quality."
            ),
            paper_only_action=(
                "Add an offline option reference pricing comparison or replay fixture. "
                "Keep broker/live data disabled."
            ),
            acceptance_evidence_required=(
                "Paper-only comparison report showing deterministic reference vs replayed "
                "option reference assumptions, with no profitability claim."
            ),
            blocked_live_usage_reason=(
                "Current option prices are deterministic references, not real option fills."
            ),
        ),
        _candidate(
            candidate_id="slippage_and_cost_sensitivity",
            title="Slippage and cost sensitivity",
            priority="high",
            source_risk_category="real_execution_absent",
            hypothesis=(
                "Transaction costs, spread, and slippage can reduce or reverse simulated "
                "paper reference results."
            ),
            paper_only_action=(
                "Run offline sensitivity bands for brokerage, taxes, spread, slippage, and "
                "unfilled exits using paper ledger rows only."
            ),
            acceptance_evidence_required=(
                "Cost sensitivity pack with multiple cost bands and pass/fail impact summary."
            ),
            blocked_live_usage_reason=(
                "No real execution, broker fill, bid/ask, or cost model is validated."
            ),
        ),
        _candidate(
            candidate_id="signal_cooldown_and_duplicate_filter",
            title="Signal cooldown and duplicate filter review",
            priority="high",
            source_risk_category="trade_frequency",
            hypothesis=(
                "Reducing duplicate or over-frequent trades may reduce noise and improve "
                "paper risk profile."
            ),
            paper_only_action=(
                "Evaluate candidate cooldown windows and duplicate-signal filters in recorded "
                "paper replay only."
            ),
            acceptance_evidence_required=(
                "Before/after paper-only ledger and metrics comparison with trade-count, "
                "drawdown, and no-profit-claim language."
            ),
            blocked_live_usage_reason=(
                "High trade frequency risk has not been validated against real costs or fills."
            ),
        ),
        _candidate(
            candidate_id="exit_rule_sensitivity",
            title="Exit rule sensitivity review",
            priority="high",
            source_risk_category="exit_rule_distribution",
            hypothesis=(
                "Target, stop, and max-holding settings materially affect paper outcomes and "
                "need sensitivity testing."
            ),
            paper_only_action=(
                "Run controlled offline sweeps for target points, stop points, and max holding "
                "bars without changing live/broker behavior."
            ),
            acceptance_evidence_required=(
                "Exit sensitivity report comparing distributions, drawdown, simulated total, "
                "and risk warnings."
            ),
            blocked_live_usage_reason=(
                "Exit assumptions are paper-only and not validated against real option fills."
            ),
        ),
        _candidate(
            candidate_id="session_and_trade_frequency_filter",
            title="Session and trade frequency filter review",
            priority="medium",
            source_risk_category="trade_frequency",
            hypothesis=(
                "Time-of-day/session filters may reduce low-quality paper trades and improve "
                "risk consistency."
            ),
            paper_only_action=(
                "Evaluate paper-only session windows and per-session trade caps using recorded data."
            ),
            acceptance_evidence_required=(
                "Session-filter comparison pack with candidate filter metrics and risk notes."
            ),
            blocked_live_usage_reason=(
                "Session behavior has not been tested across enough regimes for live use."
            ),
        ),
        _candidate(
            candidate_id="multi_dataset_replay_validation",
            title="Multi-dataset replay validation",
            priority="high",
            source_risk_category="single_recorded_dataset_scope",
            hypothesis=(
                "A single recorded dataset is insufficient; additional date ranges and regimes "
                "may expose instability."
            ),
            paper_only_action=(
                "Run the same paper replay chain across more recorded datasets and compare stability."
            ),
            acceptance_evidence_required=(
                "Multi-dataset comparison report with pass/fail gates and no-profitability-claim guard."
            ),
            blocked_live_usage_reason=(
                "Current evidence is not multi-period, multi-regime, or out-of-sample validated."
            ),
        ),
        _candidate(
            candidate_id="drawdown_guardrail_review",
            title="Drawdown guardrail review",
            priority="medium",
            source_risk_category="drawdown_reference",
            hypothesis=(
                "Paper drawdown reference may require guardrails before any future paper-forward work."
            ),
            paper_only_action=(
                "Define paper-only drawdown alert thresholds and stop-review rules for future tests."
            ),
            acceptance_evidence_required=(
                "Drawdown guardrail report with thresholds, trigger examples, and blocked-live notice."
            ),
            blocked_live_usage_reason=(
                "Drawdown is a simulated reference and not validated under real execution."
            ),
        ),
    ]

    if "option_buy_direction_mapping" not in categories:
        candidates.append(
            _candidate(
                candidate_id="option_buy_mapping_regression_guard",
                title="Option-buy mapping regression guard",
                priority="low",
                source_risk_category="option_buy_direction_mapping",
                hypothesis="Direction mapping must remain locked even when tuning filters change.",
                paper_only_action=(
                    "Keep regression tests ensuring LONG->CE BUY, SHORT->PE BUY, NEUTRAL->no trade."
                ),
                acceptance_evidence_required=(
                    "Mapping regression evidence showing no option selling, no futures, no real orders."
                ),
                blocked_live_usage_reason="Mapping guard is safety-only and not live approval.",
            )
        )

    return candidates


def _validate_candidates(candidates: Sequence[TuningCandidate]) -> list[TuningReadinessIssue]:
    issues: list[TuningReadinessIssue] = []

    candidate_ids = {candidate.candidate_id for candidate in candidates}
    missing = sorted(MANDATORY_CANDIDATE_IDS - candidate_ids)
    if missing:
        issues.append(
            _issue(
                "fail",
                "mandatory_candidates_missing",
                len(missing),
                "Mandatory tuning candidates missing: " + ", ".join(missing),
            )
        )

    live_blocking_missing = [
        candidate.candidate_id
        for candidate in candidates
        if not candidate.blocked_live_usage_reason.strip()
    ]
    if live_blocking_missing:
        issues.append(
            _issue(
                "fail",
                "candidate_live_blocking_reason_missing",
                len(live_blocking_missing),
                "Some candidates are missing live-blocking reasons.",
            )
        )

    non_paper_ready = [
        candidate.candidate_id
        for candidate in candidates
        if candidate.status != "paper_candidate_ready"
    ]
    if non_paper_ready:
        issues.append(
            _issue(
                "fail",
                "candidate_status_invalid",
                len(non_paper_ready),
                "Some candidates are not marked paper_candidate_ready.",
            )
        )

    return issues


def build_tuning_readiness_report(
    *,
    result_review_path: Path = DEFAULT_RESULT_REVIEW_PATH,
    risk_review_path: Path = DEFAULT_RISK_REVIEW_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    min_candidates: int = 6,
) -> TuningReadinessReport:
    issues: list[TuningReadinessIssue] = []

    result_review, loaded_issues = _load_json(result_review_path, "result_review")
    issues.extend(loaded_issues)

    risk_review, loaded_issues = _load_json(risk_review_path, "risk_review")
    issues.extend(loaded_issues)

    result_review_status = _status(result_review)
    risk_review_status = _status(risk_review)

    if result_review_status != "pass":
        issues.append(
            _issue(
                "fail",
                "result_review_not_pass",
                1,
                f"Result review status is not pass: {result_review_status or 'missing'}.",
            )
        )

    if risk_review_status != "pass":
        issues.append(
            _issue(
                "fail",
                "risk_review_not_pass",
                1,
                f"Risk review status is not pass: {risk_review_status or 'missing'}.",
            )
        )

    result_accepted = bool(
        result_review.get("accepted_for_future_tuning_review")
        if result_review is not None
        else False
    )
    risk_accepted = bool(
        risk_review.get("accepted_for_future_tuning_plan")
        if risk_review is not None
        else False
    )

    if not result_accepted:
        issues.append(
            _issue(
                "fail",
                "result_review_not_accepted_for_tuning_review",
                1,
                "Result review is not accepted for future tuning review.",
            )
        )

    if not risk_accepted:
        issues.append(
            _issue(
                "fail",
                "risk_review_not_accepted_for_tuning_plan",
                1,
                "Risk review is not accepted for future tuning plan.",
            )
        )

    if bool(risk_review.get("ready_for_live_or_real_money") if risk_review is not None else False):
        issues.append(
            _issue(
                "fail",
                "risk_review_allows_live_or_real_money",
                1,
                "Risk review unexpectedly allows live or real-money usage.",
            )
        )

    if bool(risk_review.get("profitability_claim_allowed") if risk_review is not None else False):
        issues.append(
            _issue(
                "fail",
                "risk_review_allows_profitability_claim",
                1,
                "Risk review unexpectedly allows a profitability claim.",
            )
        )

    candidates = _build_candidates(risk_review)
    issues.extend(_validate_candidates(candidates))

    if len(candidates) < min_candidates:
        issues.append(
            _issue(
                "fail",
                "insufficient_tuning_candidates",
                max(min_candidates - len(candidates), 1),
                f"Tuning candidate count below minimum. Required={min_candidates}, actual={len(candidates)}.",
            )
        )

    status = _status_from_issues(issues)

    high_priority_candidate_count = sum(1 for candidate in candidates if candidate.priority == "high")
    medium_priority_candidate_count = sum(1 for candidate in candidates if candidate.priority == "medium")
    low_priority_candidate_count = sum(1 for candidate in candidates if candidate.priority == "low")

    return TuningReadinessReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        accepted_for_future_paper_tuning_sprint=status in {"pass", "warn"},
        ready_for_live_or_real_money=False,
        profitability_claim_allowed=False,
        optimization_executed=False,
        strategy_logic_changed=False,
        output_directory=str(output_dir),
        safety_notice=safety_notice(),
        no_profitability_claim_notice=no_profitability_claim_notice(),
        live_trading_rejection_notice=live_trading_rejection_notice(),
        result_review_path=str(result_review_path),
        risk_review_path=str(risk_review_path),
        result_review_status=result_review_status,
        risk_review_status=risk_review_status,
        result_review_accepted_for_future_tuning_review=result_accepted,
        risk_review_accepted_for_future_tuning_plan=risk_accepted,
        ledger_trade_count=_as_int((result_review or {}).get("ledger_trade_count")),
        metric_trade_count=_as_int((result_review or {}).get("metric_trade_count")),
        win_rate_percent=_as_float((result_review or {}).get("win_rate_percent")),
        simulated_gross_result_total=_as_float(
            (result_review or {}).get("simulated_gross_result_total")
        ),
        max_drawdown_percent_reference=_as_float(
            (result_review or {}).get("max_drawdown_percent_reference")
        ),
        high_risk_item_count=_as_int((risk_review or {}).get("high_risk_item_count")),
        medium_risk_item_count=_as_int((risk_review or {}).get("medium_risk_item_count")),
        low_risk_item_count=_as_int((risk_review or {}).get("low_risk_item_count")),
        candidate_count=len(candidates),
        high_priority_candidate_count=high_priority_candidate_count,
        medium_priority_candidate_count=medium_priority_candidate_count,
        low_priority_candidate_count=low_priority_candidate_count,
        issues=issues,
        candidates=candidates,
    )


def _report_to_dict(report: TuningReadinessReport) -> dict[str, Any]:
    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["candidates"] = [asdict(candidate) for candidate in report.candidates]
    return data


def write_tuning_readiness_report(
    report: TuningReadinessReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    review_json = output_dir / "paper_tuning_candidate_readiness_pack.json"
    review_txt = output_dir / "paper_tuning_candidate_readiness_pack.txt"
    candidates_csv = output_dir / "paper_tuning_candidates.csv"
    summary_csv = output_dir / "paper_tuning_candidate_readiness_summary.csv"
    manifest_json = output_dir / "manifest.json"

    review_json.write_text(
        json.dumps(_report_to_dict(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Paper Tuning Candidate Readiness Pack",
        "",
        report.safety_notice,
        "",
        report.no_profitability_claim_notice,
        "",
        report.live_trading_rejection_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        f"Accepted for future paper tuning sprint: {report.accepted_for_future_paper_tuning_sprint}",
        f"Ready for live or real money: {report.ready_for_live_or_real_money}",
        f"Profitability claim allowed: {report.profitability_claim_allowed}",
        f"Optimization executed: {report.optimization_executed}",
        f"Strategy logic changed: {report.strategy_logic_changed}",
        "",
        "Input Review Status:",
        f"- Result review: {report.result_review_status}",
        f"- Risk review: {report.risk_review_status}",
        f"- Result accepted for tuning review: {report.result_review_accepted_for_future_tuning_review}",
        f"- Risk accepted for tuning plan: {report.risk_review_accepted_for_future_tuning_plan}",
        "",
        "Paper Result Context:",
        f"- Ledger trades: {report.ledger_trade_count}",
        f"- Metric trades: {report.metric_trade_count}",
        f"- Win rate reference: {report.win_rate_percent}",
        f"- Simulated gross result reference: {report.simulated_gross_result_total}",
        f"- Max drawdown percent reference: {report.max_drawdown_percent_reference}",
        "",
        "Risk Context:",
        f"- High risk items: {report.high_risk_item_count}",
        f"- Medium risk items: {report.medium_risk_item_count}",
        f"- Low risk items: {report.low_risk_item_count}",
        "",
        "Candidate Counts:",
        f"- Total: {report.candidate_count}",
        f"- High priority: {report.high_priority_candidate_count}",
        f"- Medium priority: {report.medium_priority_candidate_count}",
        f"- Low priority: {report.low_priority_candidate_count}",
        "",
        "Candidates:",
    ]

    for candidate in report.candidates:
        lines.extend(
            [
                f"- [{candidate.priority.upper()}] {candidate.candidate_id}: {candidate.title}",
                f"  Source risk: {candidate.source_risk_category}",
                f"  Hypothesis: {candidate.hypothesis}",
                f"  Paper-only action: {candidate.paper_only_action}",
                f"  Acceptance evidence: {candidate.acceptance_evidence_required}",
                f"  Live blocked because: {candidate.blocked_live_usage_reason}",
            ]
        )

    lines.append("")
    lines.append("Issues:")

    if report.issues:
        for issue in report.issues:
            lines.append(f"- {issue.severity.upper()} {issue.code} ({issue.count}): {issue.message}")
    else:
        lines.append("- PASS: Paper tuning candidates are ready for a future paper-only tuning sprint.")

    lines.extend(
        [
            "",
            "Decision:",
            (
                "- Future paper tuning sprint may proceed under paper/simulation-only constraints."
                if report.accepted_for_future_paper_tuning_sprint
                else "- Future paper tuning sprint is blocked until issues are fixed."
            ),
            "- Live or real-money usage remains rejected.",
            "- Profitability claim remains forbidden.",
            "- No strategy logic was changed by this pack.",
            "- No optimization was executed by this pack.",
            "",
            "This is not a profitability claim.",
        ]
    )

    review_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with candidates_csv.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=[
                "candidate_id",
                "title",
                "priority",
                "status",
                "source_risk_category",
                "hypothesis",
                "paper_only_action",
                "acceptance_evidence_required",
                "blocked_live_usage_reason",
            ],
        )
        writer.writeheader()
        for candidate in report.candidates:
            writer.writerow(asdict(candidate))

    with summary_csv.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=[
                "status",
                "accepted_for_future_paper_tuning_sprint",
                "ready_for_live_or_real_money",
                "profitability_claim_allowed",
                "optimization_executed",
                "strategy_logic_changed",
                "candidate_count",
                "high_priority_candidate_count",
                "medium_priority_candidate_count",
                "low_priority_candidate_count",
                "ledger_trade_count",
                "win_rate_percent",
                "simulated_gross_result_total",
                "max_drawdown_percent_reference",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "status": report.status,
                "accepted_for_future_paper_tuning_sprint": report.accepted_for_future_paper_tuning_sprint,
                "ready_for_live_or_real_money": report.ready_for_live_or_real_money,
                "profitability_claim_allowed": report.profitability_claim_allowed,
                "optimization_executed": report.optimization_executed,
                "strategy_logic_changed": report.strategy_logic_changed,
                "candidate_count": report.candidate_count,
                "high_priority_candidate_count": report.high_priority_candidate_count,
                "medium_priority_candidate_count": report.medium_priority_candidate_count,
                "low_priority_candidate_count": report.low_priority_candidate_count,
                "ledger_trade_count": report.ledger_trade_count,
                "win_rate_percent": report.win_rate_percent,
                "simulated_gross_result_total": report.simulated_gross_result_total,
                "max_drawdown_percent_reference": report.max_drawdown_percent_reference,
            }
        )

    manifest = {
        "report_type": "paper_tuning_candidate_readiness_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted_for_future_paper_tuning_sprint": report.accepted_for_future_paper_tuning_sprint,
        "ready_for_live_or_real_money": report.ready_for_live_or_real_money,
        "profitability_claim_allowed": report.profitability_claim_allowed,
        "optimization_executed": report.optimization_executed,
        "strategy_logic_changed": report.strategy_logic_changed,
        "safety_notice": report.safety_notice,
        "outputs": {
            "review_json": str(review_json),
            "review_txt": str(review_txt),
            "candidates_csv": str(candidates_csv),
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
        "candidates_csv": candidates_csv,
        "summary_csv": summary_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_tuning_readiness_report(
    *,
    result_review_path: Path = DEFAULT_RESULT_REVIEW_PATH,
    risk_review_path: Path = DEFAULT_RISK_REVIEW_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    min_candidates: int = 6,
) -> tuple[TuningReadinessReport, dict[str, Path]]:
    report = build_tuning_readiness_report(
        result_review_path=result_review_path,
        risk_review_path=risk_review_path,
        output_dir=output_dir,
        min_candidates=min_candidates,
    )
    outputs = write_tuning_readiness_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper-only tuning candidate readiness pack."
    )
    parser.add_argument("--result-review", default=str(DEFAULT_RESULT_REVIEW_PATH))
    parser.add_argument("--risk-review", default=str(DEFAULT_RISK_REVIEW_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-candidates", type=int, default=6)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_tuning_readiness_report(
        result_review_path=Path(args.result_review),
        risk_review_path=Path(args.risk_review),
        output_dir=Path(args.output_dir),
        min_candidates=args.min_candidates,
    )

    print("HQE paper tuning candidate readiness pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(report.live_trading_rejection_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for future paper tuning sprint: {report.accepted_for_future_paper_tuning_sprint}")
    print(f"Ready for live or real money: {report.ready_for_live_or_real_money}")
    print(f"Profitability claim allowed: {report.profitability_claim_allowed}")
    print(f"Optimization executed: {report.optimization_executed}")
    print(f"Strategy logic changed: {report.strategy_logic_changed}")
    print(f"Candidate count: {report.candidate_count}")
    print(f"High priority candidates: {report.high_priority_candidate_count}")
    print(f"Readiness report: {outputs['review_txt']}")
    print("This is not a profitability claim.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
