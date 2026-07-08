"""
Safe Paper Runner Review Criteria Pack

Module NNNNN continues Phase 10 by defining the safe review criteria for future
paper-runner evidence.

This pack does not execute a backtest, optimize parameters, change strategy
logic, connect to a broker, request live market data, place real orders, use
real money, approve live trading, or claim profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


REPORT_TYPE = "safe_paper_runner_review_criteria_pack"

DEFAULT_REVIEW_READINESS_INPUTS = (
    Path(
        "reports/paper_trading/safe_paper_runner_review_readiness_pack/"
        "safe_paper_runner_review_readiness_pack.json"
    ),
    Path("reports/paper_trading/safe_paper_runner_review_readiness_pack/manifest.json"),
)
DEFAULT_OUTPUT_DIR = Path("reports/paper_trading/safe_paper_runner_review_criteria_pack")

SAFE_CRITERIA_MODE = "criteria_only"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Safe paper-runner review criteria only. This pack does not run a backtest, "
    "connect to brokers, request live market data, place real orders, use real "
    "money, approve live trading, or prove profitability."
)
NO_PROFITABILITY_CLAIM_NOTICE = (
    "This is not a profitability claim. Review criteria describe how future "
    "paper/simulation evidence should be inspected, not whether it is profitable."
)


@dataclass(frozen=True)
class ReviewCriterion:
    """One locked criterion for future paper-runner evidence review."""

    criterion_id: str
    category: str
    title: str
    review_question: str
    required_evidence: str
    pass_rule: str
    blocked_claim: str
    status: str


@dataclass(frozen=True)
class ReviewCriteriaReport:
    """Serializable Phase 10 review-criteria evidence report."""

    report_type: str
    status: str
    generated_at_utc: str
    review_readiness_input_path: str
    review_readiness_found: bool
    review_readiness_status: str
    phase10_started: bool
    readiness_accepts_review_module: bool
    output_directory: str
    criterion_count: int
    locked_criterion_count: int
    accepted_for_future_safe_paper_runner_review_close: bool
    completed_total_after_module: int
    phase_10_pending_after_module: int
    criteria_mode: str
    runner_execution_enabled: bool
    backtest_executed: bool
    optimization_executed: bool
    strategy_logic_changed: bool
    broker_execution_mode: str
    live_data_mode: str
    real_order_mode: str
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    safety_notice: str
    no_profitability_claim_notice: str
    issues: list[dict[str, Any]]
    review_criteria: list[ReviewCriterion]


def _first_existing(paths: Sequence[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _load_json(path: Path, *, missing_code: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [
            {
                "code": missing_code,
                "severity": "warn",
                "message": f"Input report not found: {path}",
            }
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": f"{missing_code}_invalid_json",
                "severity": "fail",
                "message": str(exc),
            }
        ]

    if not isinstance(payload, dict):
        return None, [
            {
                "code": f"{missing_code}_not_object",
                "severity": "fail",
                "message": f"Input report is not a JSON object: {path}",
            }
        ]

    return payload, []


def _status(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "missing"
    return str(payload.get("status") or payload.get("report_status") or "unknown")


def _phase10_started(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    return any(
        bool(payload.get(key))
        for key in (
            "phase10_started",
            "phase_10_started",
            "safe_paper_runner_review_started",
        )
    )


def _accepts_review(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    return any(
        bool(payload.get(key))
        for key in (
            "accepted_for_future_safe_paper_runner_review_module",
            "accepted_for_future_safe_paper_runner_review_close",
            "accepted_for_future_phase10_safe_paper_runner_review",
        )
    )


def _unsafe_payload(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    return any(
        bool(payload.get(key))
        for key in (
            "ready_for_live_or_real_money",
            "profitability_claim_allowed",
            "runner_execution_enabled",
            "backtest_executed",
            "optimization_executed",
            "strategy_logic_changed",
            "broker_execution_enabled",
            "live_data_enabled",
            "real_order_enabled",
        )
    )


def _review_criteria() -> list[ReviewCriterion]:
    return [
        ReviewCriterion(
            "criteria-01",
            "input_boundary",
            "Recorded-data-only review",
            "Does the future evidence use only the recorded local dataset?",
            "dataset_path and recorded_data_only fields",
            "dataset_path points to local recorded data and live_data_mode remains recorded_data_only",
            "live-market-data-used",
            "locked",
        ),
        ReviewCriterion(
            "criteria-02",
            "execution_boundary",
            "Paper-only ledger review",
            "Does the future evidence contain only paper trade plans and no broker order payloads?",
            "paper ledger rows and safety manifest",
            "runner_execution_enabled=false and real_order_mode=real_orders_disabled",
            "broker-order-ready",
            "locked",
        ),
        ReviewCriterion(
            "criteria-03",
            "strategy_boundary",
            "No strategy mutation review",
            "Did the review leave strategy logic and optimization untouched?",
            "strategy_logic_changed and optimization_executed fields",
            "strategy_logic_changed=false and optimization_executed=false",
            "optimized-winning-strategy",
            "locked",
        ),
        ReviewCriterion(
            "criteria-04",
            "mapping_boundary",
            "Option-buy mapping review",
            "Are LONG, SHORT, and NEUTRAL mapped only to allowed paper intents?",
            "direction_to_option_intent mapping",
            "LONG=CE_BUY_PAPER, SHORT=PE_BUY_PAPER, NEUTRAL=NO_TRADE",
            "option-selling-or-futures-execution",
            "locked",
        ),
        ReviewCriterion(
            "criteria-05",
            "reporting_boundary",
            "No profitability claim review",
            "Does the future report avoid profitability, live-readiness, and real-money claims?",
            "no-profitability notice and manifest flags",
            "profitability_claim_allowed=false and ready_for_live_or_real_money=false",
            "profitable-or-live-ready-claim",
            "locked",
        ),
        ReviewCriterion(
            "criteria-06",
            "evidence_boundary",
            "Review output completeness",
            "Does the future review write inspectable JSON, text, CSV, and manifest files?",
            "outputs manifest",
            "report_json, report_txt, criteria_csv, and manifest_json exist",
            "console-only-review",
            "locked",
        ),
    ]


def build_review_criteria_report(
    *,
    review_readiness_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ReviewCriteriaReport:
    """Build the safe paper-runner review criteria without executing any runner."""

    input_path = review_readiness_input_path or _first_existing(DEFAULT_REVIEW_READINESS_INPUTS)
    payload, issues = _load_json(input_path, missing_code="review_readiness_input_missing")

    readiness_found = payload is not None
    readiness_status = _status(payload)
    phase10_started = _phase10_started(payload)
    readiness_accepts_review = _accepts_review(payload)

    if _unsafe_payload(payload):
        issues.append(
            {
                "code": "unsafe_review_readiness_input_boundary",
                "severity": "fail",
                "message": "Review readiness input allowed live/real money, runner execution, strategy change, optimization, backtest, or profitability claims.",
            }
        )

    if readiness_found and readiness_status != "pass":
        issues.append(
            {
                "code": "review_readiness_input_not_pass",
                "severity": "warn",
                "message": "Review readiness input exists but is not marked pass.",
            }
        )

    if readiness_found and not phase10_started:
        issues.append(
            {
                "code": "phase10_not_started",
                "severity": "warn",
                "message": "Review readiness input exists but does not explicitly start Phase 10.",
            }
        )

    if readiness_found and not readiness_accepts_review:
        issues.append(
            {
                "code": "readiness_not_accepted_for_review",
                "severity": "warn",
                "message": "Review readiness input exists but does not explicitly accept future review work.",
            }
        )

    failures = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "fail" if failures else "pass"
    criteria = _review_criteria()

    accepted = (
        status == "pass"
        and readiness_found
        and readiness_status == "pass"
        and phase10_started
        and readiness_accepts_review
        and all(criterion.status == "locked" for criterion in criteria)
    )

    return ReviewCriteriaReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        review_readiness_input_path=str(input_path),
        review_readiness_found=readiness_found,
        review_readiness_status=readiness_status,
        phase10_started=phase10_started,
        readiness_accepts_review_module=readiness_accepts_review,
        output_directory=str(output_dir),
        criterion_count=len(criteria),
        locked_criterion_count=sum(1 for criterion in criteria if criterion.status == "locked"),
        accepted_for_future_safe_paper_runner_review_close=accepted,
        completed_total_after_module=118,
        phase_10_pending_after_module=1,
        criteria_mode=SAFE_CRITERIA_MODE,
        runner_execution_enabled=False,
        backtest_executed=False,
        optimization_executed=False,
        strategy_logic_changed=False,
        broker_execution_mode=SAFE_BROKER_MODE,
        live_data_mode=SAFE_DATA_MODE,
        real_order_mode=SAFE_ORDER_MODE,
        ready_for_live_or_real_money=False,
        profitability_claim_allowed=False,
        safety_notice=SAFETY_NOTICE,
        no_profitability_claim_notice=NO_PROFITABILITY_CLAIM_NOTICE,
        issues=issues,
        review_criteria=criteria,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_criteria_csv(path: Path, criteria: list[ReviewCriterion]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "criterion_id",
                "category",
                "title",
                "review_question",
                "required_evidence",
                "pass_rule",
                "blocked_claim",
                "status",
            ],
        )
        writer.writeheader()
        for criterion in criteria:
            writer.writerow(asdict(criterion))


def _text_report(report: ReviewCriteriaReport) -> str:
    lines = [
        "HQE Safe Paper Runner Review Criteria Pack",
        "=" * 60,
        f"Status: {report.status}",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Review readiness input path: {report.review_readiness_input_path}",
        f"Review readiness found: {report.review_readiness_found}",
        f"Review readiness status: {report.review_readiness_status}",
        f"Phase 10 started: {report.phase10_started}",
        f"Readiness accepts review module: {report.readiness_accepts_review_module}",
        (
            "Accepted for future safe paper-runner review close: "
            f"{report.accepted_for_future_safe_paper_runner_review_close}"
        ),
        f"Criteria locked: {report.locked_criterion_count}/{report.criterion_count}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 10 pending after module: {report.phase_10_pending_after_module}",
        f"Criteria mode: {report.criteria_mode}",
        f"Runner execution enabled: {report.runner_execution_enabled}",
        f"Backtest executed: {report.backtest_executed}",
        f"Optimization executed: {report.optimization_executed}",
        f"Strategy logic changed: {report.strategy_logic_changed}",
        f"Broker execution mode: {report.broker_execution_mode}",
        f"Live data mode: {report.live_data_mode}",
        f"Real order mode: {report.real_order_mode}",
        f"Ready for live or real money: {report.ready_for_live_or_real_money}",
        f"Profitability claim allowed: {report.profitability_claim_allowed}",
        "",
        report.safety_notice,
        report.no_profitability_claim_notice,
        "",
        "Review criteria:",
    ]

    for criterion in report.review_criteria:
        lines.extend(
            [
                "",
                f"- {criterion.criterion_id}: {criterion.title}",
                f"  Category: {criterion.category}",
                f"  Question: {criterion.review_question}",
                f"  Required evidence: {criterion.required_evidence}",
                f"  Pass rule: {criterion.pass_rule}",
                f"  Blocked claim: {criterion.blocked_claim}",
                f"  Status: {criterion.status}",
            ]
        )

    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(
                f"- {issue.get('severity', 'unknown').upper()} {issue.get('code')}: {issue.get('message')}"
            )

    return "\n".join(lines) + "\n"


def write_review_criteria_pack(
    report: ReviewCriteriaReport,
    output_dir: Path,
) -> dict[str, str]:
    """Write JSON, text, CSV, and manifest evidence files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    criteria_csv = output_dir / "safe_paper_runner_review_criteria.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_criteria_csv(criteria_csv, report.review_criteria)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "criteria_csv": str(criteria_csv),
        "manifest_json": str(manifest_json),
    }

    _write_json(
        manifest_json,
        {
            "report_type": REPORT_TYPE,
            "status": report.status,
            "generated_at_utc": report.generated_at_utc,
            "accepted_for_future_safe_paper_runner_review_close": report.accepted_for_future_safe_paper_runner_review_close,
            "completed_total_after_module": report.completed_total_after_module,
            "phase_10_pending_after_module": report.phase_10_pending_after_module,
            "criteria_mode": report.criteria_mode,
            "runner_execution_enabled": report.runner_execution_enabled,
            "backtest_executed": report.backtest_executed,
            "optimization_executed": report.optimization_executed,
            "strategy_logic_changed": report.strategy_logic_changed,
            "broker_execution_mode": report.broker_execution_mode,
            "live_data_mode": report.live_data_mode,
            "real_order_mode": report.real_order_mode,
            "ready_for_live_or_real_money": report.ready_for_live_or_real_money,
            "profitability_claim_allowed": report.profitability_claim_allowed,
            "outputs": outputs,
        },
    )

    return outputs


