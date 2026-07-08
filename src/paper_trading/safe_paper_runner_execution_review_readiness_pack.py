"""
Safe Paper Runner Execution Review Readiness Pack

Module PPPPP starts Phase 11 after Phase 10 close.

This pack verifies that Phase 10 close evidence can be used to start a safe
paper-runner execution review track. It does not execute a backtest, optimize
parameters, change strategy logic, connect to a broker, request live market
data, place real orders, use real money, approve live trading, or claim
profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


REPORT_TYPE = "safe_paper_runner_execution_review_readiness_pack"

DEFAULT_PHASE10_CLOSE_INPUTS = (
    Path(
        "reports/paper_trading/safe_paper_runner_review_phase_close_pack/"
        "safe_paper_runner_review_phase_close_pack.json"
    ),
    Path("reports/paper_trading/safe_paper_runner_review_phase_close_pack/manifest.json"),
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/safe_paper_runner_execution_review_readiness_pack"
)

SAFE_READINESS_MODE = "execution_review_readiness_only"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Safe paper-runner execution review readiness only. This pack does not run "
    "a backtest, connect to brokers, request live market data, place real orders, "
    "use real money, approve live trading, or prove profitability."
)
NO_PROFITABILITY_CLAIM_NOTICE = (
    "This is not a profitability claim. Phase 11 readiness is a paper/simulation "
    "project-control artifact only."
)


@dataclass(frozen=True)
class ExecutionReviewReadinessItem:
    """One Phase 11 execution-review readiness checklist item."""

    item_id: str
    category: str
    title: str
    requirement: str
    evidence: str
    status: str


@dataclass(frozen=True)
class ExecutionReviewReadinessReport:
    """Serializable Phase 11 execution-review readiness report."""

    report_type: str
    status: str
    generated_at_utc: str
    phase10_close_input_path: str
    phase10_close_report_found: bool
    phase10_close_status: str
    phase10_complete: bool
    phase10_accepts_phase11_review: bool
    output_directory: str
    readiness_item_count: int
    passed_readiness_item_count: int
    phase11_started: bool
    accepted_for_future_safe_paper_runner_execution_review_criteria: bool
    completed_total_after_module: int
    phase_11_pending_after_module: int
    readiness_mode: str
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
    readiness_items: list[ExecutionReviewReadinessItem]


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


def _phase10_complete(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    return any(
        bool(payload.get(key))
        for key in (
            "phase_10_complete",
            "safe_paper_runner_review_phase_10_complete",
            "phase_complete",
        )
    )


def _accepts_phase11(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    return any(
        bool(payload.get(key))
        for key in (
            "accepted_for_future_phase11_safe_paper_runner_execution_review",
            "accepted_for_future_safe_paper_runner_execution_review_criteria",
            "accepted_for_future_safe_paper_runner_execution_review_close",
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


def _readiness_items(
    *,
    phase10_found: bool,
    phase10_status: str,
    phase10_complete: bool,
    phase10_accepts_phase11: bool,
) -> list[ExecutionReviewReadinessItem]:
    return [
        ExecutionReviewReadinessItem(
            "phase11-readiness-01",
            "phase_gate",
            "Phase 10 close evidence available",
            "Phase 11 execution review track must start only after Phase 10 close evidence exists.",
            f"found={phase10_found}; status={phase10_status}",
            "pass" if phase10_found and phase10_status == "pass" else "warn",
        ),
        ExecutionReviewReadinessItem(
            "phase11-readiness-02",
            "phase_gate",
            "Phase 10 marked complete",
            "Phase 11 readiness requires Phase 10 pending count to be zero.",
            f"phase_10_complete={phase10_complete}",
            "pass" if phase10_complete else "warn",
        ),
        ExecutionReviewReadinessItem(
            "phase11-readiness-03",
            "handoff",
            "Phase 10 accepts Phase 11 execution review",
            "Phase 10 close evidence must explicitly accept future safe paper-runner execution review.",
            f"accepted_for_phase11_review={phase10_accepts_phase11}",
            "pass" if phase10_accepts_phase11 else "warn",
        ),
        ExecutionReviewReadinessItem(
            "phase11-readiness-04",
            "safety",
            "Runner execution remains disabled",
            "This readiness module must not execute or enable the future paper runner.",
            "runner_execution_enabled=false; backtest_executed=false",
            "pass",
        ),
        ExecutionReviewReadinessItem(
            "phase11-readiness-05",
            "safety",
            "Broker, live data, and real orders remain disabled",
            "Phase 11 readiness must keep live trading surfaces disabled.",
            "broker_disabled; recorded_data_only; real_orders_disabled",
            "pass",
        ),
        ExecutionReviewReadinessItem(
            "phase11-readiness-06",
            "reporting",
            "No profitability or live-readiness claim",
            "Phase 11 readiness must not claim profit, live readiness, or real-money readiness.",
            "profitability_claim_allowed=false; ready_for_live_or_real_money=false",
            "pass",
        ),
    ]


def build_execution_review_readiness_report(
    *,
    phase10_close_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ExecutionReviewReadinessReport:
    """Build Phase 11 readiness report without executing any runner."""

    input_path = phase10_close_input_path or _first_existing(DEFAULT_PHASE10_CLOSE_INPUTS)
    payload, issues = _load_json(input_path, missing_code="phase10_close_input_missing")

    phase10_found = payload is not None
    phase10_status = _status(payload)
    phase10_done = _phase10_complete(payload)
    phase10_accepts = _accepts_phase11(payload)

    if _unsafe_payload(payload):
        issues.append(
            {
                "code": "unsafe_phase10_close_input_boundary",
                "severity": "fail",
                "message": "Phase 10 close input allowed live/real money, runner execution, strategy change, optimization, backtest, or profitability claims.",
            }
        )

    if phase10_found and phase10_status != "pass":
        issues.append(
            {
                "code": "phase10_close_input_not_pass",
                "severity": "warn",
                "message": "Phase 10 close input exists but is not marked pass.",
            }
        )

    if phase10_found and not phase10_done:
        issues.append(
            {
                "code": "phase10_not_marked_complete",
                "severity": "warn",
                "message": "Phase 10 close input exists but does not explicitly mark Phase 10 complete.",
            }
        )

    if phase10_found and not phase10_accepts:
        issues.append(
            {
                "code": "phase10_not_accepted_for_phase11_review",
                "severity": "warn",
                "message": "Phase 10 close input exists but does not explicitly accept future Phase 11 safe paper-runner execution review.",
            }
        )

    readiness_items = _readiness_items(
        phase10_found=phase10_found,
        phase10_status=phase10_status,
        phase10_complete=phase10_done,
        phase10_accepts_phase11=phase10_accepts,
    )

    failures = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "fail" if failures else "pass"
    phase11_started = status == "pass"
    accepted = (
        status == "pass"
        and phase10_found
        and phase10_status == "pass"
        and phase10_done
        and phase10_accepts
        and all(item.status == "pass" for item in readiness_items)
    )

    return ExecutionReviewReadinessReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        phase10_close_input_path=str(input_path),
        phase10_close_report_found=phase10_found,
        phase10_close_status=phase10_status,
        phase10_complete=phase10_done,
        phase10_accepts_phase11_review=phase10_accepts,
        output_directory=str(output_dir),
        readiness_item_count=len(readiness_items),
        passed_readiness_item_count=sum(1 for item in readiness_items if item.status == "pass"),
        phase11_started=phase11_started,
        accepted_for_future_safe_paper_runner_execution_review_criteria=accepted,
        completed_total_after_module=120,
        phase_11_pending_after_module=2,
        readiness_mode=SAFE_READINESS_MODE,
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
        readiness_items=readiness_items,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_readiness_csv(path: Path, items: list[ExecutionReviewReadinessItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "item_id",
                "category",
                "title",
                "requirement",
                "evidence",
                "status",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def _text_report(report: ExecutionReviewReadinessReport) -> str:
    lines = [
        "HQE Safe Paper Runner Execution Review Readiness Pack",
        "=" * 70,
        f"Status: {report.status}",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Phase 10 close input path: {report.phase10_close_input_path}",
        f"Phase 10 close report found: {report.phase10_close_report_found}",
        f"Phase 10 close status: {report.phase10_close_status}",
        f"Phase 10 complete: {report.phase10_complete}",
        f"Phase 10 accepts Phase 11 review: {report.phase10_accepts_phase11_review}",
        f"Phase 11 started: {report.phase11_started}",
        (
            "Accepted for future safe paper-runner execution review criteria: "
            f"{report.accepted_for_future_safe_paper_runner_execution_review_criteria}"
        ),
        f"Readiness passed: {report.passed_readiness_item_count}/{report.readiness_item_count}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 11 pending after module: {report.phase_11_pending_after_module}",
        f"Readiness mode: {report.readiness_mode}",
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
        "Readiness checklist:",
    ]

    for item in report.readiness_items:
        lines.extend(
            [
                "",
                f"- {item.item_id}: {item.title}",
                f"  Category: {item.category}",
                f"  Requirement: {item.requirement}",
                f"  Evidence: {item.evidence}",
                f"  Status: {item.status}",
            ]
        )

    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(
                f"- {issue.get('severity', 'unknown').upper()} {issue.get('code')}: {issue.get('message')}"
            )

    return "\n".join(lines) + "\n"


def write_execution_review_readiness_pack(
    report: ExecutionReviewReadinessReport,
    output_dir: Path,
) -> dict[str, str]:
    """Write JSON, text, CSV, and manifest evidence files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    readiness_csv = output_dir / "safe_paper_runner_execution_review_readiness_checklist.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_readiness_csv(readiness_csv, report.readiness_items)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "readiness_csv": str(readiness_csv),
        "manifest_json": str(manifest_json),
    }

    _write_json(
        manifest_json,
        {
            "report_type": REPORT_TYPE,
            "status": report.status,
            "generated_at_utc": report.generated_at_utc,
            "phase11_started": report.phase11_started,
            "accepted_for_future_safe_paper_runner_execution_review_criteria": report.accepted_for_future_safe_paper_runner_execution_review_criteria,
            "completed_total_after_module": report.completed_total_after_module,
            "phase_11_pending_after_module": report.phase_11_pending_after_module,
            "readiness_mode": report.readiness_mode,
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


def build_and_write_execution_review_readiness_pack(
    *,
    phase10_close_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[ExecutionReviewReadinessReport, dict[str, str]]:
    report = build_execution_review_readiness_report(
        phase10_close_input_path=phase10_close_input_path,
        output_dir=output_dir,
    )
    outputs = write_execution_review_readiness_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write the safe paper-runner execution review readiness pack."
    )
    parser.add_argument("--phase10-close-input", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_execution_review_readiness_pack(
        phase10_close_input_path=Path(args.phase10_close_input)
        if args.phase10_close_input
        else None,
        output_dir=Path(args.output_dir),
    )

    print("HQE safe paper-runner execution review readiness pack completed.")
    print(f"Status: {report.status}")
    print(f"Phase 10 close report found: {report.phase10_close_report_found}")
    print(f"Phase 10 complete: {report.phase10_complete}")
    print(f"Phase 11 started: {report.phase11_started}")
    print(
        "Accepted for future safe paper-runner execution review criteria: "
        f"{report.accepted_for_future_safe_paper_runner_execution_review_criteria}"
    )
    print(f"Readiness passed: {report.passed_readiness_item_count}/{report.readiness_item_count}")
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
