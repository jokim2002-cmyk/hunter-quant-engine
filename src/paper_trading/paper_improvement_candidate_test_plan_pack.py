"""
Paper improvement candidate test plan pack.

Module RRRR in the post-v1.0 paper improvement readiness sprint.

This module reads the paper improvement candidate registry pack and creates a
planning-only paper improvement candidate test plan.

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


REQUIRED_CANDIDATES = {
    "baseline_documentation_candidate",
    "dataset_scope_review_candidate",
    "ledger_quality_review_candidate",
    "direction_mapping_review_candidate",
    "metrics_context_review_candidate",
    "cost_risk_note_candidate",
    "report_language_guard_candidate",
    "regression_test_candidate",
    "paper_rerun_candidate",
    "generated_output_git_guard_candidate",
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
class PaperImprovementCandidateTestPlanItem:
    item_index: int
    test_plan_name: str
    test_area: str
    evidence_source: str
    test_instruction: str
    required_before_status: str
    safety_boundary: str


@dataclass(frozen=True)
class PaperImprovementCandidateTestPlanIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperImprovementCandidateTestPlanReport:
    generated_at_utc: str
    paper_improvement_candidate_registry_path: str
    output_directory: str
    status: str
    ready_for_paper_rerun_readiness_gate: bool
    selected_dataset_path: str
    safety_notice: str
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
    recommended_next_action: str
    issues: list[PaperImprovementCandidateTestPlanIssue]
    test_plan_items: list[PaperImprovementCandidateTestPlanItem]
    candidate_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper improvement candidate test plan pack only. "
        "This pack creates planning-only test plan items from the paper "
        "improvement candidate registry. It does not start a dashboard UI, "
        "does not import or require Streamlit at runtime, does not run "
        "backtests, does not calculate profitability, does not select a "
        "winning strategy, does not modify strategy logic, does not connect to "
        "brokers, does not request live market data, does not place real "
        "orders, does not use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> PaperImprovementCandidateTestPlanIssue:
    return PaperImprovementCandidateTestPlanIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperImprovementCandidateTestPlanIssue]) -> str:
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


def _load_candidate_registry(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperImprovementCandidateTestPlanIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_improvement_candidate_registry_pack_missing",
                1,
                f"Paper improvement candidate registry pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_improvement_candidate_registry_pack_invalid_json",
                1,
                f"Paper improvement candidate registry pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_improvement_candidate_registry_pack_invalid_shape",
                1,
                "Paper improvement candidate registry pack must be a JSON object.",
            )
        ]

    return payload, []


def _candidate_registry_issues(
    registry: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperImprovementCandidateTestPlanIssue]:
    if registry is None:
        return []

    issues: list[PaperImprovementCandidateTestPlanIssue] = []

    status = str(registry.get("status") or "unknown").lower()
    ready = bool(registry.get("ready_for_candidate_test_plan"))
    missing_required = int(registry.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_improvement_candidate_registry_pack_warn",
                1,
                "Paper improvement candidate registry pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_improvement_candidate_registry_pack_not_pass",
                1,
                f"Paper improvement candidate registry pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_candidate_registry_pack_not_ready",
                1,
                "Paper improvement candidate registry pack is not ready for candidate test plan.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_candidate_test_plan_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(registry)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_candidate_registry_forbidden_fields",
                len(forbidden),
                "Paper improvement candidate registry pack contains forbidden broker/order fields.",
            )
        )

    registry_issues = registry.get("issues")
    if isinstance(registry_issues, list):
        fail_count = sum(
            1
            for item in registry_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "paper_improvement_candidate_registry_contains_fail_issues",
                    fail_count,
                    "Paper improvement candidate registry pack contains fail issues.",
                )
            )

    return issues


def _candidate_names(registry: Mapping[str, Any] | None) -> list[str]:
    if registry is None:
        return []

    raw_items = registry.get("candidate_registry_items")
    if not isinstance(raw_items, list):
        return []

    return sorted(
        {
            str(item.get("candidate_name") or "").strip().lower()
            for item in raw_items
            if isinstance(item, Mapping) and str(item.get("candidate_name") or "").strip()
        }
    )


def _readiness_issues(
    *,
    candidate_names: Sequence[str],
) -> list[PaperImprovementCandidateTestPlanIssue]:
    missing_candidates = REQUIRED_CANDIDATES - set(candidate_names)

    if missing_candidates:
        return [
            _issue(
                "fail",
                "required_paper_improvement_candidates_missing",
                len(missing_candidates),
                "Required paper improvement candidates are missing.",
            )
        ]

    return []


def _test_plan_items() -> list[PaperImprovementCandidateTestPlanItem]:
    raw_items = [
        (
            "baseline_documentation_test_plan",
            "baseline",
            "baseline_documentation_candidate",
            "Verify baseline report docs mention paper-only evidence and frozen baseline.",
            "required_before_any_future_change",
            "No strategy logic modification in this pack.",
        ),
        (
            "dataset_scope_test_plan",
            "dataset",
            "dataset_scope_review_candidate",
            "Verify dataset scope labels, recorded-data source notes, and limitation wording.",
            "required_before_any_dataset_scope_change",
            "No live market data request.",
        ),
        (
            "ledger_quality_test_plan",
            "ledger",
            "ledger_quality_review_candidate",
            "Verify ledger completeness checks and missing-field notes remain descriptive.",
            "required_before_any_ledger_improvement",
            "No broker order fields and no real orders.",
        ),
        (
            "direction_mapping_test_plan",
            "decision_mapping",
            "direction_mapping_review_candidate",
            "Verify LONG maps to CE BUY paper plan, SHORT maps to PE BUY paper plan, and NEUTRAL maps to no trade.",
            "required_before_any_decision_mapping_change",
            "No option selling.",
        ),
        (
            "metrics_context_test_plan",
            "metrics",
            "metrics_context_review_candidate",
            "Verify sample-size, trade-count, and metric wording is descriptive evidence only.",
            "required_before_any_metrics_report_change",
            "Not a profitability claim.",
        ),
        (
            "cost_risk_note_test_plan",
            "costs_and_risk",
            "cost_risk_note_candidate",
            "Verify cost, slippage, and risk notes remain assumptions or paper evidence.",
            "required_before_any_cost_risk_wording_change",
            "No real-money risk claim.",
        ),
        (
            "report_language_guard_test_plan",
            "report_safety",
            "report_language_guard_candidate",
            "Verify no-winner, no-profitability-claim, and paper-only language remains present.",
            "required_before_any_report_language_change",
            "No winning strategy selection.",
        ),
        (
            "regression_test_plan_test_plan",
            "testing",
            "regression_test_candidate",
            "Verify future changes must include targeted tests, smoke tests, and full quick check.",
            "required_before_any_implementation",
            "No untested logic change.",
        ),
        (
            "paper_rerun_boundary_test_plan",
            "rerun_control",
            "paper_rerun_candidate",
            "Verify future rerun commands stay recorded-data paper/simulation unless separately gated.",
            "required_before_any_rerun_workflow_change",
            "No broker execution.",
        ),
        (
            "generated_output_git_guard_test_plan",
            "git_safety",
            "generated_output_git_guard_candidate",
            "Verify generated reports/data stay ignored and uncommitted.",
            "required_before_any_git_guard_change",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        PaperImprovementCandidateTestPlanItem(
            item_index=index,
            test_plan_name=test_plan_name,
            test_area=test_area,
            evidence_source=evidence_source,
            test_instruction=test_instruction,
            required_before_status=required_before_status,
            safety_boundary=safety_boundary,
        )
        for index, (
            test_plan_name,
            test_area,
            evidence_source,
            test_instruction,
            required_before_status,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_paper_improvement_candidate_test_plan_report(
    *,
    paper_improvement_candidate_registry_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperImprovementCandidateTestPlanReport:
    registry, load_issues = _load_candidate_registry(paper_improvement_candidate_registry_path)

    issues: list[PaperImprovementCandidateTestPlanIssue] = []
    issues.extend(load_issues)
    issues.extend(_candidate_registry_issues(registry, allow_warnings=allow_warnings))

    names = _candidate_names(registry)
    issues.extend(_readiness_issues(candidate_names=names))

    test_items = _test_plan_items()
    status = _status(issues)

    return PaperImprovementCandidateTestPlanReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_improvement_candidate_registry_path=str(paper_improvement_candidate_registry_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_paper_rerun_readiness_gate=status in {"pass", "warn"},
        selected_dataset_path=str((registry or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        test_plan_item_count=len(test_items),
        candidate_registry_item_count=len(names),
        improvement_readiness_item_count=int(
            (registry or {}).get("improvement_readiness_item_count") or 0
        ),
        phase_4_close_checklist_item_count=int(
            (registry or {}).get("phase_4_close_checklist_item_count") or 0
        ),
        close_gate_item_count=int((registry or {}).get("close_gate_item_count") or 0),
        report_safety_language_item_count=int(
            (registry or {}).get("report_safety_language_item_count") or 0
        ),
        metrics_context_item_count=int((registry or {}).get("metrics_context_item_count") or 0),
        ledger_snapshot_item_count=int((registry or {}).get("ledger_snapshot_item_count") or 0),
        analysis_item_count=int((registry or {}).get("analysis_item_count") or 0),
        review_summary_item_count=int((registry or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((registry or {}).get("presence_check_count") or 0),
        expected_output_count=int((registry or {}).get("expected_output_count") or 0),
        present_required_file_count=int((registry or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((registry or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=95,
        completed_total_after_module=96,
        phase_5_pending_before_module=4,
        phase_5_pending_after_module=3,
        full_hqe_product_estimate_after_module="88-93%",
        recommended_next_action=(
            "Build paper rerun readiness gate next. Keep candidate tests planning-only until "
            "a separate implementation module is explicitly created and fully tested."
        ),
        issues=issues,
        test_plan_items=test_items,
        candidate_names=names,
    )


def write_paper_improvement_candidate_test_plan_report(
    report: PaperImprovementCandidateTestPlanReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    test_plan_json = output_dir / "paper_improvement_candidate_test_plan_pack.json"
    test_plan_txt = output_dir / "paper_improvement_candidate_test_plan_pack.txt"
    items_csv = output_dir / "paper_improvement_candidate_test_plan_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["test_plan_items"] = [asdict(item) for item in report.test_plan_items]
    test_plan_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with items_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "test_plan_name",
                "test_area",
                "evidence_source",
                "test_instruction",
                "required_before_status",
                "safety_boundary",
            ]
        )
        for item in report.test_plan_items:
            writer.writerow(
                [
                    item.item_index,
                    item.test_plan_name,
                    item.test_area,
                    item.evidence_source,
                    item.test_instruction,
                    item.required_before_status,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Paper Improvement Candidate Test Plan Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for paper rerun readiness gate: {report.ready_for_paper_rerun_readiness_gate}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Test plan items: {report.test_plan_item_count}",
        f"Candidate registry items carried forward: {report.candidate_registry_item_count}",
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
        f"- Completed total before Module RRRR: {report.completed_total_before_module} modules.",
        f"- Completed total after Module RRRR: {report.completed_total_after_module} modules.",
        f"- Phase 5 pending before Module RRRR: {report.phase_5_pending_before_module} modules.",
        f"- Phase 5 pending after Module RRRR: {report.phase_5_pending_after_module} modules.",
        f"- Full HQE product estimate after Module RRRR: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Candidate test plan items:",
    ]

    for item in report.test_plan_items:
        lines.append(f"{item.item_index}. {item.test_plan_name} [{item.test_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Instruction: {item.test_instruction}")
        lines.append(f"   Required before: {item.required_before_status}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Candidate registry items carried forward:"])
    for candidate_name in report.candidate_names:
        lines.append(f"- {candidate_name}")

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
        lines.append("- PASS: Paper improvement candidate test plan is ready.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {test_plan_json}",
            f"- {test_plan_txt}",
            f"- {items_csv}",
            f"- {manifest_json}",
        ]
    )
    test_plan_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "paper_improvement_candidate_test_plan_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_paper_rerun_readiness_gate": report.ready_for_paper_rerun_readiness_gate,
        "selected_dataset_path": report.selected_dataset_path,
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
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_improvement_candidate_test_plan_pack_json": str(test_plan_json),
            "paper_improvement_candidate_test_plan_pack_txt": str(test_plan_txt),
            "paper_improvement_candidate_test_plan_items_csv": str(items_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_improvement_candidate_test_plan_pack_json": test_plan_json,
        "paper_improvement_candidate_test_plan_pack_txt": test_plan_txt,
        "paper_improvement_candidate_test_plan_items_csv": items_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_improvement_candidate_test_plan_report(
    *,
    paper_improvement_candidate_registry_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperImprovementCandidateTestPlanReport, dict[str, Path]]:
    report = build_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=paper_improvement_candidate_registry_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_improvement_candidate_test_plan_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper improvement candidate test plan pack."
    )
    parser.add_argument(
        "--paper-improvement-candidate-registry",
        default=(
            "reports/paper_trading/"
            "paper_improvement_candidate_registry_pack/"
            "paper_improvement_candidate_registry_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_improvement_candidate_test_plan_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=Path(
            args.paper_improvement_candidate_registry
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper improvement candidate test plan pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for paper rerun readiness gate: {report.ready_for_paper_rerun_readiness_gate}")
    print(f"Candidate test plan: {outputs['paper_improvement_candidate_test_plan_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
