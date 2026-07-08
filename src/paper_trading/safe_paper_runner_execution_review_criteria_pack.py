"""
Safe Paper Runner Execution Review Criteria Pack

Module QQQQQ continues Phase 11 by defining safe execution-review criteria for
future paper-runner evidence.

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


REPORT_TYPE = "safe_paper_runner_execution_review_criteria_pack"

DEFAULT_EXECUTION_REVIEW_READINESS_INPUTS = (
    Path(
        "reports/paper_trading/safe_paper_runner_execution_review_readiness_pack/"
        "safe_paper_runner_execution_review_readiness_pack.json"
    ),
    Path(
        "reports/paper_trading/safe_paper_runner_execution_review_readiness_pack/"
        "manifest.json"
    ),
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/safe_paper_runner_execution_review_criteria_pack"
)

SAFE_CRITERIA_MODE = "execution_review_criteria_only"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Safe paper-runner execution review criteria only. This pack does not run a "
    "backtest, connect to brokers, request live market data, place real orders, "
    "use real money, approve live trading, or prove profitability."
)
NO_PROFITABILITY_CLAIM_NOTICE = (
    "This is not a profitability claim. Execution-review criteria define how "
    "future paper/simulation evidence should be inspected, not whether it is "
    "profitable or live-ready."
)


@dataclass(frozen=True)
class ExecutionReviewCriterion:
    """One locked criterion for future paper-runner execution review."""

    criterion_id: str
    category: str
    title: str
    review_question: str
    required_evidence: str
    pass_rule: str
    blocked_claim: str
    status: str


@dataclass(frozen=True)
class ExecutionReviewCriteriaReport:
    """Serializable Phase 11 execution-review criteria report."""

    report_type: str
    status: str
    generated_at_utc: str
    execution_review_readiness_input_path: str
    execution_review_readiness_found: bool
    execution_review_readiness_status: str
    phase11_started: bool
    readiness_accepts_criteria: bool
    output_directory: str
    criterion_count: int
    locked_criterion_count: int
    accepted_for_future_safe_paper_runner_execution_review_close: bool
    completed_total_after_module: int
    phase_11_pending_after_module: int
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
    execution_review_criteria: list[ExecutionReviewCriterion]


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


def _phase11_started(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    return any(
        bool(payload.get(key))
        for key in (
            "phase11_started",
            "phase_11_started",
            "safe_paper_runner_execution_review_started",
        )
    )


def _accepts_criteria(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    return any(
        bool(payload.get(key))
        for key in (
            "accepted_for_future_safe_paper_runner_execution_review_criteria",
            "accepted_for_future_safe_paper_runner_execution_review_close",
            "accepted_for_future_phase11_safe_paper_runner_execution_review",
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


def _execution_review_criteria() -> list[ExecutionReviewCriterion]:
    return [
        ExecutionReviewCriterion(
            "exec-review-01",
            "input_boundary",
            "Recorded-data-only execution review",
            "Does the future execution evidence use only local recorded data?",
            "dataset_path, recorded_data_only, live_data_mode",
            "live_data_mode=recorded_data_only and no live feed fields are enabled",
            "live-data-execution-review",
            "locked",
        ),
        ExecutionReviewCriterion(
            "exec-review-02",
            "execution_boundary",
            "No runner execution enablement review",
            "Does the future review keep execution disabled while inspecting evidence?",
            "runner_execution_enabled and backtest_executed fields",
            "runner_execution_enabled=false and backtest_executed=false",
            "execution-enabled-during-review",
            "locked",
        ),
        ExecutionReviewCriterion(
            "exec-review-03",
            "broker_boundary",
            "No broker/order surface review",
            "Does the future evidence avoid broker payloads, order placement, and real-order readiness?",
            "broker_execution_mode and real_order_mode fields",
            "broker_execution_mode=broker_disabled and real_order_mode=real_orders_disabled",
            "broker-or-real-order-ready",
            "locked",
        ),
        ExecutionReviewCriterion(
            "exec-review-04",
            "trade_mapping_boundary",
            "Option-buy paper mapping review",
            "Does the future execution review preserve only CE/PE buy paper intent mapping?",
            "direction_to_option_intent fields",
            "LONG=CE_BUY_PAPER, SHORT=PE_BUY_PAPER, NEUTRAL=NO_TRADE",
            "option-selling-futures-or-equity-execution",
            "locked",
        ),
        ExecutionReviewCriterion(
            "exec-review-05",
            "strategy_boundary",
            "No optimization or strategy mutation review",
            "Does the future review avoid parameter optimization and strategy edits?",
            "optimization_executed and strategy_logic_changed fields",
            "optimization_executed=false and strategy_logic_changed=false",
            "optimized-winning-strategy",
            "locked",
        ),
        ExecutionReviewCriterion(
            "exec-review-06",
            "reporting_boundary",
            "No profitability or live-readiness claim review",
            "Does the future report avoid profit, live-readiness, and real-money claims?",
            "profitability_claim_allowed, ready_for_live_or_real_money, and safety notices",
            "profitability_claim_allowed=false and ready_for_live_or_real_money=false",
            "profitable-live-ready-real-money-claim",
            "locked",
        ),
    ]


def build_execution_review_criteria_report(
    *,
    execution_review_readiness_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ExecutionReviewCriteriaReport:
    """Build safe execution-review criteria without executing any runner."""

    input_path = execution_review_readiness_input_path or _first_existing(
        DEFAULT_EXECUTION_REVIEW_READINESS_INPUTS
    )
    payload, issues = _load_json(
        input_path,
        missing_code="execution_review_readiness_input_missing",
    )

    readiness_found = payload is not None
    readiness_status = _status(payload)
    phase11_started = _phase11_started(payload)
    readiness_accepts = _accepts_criteria(payload)

    if _unsafe_payload(payload):
        issues.append(
            {
                "code": "unsafe_execution_review_readiness_input_boundary",
                "severity": "fail",
                "message": "Execution review readiness input allowed live/real money, runner execution, strategy change, optimization, backtest, or profitability claims.",
            }
        )

    if readiness_found and readiness_status != "pass":
        issues.append(
            {
                "code": "execution_review_readiness_input_not_pass",
                "severity": "warn",
                "message": "Execution review readiness input exists but is not marked pass.",
            }
        )

    if readiness_found and not phase11_started:
        issues.append(
            {
                "code": "phase11_not_started",
                "severity": "warn",
                "message": "Execution review readiness input exists but does not explicitly start Phase 11.",
            }
        )

    if readiness_found and not readiness_accepts:
        issues.append(
            {
                "code": "readiness_not_accepted_for_execution_review_criteria",
                "severity": "warn",
                "message": "Execution review readiness input exists but does not explicitly accept future criteria work.",
            }
        )

    criteria = _execution_review_criteria()
    failures = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "fail" if failures else "pass"

    accepted = (
        status == "pass"
        and readiness_found
        and readiness_status == "pass"
        and phase11_started
        and readiness_accepts
        and all(criterion.status == "locked" for criterion in criteria)
    )

    return ExecutionReviewCriteriaReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        execution_review_readiness_input_path=str(input_path),
        execution_review_readiness_found=readiness_found,
        execution_review_readiness_status=readiness_status,
        phase11_started=phase11_started,
        readiness_accepts_criteria=readiness_accepts,
        output_directory=str(output_dir),
        criterion_count=len(criteria),
        locked_criterion_count=sum(1 for criterion in criteria if criterion.status == "locked"),
        accepted_for_future_safe_paper_runner_execution_review_close=accepted,
        completed_total_after_module=121,
        phase_11_pending_after_module=1,
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
        execution_review_criteria=criteria,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_criteria_csv(path: Path, criteria: list[ExecutionReviewCriterion]) -> None:
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


def _text_report(report: ExecutionReviewCriteriaReport) -> str:
    lines = [
        "HQE Safe Paper Runner Execution Review Criteria Pack",
        "=" * 70,
        f"Status: {report.status}",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Execution review readiness input path: {report.execution_review_readiness_input_path}",
        f"Execution review readiness found: {report.execution_review_readiness_found}",
        f"Execution review readiness status: {report.execution_review_readiness_status}",
        f"Phase 11 started: {report.phase11_started}",
        f"Readiness accepts criteria: {report.readiness_accepts_criteria}",
        (
            "Accepted for future safe paper-runner execution review close: "
            f"{report.accepted_for_future_safe_paper_runner_execution_review_close}"
        ),
        f"Criteria locked: {report.locked_criterion_count}/{report.criterion_count}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 11 pending after module: {report.phase_11_pending_after_module}",
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
        "Execution review criteria:",
    ]

    for criterion in report.execution_review_criteria:
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


def write_execution_review_criteria_pack(
    report: ExecutionReviewCriteriaReport,
    output_dir: Path,
) -> dict[str, str]:
    """Write JSON, text, CSV, and manifest evidence files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    criteria_csv = output_dir / "safe_paper_runner_execution_review_criteria.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_criteria_csv(criteria_csv, report.execution_review_criteria)

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
            "accepted_for_future_safe_paper_runner_execution_review_close": report.accepted_for_future_safe_paper_runner_execution_review_close,
            "completed_total_after_module": report.completed_total_after_module,
            "phase_11_pending_after_module": report.phase_11_pending_after_module,
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


