"""
Paper improvement rerun readiness gate pack.

Module SSSS in the post-v1.0 paper improvement readiness sprint.

This module reads the paper improvement candidate test plan pack and creates a
paper-only rerun readiness gate. It prepares guardrails for a future rerun, but
does not run a backtest or rerun anything.

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


REQUIRED_TEST_PLANS = {
    "baseline_documentation_test_plan",
    "dataset_scope_test_plan",
    "ledger_quality_test_plan",
    "direction_mapping_test_plan",
    "metrics_context_test_plan",
    "cost_risk_note_test_plan",
    "report_language_guard_test_plan",
    "regression_test_plan_test_plan",
    "paper_rerun_boundary_test_plan",
    "generated_output_git_guard_test_plan",
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
class PaperImprovementRerunReadinessGateItem:
    item_index: int
    gate_name: str
    gate_area: str
    evidence_source: str
    gate_requirement: str
    rerun_status: str
    safety_boundary: str


@dataclass(frozen=True)
class PaperImprovementRerunReadinessGateIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperImprovementRerunReadinessGateReport:
    generated_at_utc: str
    paper_improvement_candidate_test_plan_path: str
    output_directory: str
    status: str
    ready_for_paper_improvement_acceptance_gate: bool
    selected_dataset_path: str
    safety_notice: str
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
    recommended_next_action: str
    issues: list[PaperImprovementRerunReadinessGateIssue]
    rerun_readiness_gate_items: list[PaperImprovementRerunReadinessGateItem]
    test_plan_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper improvement rerun readiness gate pack only. "
        "This pack creates paper-only rerun readiness gates from candidate test "
        "plan evidence. It does not start a dashboard UI, does not import or "
        "require Streamlit at runtime, does not run backtests, does not "
        "calculate profitability, does not select a winning strategy, does not "
        "modify strategy logic, does not connect to brokers, does not request "
        "live market data, does not place real orders, does not use real money, "
        "or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> PaperImprovementRerunReadinessGateIssue:
    return PaperImprovementRerunReadinessGateIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperImprovementRerunReadinessGateIssue]) -> str:
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


def _load_test_plan(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperImprovementRerunReadinessGateIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_improvement_candidate_test_plan_pack_missing",
                1,
                f"Paper improvement candidate test plan pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_improvement_candidate_test_plan_pack_invalid_json",
                1,
                f"Paper improvement candidate test plan pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_improvement_candidate_test_plan_pack_invalid_shape",
                1,
                "Paper improvement candidate test plan pack must be a JSON object.",
            )
        ]

    return payload, []


def _test_plan_issues(
    test_plan: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperImprovementRerunReadinessGateIssue]:
    if test_plan is None:
        return []

    issues: list[PaperImprovementRerunReadinessGateIssue] = []

    status = str(test_plan.get("status") or "unknown").lower()
    ready = bool(test_plan.get("ready_for_paper_rerun_readiness_gate"))
    missing_required = int(test_plan.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_improvement_candidate_test_plan_pack_warn",
                1,
                "Paper improvement candidate test plan pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_improvement_candidate_test_plan_pack_not_pass",
                1,
                f"Paper improvement candidate test plan pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_candidate_test_plan_pack_not_ready",
                1,
                "Paper improvement candidate test plan pack is not ready for rerun readiness gate.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_rerun_readiness_gate_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(test_plan)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_candidate_test_plan_forbidden_fields",
                len(forbidden),
                "Paper improvement candidate test plan pack contains forbidden broker/order fields.",
            )
        )

    test_plan_issues = test_plan.get("issues")
    if isinstance(test_plan_issues, list):
        fail_count = sum(
            1
            for item in test_plan_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "paper_improvement_candidate_test_plan_contains_fail_issues",
                    fail_count,
                    "Paper improvement candidate test plan pack contains fail issues.",
                )
            )

    return issues


def _test_plan_names(test_plan: Mapping[str, Any] | None) -> list[str]:
    if test_plan is None:
        return []

    raw_items = test_plan.get("test_plan_items")
    if not isinstance(raw_items, list):
        return []

    return sorted(
        {
            str(item.get("test_plan_name") or "").strip().lower()
            for item in raw_items
            if isinstance(item, Mapping) and str(item.get("test_plan_name") or "").strip()
        }
    )


def _readiness_issues(
    *,
    test_plan_names: Sequence[str],
) -> list[PaperImprovementRerunReadinessGateIssue]:
    missing_test_plans = REQUIRED_TEST_PLANS - set(test_plan_names)

    if missing_test_plans:
        return [
            _issue(
                "fail",
                "required_paper_improvement_test_plans_missing",
                len(missing_test_plans),
                "Required paper improvement candidate test plans are missing.",
            )
        ]

    return []


def _rerun_readiness_gate_items() -> list[PaperImprovementRerunReadinessGateItem]:
    raw_items = [
        (
            "git_clean_before_rerun_gate",
            "git_safety",
            "generated_output_git_guard_test_plan",
            "Operator must confirm git status is clean before any future paper rerun.",
            "not_run",
            "Generated reports/data remain ignored and uncommitted.",
        ),
        (
            "baseline_frozen_before_rerun_gate",
            "baseline",
            "baseline_documentation_test_plan",
            "Current evidence baseline must be frozen before any future rerun comparison.",
            "not_run",
            "No strategy logic modification in this pack.",
        ),
        (
            "dataset_scope_before_rerun_gate",
            "dataset",
            "dataset_scope_test_plan",
            "Dataset scope and recorded-data path must be confirmed before any rerun.",
            "not_run",
            "No live market data request.",
        ),
        (
            "ledger_quality_before_rerun_gate",
            "ledger",
            "ledger_quality_test_plan",
            "Ledger quality and missing-field checks must be reviewed before rerun.",
            "not_run",
            "No broker order fields and no real orders.",
        ),
        (
            "direction_mapping_before_rerun_gate",
            "decision_mapping",
            "direction_mapping_test_plan",
            "LONG/SHORT/NEUTRAL mapping must remain CE BUY, PE BUY, and no-trade.",
            "not_run",
            "No option selling.",
        ),
        (
            "metrics_context_before_rerun_gate",
            "metrics",
            "metrics_context_test_plan",
            "Metrics wording must remain descriptive evidence before any rerun report.",
            "not_run",
            "Not a profitability claim.",
        ),
        (
            "cost_risk_before_rerun_gate",
            "costs_and_risk",
            "cost_risk_note_test_plan",
            "Cost, slippage, and risk assumptions must remain paper-only context.",
            "not_run",
            "No real-money risk claim.",
        ),
        (
            "report_language_before_rerun_gate",
            "report_safety",
            "report_language_guard_test_plan",
            "Paper-only, no-winner, and no-profitability wording must remain present.",
            "not_run",
            "No winning strategy selection.",
        ),
        (
            "regression_tests_before_rerun_gate",
            "testing",
            "regression_test_plan_test_plan",
            "Targeted tests, smoke tests, and full quick check must pass before future implementation.",
            "not_run",
            "No untested logic change.",
        ),
        (
            "paper_only_rerun_boundary_gate",
            "rerun_control",
            "paper_rerun_boundary_test_plan",
            "Any future rerun must stay recorded-data paper/simulation unless separately gated.",
            "not_run",
            "No broker execution.",
        ),
    ]

    return [
        PaperImprovementRerunReadinessGateItem(
            item_index=index,
            gate_name=gate_name,
            gate_area=gate_area,
            evidence_source=evidence_source,
            gate_requirement=gate_requirement,
            rerun_status=rerun_status,
            safety_boundary=safety_boundary,
        )
        for index, (
            gate_name,
            gate_area,
            evidence_source,
            gate_requirement,
            rerun_status,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_paper_improvement_rerun_readiness_gate_report(
    *,
    paper_improvement_candidate_test_plan_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperImprovementRerunReadinessGateReport:
    test_plan, load_issues = _load_test_plan(paper_improvement_candidate_test_plan_path)

    issues: list[PaperImprovementRerunReadinessGateIssue] = []
    issues.extend(load_issues)
    issues.extend(_test_plan_issues(test_plan, allow_warnings=allow_warnings))

    names = _test_plan_names(test_plan)
    issues.extend(_readiness_issues(test_plan_names=names))

    gate_items = _rerun_readiness_gate_items()
    status = _status(issues)

    return PaperImprovementRerunReadinessGateReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_improvement_candidate_test_plan_path=str(paper_improvement_candidate_test_plan_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_paper_improvement_acceptance_gate=status in {"pass", "warn"},
        selected_dataset_path=str((test_plan or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        rerun_readiness_gate_item_count=len(gate_items),
        test_plan_item_count=len(names),
        candidate_registry_item_count=int(
            (test_plan or {}).get("candidate_registry_item_count") or 0
        ),
        improvement_readiness_item_count=int(
            (test_plan or {}).get("improvement_readiness_item_count") or 0
        ),
        phase_4_close_checklist_item_count=int(
            (test_plan or {}).get("phase_4_close_checklist_item_count") or 0
        ),
        close_gate_item_count=int((test_plan or {}).get("close_gate_item_count") or 0),
        report_safety_language_item_count=int(
            (test_plan or {}).get("report_safety_language_item_count") or 0
        ),
        metrics_context_item_count=int((test_plan or {}).get("metrics_context_item_count") or 0),
        ledger_snapshot_item_count=int((test_plan or {}).get("ledger_snapshot_item_count") or 0),
        analysis_item_count=int((test_plan or {}).get("analysis_item_count") or 0),
        review_summary_item_count=int((test_plan or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((test_plan or {}).get("presence_check_count") or 0),
        expected_output_count=int((test_plan or {}).get("expected_output_count") or 0),
        present_required_file_count=int((test_plan or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((test_plan or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=96,
        completed_total_after_module=97,
        phase_5_pending_before_module=3,
        phase_5_pending_after_module=2,
        full_hqe_product_estimate_after_module="89-94%",
        recommended_next_action=(
            "Build paper improvement acceptance gate next. Do not run a rerun or implement "
            "candidate changes until a separate implementation module is created and tested."
        ),
        issues=issues,
        rerun_readiness_gate_items=gate_items,
        test_plan_names=names,
    )


def write_paper_improvement_rerun_readiness_gate_report(
    report: PaperImprovementRerunReadinessGateReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    gate_json = output_dir / "paper_improvement_rerun_readiness_gate_pack.json"
    gate_txt = output_dir / "paper_improvement_rerun_readiness_gate_pack.txt"
    items_csv = output_dir / "paper_improvement_rerun_readiness_gate_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["rerun_readiness_gate_items"] = [
        asdict(item) for item in report.rerun_readiness_gate_items
    ]
    gate_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with items_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "gate_name",
                "gate_area",
                "evidence_source",
                "gate_requirement",
                "rerun_status",
                "safety_boundary",
            ]
        )
        for item in report.rerun_readiness_gate_items:
            writer.writerow(
                [
                    item.item_index,
                    item.gate_name,
                    item.gate_area,
                    item.evidence_source,
                    item.gate_requirement,
                    item.rerun_status,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Paper Improvement Rerun Readiness Gate Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for paper improvement acceptance gate: {report.ready_for_paper_improvement_acceptance_gate}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Rerun readiness gate items: {report.rerun_readiness_gate_item_count}",
        f"Test plan items carried forward: {report.test_plan_item_count}",
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
        f"- Completed total before Module SSSS: {report.completed_total_before_module} modules.",
        f"- Completed total after Module SSSS: {report.completed_total_after_module} modules.",
        f"- Phase 5 pending before Module SSSS: {report.phase_5_pending_before_module} modules.",
        f"- Phase 5 pending after Module SSSS: {report.phase_5_pending_after_module} modules.",
        f"- Full HQE product estimate after Module SSSS: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Rerun readiness gate items:",
    ]

    for item in report.rerun_readiness_gate_items:
        lines.append(f"{item.item_index}. {item.gate_name} [{item.gate_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Requirement: {item.gate_requirement}")
        lines.append(f"   Rerun status: {item.rerun_status}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Candidate test plan items carried forward:"])
    for test_plan_name in report.test_plan_names:
        lines.append(f"- {test_plan_name}")

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
        lines.append("- PASS: Paper improvement rerun readiness gate is ready.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {gate_json}",
            f"- {gate_txt}",
            f"- {items_csv}",
            f"- {manifest_json}",
        ]
    )
    gate_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "paper_improvement_rerun_readiness_gate_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_paper_improvement_acceptance_gate": report.ready_for_paper_improvement_acceptance_gate,
        "selected_dataset_path": report.selected_dataset_path,
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
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_improvement_rerun_readiness_gate_pack_json": str(gate_json),
            "paper_improvement_rerun_readiness_gate_pack_txt": str(gate_txt),
            "paper_improvement_rerun_readiness_gate_items_csv": str(items_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_improvement_rerun_readiness_gate_pack_json": gate_json,
        "paper_improvement_rerun_readiness_gate_pack_txt": gate_txt,
        "paper_improvement_rerun_readiness_gate_items_csv": items_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_improvement_rerun_readiness_gate_report(
    *,
    paper_improvement_candidate_test_plan_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperImprovementRerunReadinessGateReport, dict[str, Path]]:
    report = build_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=paper_improvement_candidate_test_plan_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_improvement_rerun_readiness_gate_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper improvement rerun readiness gate pack."
    )
    parser.add_argument(
        "--paper-improvement-candidate-test-plan",
        default=(
            "reports/paper_trading/"
            "paper_improvement_candidate_test_plan_pack/"
            "paper_improvement_candidate_test_plan_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_improvement_rerun_readiness_gate_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=Path(
            args.paper_improvement_candidate_test_plan
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper improvement rerun readiness gate pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for paper improvement acceptance gate: {report.ready_for_paper_improvement_acceptance_gate}")
    print(f"Rerun readiness gate: {outputs['paper_improvement_rerun_readiness_gate_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