def build_and_write_review_criteria_pack(
    *,
    review_readiness_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[ReviewCriteriaReport, dict[str, str]]:
    report = build_review_criteria_report(
        review_readiness_input_path=review_readiness_input_path,
        output_dir=output_dir,
    )
    outputs = write_review_criteria_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write the safe paper-runner review criteria pack."
    )
    parser.add_argument("--review-readiness-input", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_review_criteria_pack(
        review_readiness_input_path=Path(args.review_readiness_input)
        if args.review_readiness_input
        else None,
        output_dir=Path(args.output_dir),
    )

    print("HQE safe paper-runner review criteria pack completed.")
    print(f"Status: {report.status}")
    print(f"Review readiness found: {report.review_readiness_found}")
    print(f"Phase 10 started: {report.phase10_started}")
    print(
        "Accepted for future safe paper-runner review close: "
        f"{report.accepted_for_future_safe_paper_runner_review_close}"
    )
    print(f"Criteria locked: {report.locked_criterion_count}/{report.criterion_count}")
    print(f"Runner execution enabled: {report.runner_execution_enabled}")
    print(f"Backtest executed: {report.backtest_executed}")
    print(f"Strategy logic changed: {report.strategy_logic_changed}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 10 pending after module: {report.phase_10_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print(SAFETY_NOTICE)
    print(NO_PROFITABILITY_CLAIM_NOTICE)

    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