def build_and_write_execution_review_criteria_pack(
    *,
    execution_review_readiness_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[ExecutionReviewCriteriaReport, dict[str, str]]:
    report = build_execution_review_criteria_report(
        execution_review_readiness_input_path=execution_review_readiness_input_path,
        output_dir=output_dir,
    )
    outputs = write_execution_review_criteria_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write the safe paper-runner execution review criteria pack."
    )
    parser.add_argument("--execution-review-readiness-input", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_execution_review_criteria_pack(
        execution_review_readiness_input_path=Path(args.execution_review_readiness_input)
        if args.execution_review_readiness_input
        else None,
        output_dir=Path(args.output_dir),
    )

    print("HQE safe paper-runner execution review criteria pack completed.")
    print(f"Status: {report.status}")
    print(f"Execution review readiness found: {report.execution_review_readiness_found}")
    print(f"Phase 11 started: {report.phase11_started}")
    print(
        "Accepted for future safe paper-runner execution review close: "
        f"{report.accepted_for_future_safe_paper_runner_execution_review_close}"
    )
    print(f"Criteria locked: {report.locked_criterion_count}/{report.criterion_count}")
    print(f"Runner execution enabled: {report.runner_execution_enabled}")
    print(f"Backtest executed: {report.backtest_executed}")
    print(f"Strategy logic changed: {report.strategy_logic_changed}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 11 pending after module: {report.phase_11_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print(SAFETY_NOTICE)
    print(NO_PROFITABILITY_CLAIM_NOTICE)

    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
