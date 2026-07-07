"""
Paper improvement readiness sprint close pack.

Module UUUU closes the post-v1.0 paper improvement readiness sprint.

This module reads the paper improvement acceptance gate pack and creates a
paper-only sprint close report.

It does not start a dashboard UI, does not import or require Streamlit at
runtime, does not run backtests, does not calculate profitability, does not
select a winning strategy, does not modify strategy logic, does not connect to
brokers, does not request live market data, does not place real orders, does
not use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_ACCEPTANCE_GATES = {
    "paper_only_acceptance_gate",
    "no_backtest_rerun_acceptance_gate",
    "no_strategy_change_acceptance_gate",
    "dataset_scope_acceptance_gate",
    "ledger_quality_acceptance_gate",
    "direction_mapping_acceptance_gate",
    "metrics_language_acceptance_gate",
    "cost_risk_acceptance_gate",
    "report_safety_acceptance_gate",
    "test_guard_acceptance_gate",
    "git_output_acceptance_gate",
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
class PaperImprovementReadinessSprintCloseChecklistItem:
    item_index: int
    item_name: str
    status: str
    evidence: str
    next_instruction: str


@dataclass(frozen=True)
class PaperImprovementReadinessSprintCloseIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperImprovementReadinessSprintCloseReport:
    generated_at_utc: str
    paper_improvement_acceptance_gate_path: str
    output_directory: str
    status: str
    paper_improvement_readiness_sprint_closed: bool
    ready_for_next_paper_planning_phase: bool
    selected_dataset_path: str
    safety_notice: str
    close_checklist_item_count: int
    acceptance_gate_item_count: int
    rerun_readiness_gate_item_count: int
    test_plan_item_count: int
    candidate_registry_item_count: int
    improvement_readiness_item_count: int
    phase_4_close_checklist_item_count: int
    close_gate_item_count: int
    report_safety_language_item_count: int
    metrics_context_item_count: int
    ledger_snapshot_item_count: int
    analysis_item_count: int
    review_summary_item_count: int
    presence_check_count: int
    expected_output_count: int
    present_required_file_count: int
    missing_required_file_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_5_pending_before_module: int
    phase_5_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_phase: str
    issues: list[PaperImprovementReadinessSprintCloseIssue]
    close_checklist: list[PaperImprovementReadinessSprintCloseChecklistItem]
    acceptance_gate_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper improvement readiness sprint close pack only. "
        "This pack closes the paper improvement readiness sprint from paper-only "
        "acceptance gate evidence. It does not start a dashboard UI, does not "
        "import or require Streamlit at runtime, does not run backtests, does "
        "not calculate profitability, does not select a winning strategy, does "
        "not modify strategy logic, does not connect to brokers, does not "
        "request live market data, does not place real orders, does not use "
        "real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> PaperImprovementReadinessSprintCloseIssue:
    return PaperImprovementReadinessSprintCloseIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperImprovementReadinessSprintCloseIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _load_acceptance_gate(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperImprovementReadinessSprintCloseIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_improvement_acceptance_gate_pack_missing",
                1,
                f"Paper improvement acceptance gate pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_improvement_acceptance_gate_pack_invalid_json",
                1,
                f"Paper improvement acceptance gate pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_improvement_acceptance_gate_pack_invalid_shape",
                1,
                "Paper improvement acceptance gate pack must be a JSON object.",
            )
        ]

    return payload, []


def _acceptance_gate_issues(
    acceptance_gate: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperImprovementReadinessSprintCloseIssue]:
    if acceptance_gate is None:
        return []

    issues: list[PaperImprovementReadinessSprintCloseIssue] = []

    status = str(acceptance_gate.get("status") or "unknown").lower()
    ready = bool(acceptance_gate.get("ready_for_paper_improvement_readiness_close"))
    missing_required = int(acceptance_gate.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_improvement_acceptance_gate_pack_warn",
                1,
                "Paper improvement acceptance gate pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_improvement_acceptance_gate_pack_not_pass",
                1,
                f"Paper improvement acceptance gate pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_acceptance_gate_pack_not_ready",
                1,
                "Paper improvement acceptance gate pack is not ready for sprint close.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_readiness_sprint_close_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(acceptance_gate)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_acceptance_gate_forbidden_fields",
                len(forbidden),
                "Paper improvement acceptance gate pack contains forbidden broker/order fields.",
            )
        )

    acceptance_issues = acceptance_gate.get("issues")
    if isinstance(acceptance_issues, list):
        fail_count = sum(
            1
            for item in acceptance_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "paper_improvement_acceptance_gate_contains_fail_issues",
                    fail_count,
                    "Paper improvement acceptance gate pack contains fail issues.",
                )
            )

    return issues


def _acceptance_gate_names(acceptance_gate: Mapping[str, Any] | None) -> list[str]:
    if acceptance_gate is None:
        return []

    raw_items = acceptance_gate.get("acceptance_gate_items")
    if not isinstance(raw_items, list):
        return []

    return sorted(
        {
            str(item.get("acceptance_gate_name") or "").strip().lower()
            for item in raw_items
            if isinstance(item, Mapping)
            and str(item.get("acceptance_gate_name") or "").strip()
        }
    )


def _readiness_issues(
    *,
    acceptance_gate_names: Sequence[str],
) -> list[PaperImprovementReadinessSprintCloseIssue]:
    missing_gates = REQUIRED_ACCEPTANCE_GATES - set(acceptance_gate_names)

    if missing_gates:
        return [
            _issue(
                "fail",
                "required_paper_improvement_acceptance_gates_missing",
                len(missing_gates),
                "Required paper improvement acceptance gates are missing.",
            )
        ]

    return []


def _close_checklist(
    status: str,
) -> list[PaperImprovementReadinessSprintCloseChecklistItem]:
    checklist_status = "closed" if status in {"pass", "warn"} else "blocked"

    raw_items = [
        (
            "paper_only_acceptance_closed",
            checklist_status,
            "Paper-only acceptance gate is present.",
            "Keep next phase paper-only unless a separate live-readiness path is created.",
        ),
        (
            "no_backtest_rerun_closed",
            checklist_status,
            "No backtest/rerun acceptance gate is present.",
            "Do not run a rerun without a separate tested execution module.",
        ),
        (
            "no_strategy_change_closed",
            checklist_status,
            "No strategy change acceptance gate is present.",
            "Do not modify strategy logic without a separate implementation and test gate.",
        ),
        (
            "dataset_scope_closed",
            checklist_status,
            "Dataset scope acceptance gate is present.",
            "Carry recorded-data scope and limitations into the next paper planning phase.",
        ),
        (
            "ledger_quality_closed",
            checklist_status,
            "Ledger quality acceptance gate is present.",
            "Carry ledger quality and missing-field notes forward.",
        ),
        (
            "direction_mapping_closed",
            checklist_status,
            "Direction mapping acceptance gate is present.",
            "Preserve LONG = CE BUY paper plan, SHORT = PE BUY paper plan, NEUTRAL = no trade.",
        ),
        (
            "metrics_language_closed",
            checklist_status,
            "Metrics language acceptance gate is present.",
            "Use metrics as descriptive paper evidence only.",
        ),
        (
            "cost_risk_closed",
            checklist_status,
            "Cost/risk acceptance gate is present.",
            "Keep costs, slippage, and risk notes as assumptions or paper evidence.",
        ),
        (
            "report_safety_closed",
            checklist_status,
            "Report safety acceptance gate is present.",
            "Keep no-winner and no-profitability-claim language.",
        ),
        (
            "test_guard_closed",
            checklist_status,
            "Test guard acceptance gate is present.",
            "Require targeted tests, smoke tests, and full quick check before future implementation.",
        ),
        (
            "git_output_closed",
            checklist_status,
            "Git output acceptance gate is present.",
            "Keep generated reports/data ignored and uncommitted.",
        ),
        (
            "phase_5_closed",
            checklist_status,
            "All Phase 5 paper improvement readiness gates are present.",
            "Next module can start a new paper-only planning or implementation-readiness phase.",
        ),
    ]

    return [
        PaperImprovementReadinessSprintCloseChecklistItem(
            item_index=index,
            item_name=item_name,
            status=item_status,
            evidence=evidence,
            next_instruction=next_instruction,
        )
        for index, (item_name, item_status, evidence, next_instruction) in enumerate(
            raw_items,
            start=1,
        )
    ]


def build_paper_improvement_readiness_sprint_close_report(
    *,
    paper_improvement_acceptance_gate_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperImprovementReadinessSprintCloseReport:
    acceptance_gate, load_issues = _load_acceptance_gate(
        paper_improvement_acceptance_gate_path
    )

    issues: list[PaperImprovementReadinessSprintCloseIssue] = []
    issues.extend(load_issues)
    issues.extend(_acceptance_gate_issues(acceptance_gate, allow_warnings=allow_warnings))

    acceptance_names = _acceptance_gate_names(acceptance_gate)
    issues.extend(_readiness_issues(acceptance_gate_names=acceptance_names))

    status = _status(issues)
    checklist = _close_checklist(status)

    return PaperImprovementReadinessSprintCloseReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_improvement_acceptance_gate_path=str(paper_improvement_acceptance_gate_path),
        output_directory=str(output_dir),
        status=status,
        paper_improvement_readiness_sprint_closed=status in {"pass", "warn"},
        ready_for_next_paper_planning_phase=status in {"pass", "warn"},
        selected_dataset_path=str((acceptance_gate or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        close_checklist_item_count=len(checklist),
        acceptance_gate_item_count=len(acceptance_names),
        rerun_readiness_gate_item_count=int(
            (acceptance_gate or {}).get("rerun_readiness_gate_item_count") or 0
        ),
        test_plan_item_count=int((acceptance_gate or {}).get("test_plan_item_count") or 0),
        candidate_registry_item_count=int(
            (acceptance_gate or {}).get("candidate_registry_item_count") or 0
        ),
        improvement_readiness_item_count=int(
            (acceptance_gate or {}).get("improvement_readiness_item_count") or 0
        ),
        phase_4_close_checklist_item_count=int(
            (acceptance_gate or {}).get("phase_4_close_checklist_item_count") or 0
        ),
        close_gate_item_count=int((acceptance_gate or {}).get("close_gate_item_count") or 0),
        report_safety_language_item_count=int(
            (acceptance_gate or {}).get("report_safety_language_item_count") or 0
        ),
        metrics_context_item_count=int((acceptance_gate or {}).get("metrics_context_item_count") or 0),
        ledger_snapshot_item_count=int((acceptance_gate or {}).get("ledger_snapshot_item_count") or 0),
        analysis_item_count=int((acceptance_gate or {}).get("analysis_item_count") or 0),
        review_summary_item_count=int((acceptance_gate or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((acceptance_gate or {}).get("presence_check_count") or 0),
        expected_output_count=int((acceptance_gate or {}).get("expected_output_count") or 0),
        present_required_file_count=int((acceptance_gate or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((acceptance_gate or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=98,
        completed_total_after_module=99,
        phase_5_pending_before_module=1,
        phase_5_pending_after_module=0,
        full_hqe_product_estimate_after_module="91-96%",
        recommended_next_phase=(
            "Begin the next paper-only planning phase. Do not introduce live market data, "
            "broker execution, real money, strategy changes, backtest reruns, profitability claims, "
            "or winning-strategy selection without a separate tested safety path."
        ),
        issues=issues,
        close_checklist=checklist,
        acceptance_gate_names=acceptance_names,
    )


def write_paper_improvement_readiness_sprint_close_report(
    report: PaperImprovementReadinessSprintCloseReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    close_json = output_dir / "paper_improvement_readiness_sprint_close_pack.json"
    close_txt = output_dir / "paper_improvement_readiness_sprint_close_pack.txt"
    checklist_csv = output_dir / "paper_improvement_readiness_sprint_close_checklist.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["close_checklist"] = [asdict(item) for item in report.close_checklist]
    close_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with checklist_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "item_name",
                "status",
                "evidence",
                "next_instruction",
            ]
        )
        for item in report.close_checklist:
            writer.writerow(
                [
                    item.item_index,
                    item.item_name,
                    item.status,
                    item.evidence,
                    item.next_instruction,
                ]
            )

    lines = [
        "HQE Paper Improvement Readiness Sprint Close Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Paper improvement readiness sprint closed: {report.paper_improvement_readiness_sprint_closed}",
        f"Ready for next paper planning phase: {report.ready_for_next_paper_planning_phase}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Close checklist items: {report.close_checklist_item_count}",
        f"Acceptance gate items: {report.acceptance_gate_item_count}",
        f"Rerun readiness gate items: {report.rerun_readiness_gate_item_count}",
        f"Test plan items: {report.test_plan_item_count}",
        f"Candidate registry items: {report.candidate_registry_item_count}",
        f"Improvement readiness items: {report.improvement_readiness_item_count}",
        f"Phase 4 close checklist items: {report.phase_4_close_checklist_item_count}",
        f"Close gate items: {report.close_gate_item_count}",
        f"Report safety language items: {report.report_safety_language_item_count}",
        f"Metrics context items: {report.metrics_context_item_count}",
        f"Ledger snapshot items: {report.ledger_snapshot_item_count}",
        f"Analysis items: {report.analysis_item_count}",
        f"Review summary items: {report.review_summary_item_count}",
        f"Presence checks: {report.presence_check_count}",
        f"Expected outputs: {report.expected_output_count}",
        f"Present required files: {report.present_required_file_count}",
        f"Missing required files: {report.missing_required_file_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Post-v1.0 Phase 1: Real Backtest Usage Sprint complete.",
        "- Post-v1.0 Phase 2: Dashboard Sprint complete.",
        "- Post-v1.0 Phase 3: Recorded Backtest Review Workflow complete.",
        "- Post-v1.0 Phase 4: Paper Backtest Evidence Analysis Sprint complete.",
        f"- Completed total before Module UUUU: {report.completed_total_before_module} modules.",
        f"- Completed total after Module UUUU: {report.completed_total_after_module} modules.",
        f"- Phase 5 pending before Module UUUU: {report.phase_5_pending_before_module} module.",
        f"- Phase 5 pending after Module UUUU: {report.phase_5_pending_after_module} modules.",
        f"- Full HQE product estimate after Module UUUU: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next phase:",
        report.recommended_next_phase,
        "",
        "Sprint close checklist:",
    ]

    for item in report.close_checklist:
        lines.append(
            (
                f"{item.item_index}. {item.item_name} [{item.status}] - "
                f"{item.evidence} Next={item.next_instruction}"
            )
        )

    lines.extend(["", "Acceptance gate names:"])
    for gate_name in report.acceptance_gate_names:
        lines.append(f"- {gate_name}")

    lines.extend(
        [
            "",
            "Safety:",
            "- This pack does not start a dashboard UI.",
            "- This pack does not import or require Streamlit at runtime.",
            "- This pack does not run backtests.",
            "- This pack does not calculate profitability.",
            "- This pack does not select a winning strategy.",
            "- This pack does not modify strategy logic.",
            "- This report is not a profitability claim.",
            "- LONG = CE BUY paper plan only.",
            "- SHORT = PE BUY paper plan only.",
            "- NEUTRAL = no trade.",
            "- No option selling.",
            "- No broker orders.",
            "- No live market data.",
            "- No real money.",
            "",
            "Issues:",
        ]
    )

    if not report.issues:
        lines.append("- PASS: Paper improvement readiness sprint is closed.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {close_json}",
            f"- {close_txt}",
            f"- {checklist_csv}",
            f"- {manifest_json}",
        ]
    )
    close_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "paper_improvement_readiness_sprint_close_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "paper_improvement_readiness_sprint_closed": report.paper_improvement_readiness_sprint_closed,
        "ready_for_next_paper_planning_phase": report.ready_for_next_paper_planning_phase,
        "selected_dataset_path": report.selected_dataset_path,
        "close_checklist_item_count": report.close_checklist_item_count,
        "acceptance_gate_item_count": report.acceptance_gate_item_count,
        "rerun_readiness_gate_item_count": report.rerun_readiness_gate_item_count,
        "test_plan_item_count": report.test_plan_item_count,
        "candidate_registry_item_count": report.candidate_registry_item_count,
        "improvement_readiness_item_count": report.improvement_readiness_item_count,
        "phase_4_close_checklist_item_count": report.phase_4_close_checklist_item_count,
        "close_gate_item_count": report.close_gate_item_count,
        "report_safety_language_item_count": report.report_safety_language_item_count,
        "metrics_context_item_count": report.metrics_context_item_count,
        "ledger_snapshot_item_count": report.ledger_snapshot_item_count,
        "analysis_item_count": report.analysis_item_count,
        "review_summary_item_count": report.review_summary_item_count,
        "presence_check_count": report.presence_check_count,
        "expected_output_count": report.expected_output_count,
        "present_required_file_count": report.present_required_file_count,
        "missing_required_file_count": report.missing_required_file_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_5_pending_after_module": report.phase_5_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_phase": report.recommended_next_phase,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_improvement_readiness_sprint_close_pack_json": str(close_json),
            "paper_improvement_readiness_sprint_close_pack_txt": str(close_txt),
            "paper_improvement_readiness_sprint_close_checklist_csv": str(checklist_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_improvement_readiness_sprint_close_pack_json": close_json,
        "paper_improvement_readiness_sprint_close_pack_txt": close_txt,
        "paper_improvement_readiness_sprint_close_checklist_csv": checklist_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_improvement_readiness_sprint_close_report(
    *,
    paper_improvement_acceptance_gate_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperImprovementReadinessSprintCloseReport, dict[str, Path]]:
    report = build_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=paper_improvement_acceptance_gate_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_improvement_readiness_sprint_close_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper improvement readiness sprint close pack."
    )
    parser.add_argument(
        "--paper-improvement-acceptance-gate",
        default=(
            "reports/paper_trading/"
            "paper_improvement_acceptance_gate_pack/"
            "paper_improvement_acceptance_gate_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_improvement_readiness_sprint_close_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=Path(
            args.paper_improvement_acceptance_gate
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper improvement readiness sprint close pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Paper improvement readiness sprint closed: {report.paper_improvement_readiness_sprint_closed}")
    print(f"Sprint close report: {outputs['paper_improvement_readiness_sprint_close_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
