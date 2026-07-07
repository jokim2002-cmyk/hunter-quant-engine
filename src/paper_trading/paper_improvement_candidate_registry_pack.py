"""
Paper improvement candidate registry pack.

Module QQQQ in the post-v1.0 paper improvement readiness sprint.

This module reads the paper improvement readiness launch pack and creates a
planning-only paper improvement candidate registry.

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


REQUIRED_READINESS_ITEMS = {
    "evidence_baseline_freeze",
    "dataset_scope_preservation",
    "ledger_issue_review",
    "metrics_context_preservation",
    "cost_risk_context_preservation",
    "report_language_guard",
    "candidate_improvement_log",
    "regression_test_plan",
    "paper_rerun_boundary",
    "git_output_guard",
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
class PaperImprovementCandidateRegistryItem:
    item_index: int
    candidate_name: str
    candidate_area: str
    evidence_source: str
    candidate_instruction: str
    implementation_status: str
    safety_boundary: str


@dataclass(frozen=True)
class PaperImprovementCandidateRegistryIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperImprovementCandidateRegistryReport:
    generated_at_utc: str
    paper_improvement_readiness_launch_path: str
    output_directory: str
    status: str
    ready_for_candidate_test_plan: bool
    selected_dataset_path: str
    safety_notice: str
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
    issues: list[PaperImprovementCandidateRegistryIssue]
    candidate_registry_items: list[PaperImprovementCandidateRegistryItem]
    improvement_readiness_item_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper improvement candidate registry pack only. "
        "This pack creates a planning-only improvement candidate registry from "
        "paper improvement readiness evidence. It does not start a dashboard UI, "
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
) -> PaperImprovementCandidateRegistryIssue:
    return PaperImprovementCandidateRegistryIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperImprovementCandidateRegistryIssue]) -> str:
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


def _load_readiness_launch(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperImprovementCandidateRegistryIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_improvement_readiness_launch_pack_missing",
                1,
                f"Paper improvement readiness launch pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_improvement_readiness_launch_pack_invalid_json",
                1,
                f"Paper improvement readiness launch pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_improvement_readiness_launch_pack_invalid_shape",
                1,
                "Paper improvement readiness launch pack must be a JSON object.",
            )
        ]

    return payload, []


def _readiness_launch_issues(
    launch: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperImprovementCandidateRegistryIssue]:
    if launch is None:
        return []

    issues: list[PaperImprovementCandidateRegistryIssue] = []

    status = str(launch.get("status") or "unknown").lower()
    ready = bool(launch.get("ready_for_paper_improvement_readiness"))
    missing_required = int(launch.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_improvement_readiness_launch_pack_warn",
                1,
                "Paper improvement readiness launch pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_improvement_readiness_launch_pack_not_pass",
                1,
                f"Paper improvement readiness launch pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_readiness_launch_pack_not_ready",
                1,
                "Paper improvement readiness launch pack is not ready for candidate registry.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_candidate_registry_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(launch)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_readiness_launch_forbidden_fields",
                len(forbidden),
                "Paper improvement readiness launch pack contains forbidden broker/order fields.",
            )
        )

    launch_issues = launch.get("issues")
    if isinstance(launch_issues, list):
        fail_count = sum(
            1
            for item in launch_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "paper_improvement_readiness_launch_contains_fail_issues",
                    fail_count,
                    "Paper improvement readiness launch pack contains fail issues.",
                )
            )

    return issues


def _readiness_item_names(launch: Mapping[str, Any] | None) -> list[str]:
    if launch is None:
        return []

    raw_items = launch.get("improvement_readiness_items")
    if not isinstance(raw_items, list):
        return []

    return sorted(
        {
            str(item.get("item_name") or "").strip().lower()
            for item in raw_items
            if isinstance(item, Mapping) and str(item.get("item_name") or "").strip()
        }
    )


def _readiness_issues(
    *,
    readiness_item_names: Sequence[str],
) -> list[PaperImprovementCandidateRegistryIssue]:
    missing_items = REQUIRED_READINESS_ITEMS - set(readiness_item_names)

    if missing_items:
        return [
            _issue(
                "fail",
                "required_paper_improvement_readiness_items_missing",
                len(missing_items),
                "Required paper improvement readiness items are missing.",
            )
        ]

    return []


def _candidate_registry_items() -> list[PaperImprovementCandidateRegistryItem]:
    raw_items = [
        (
            "baseline_documentation_candidate",
            "baseline",
            "evidence_baseline_freeze",
            "Document the current paper evidence baseline before any future change is proposed.",
            "planning_only",
            "No strategy logic modification in this pack.",
        ),
        (
            "dataset_scope_review_candidate",
            "dataset",
            "dataset_scope_preservation",
            "Create a candidate to improve dataset scope notes and recorded-data coverage labels.",
            "planning_only",
            "No live market data request.",
        ),
        (
            "ledger_quality_review_candidate",
            "ledger",
            "ledger_issue_review",
            "Create a candidate to review ledger missing fields, row completeness, and traceability notes.",
            "planning_only",
            "No real orders and no broker fields.",
        ),
        (
            "direction_mapping_review_candidate",
            "decision_mapping",
            "ledger_issue_review",
            "Create a candidate to reinforce LONG/SHORT/NEUTRAL paper mapping checks.",
            "planning_only",
            "LONG = CE BUY paper plan, SHORT = PE BUY paper plan, NEUTRAL = no trade.",
        ),
        (
            "metrics_context_review_candidate",
            "metrics",
            "metrics_context_preservation",
            "Create a candidate to improve sample-size, trade-count, and descriptive metric context.",
            "planning_only",
            "Not a profitability claim.",
        ),
        (
            "cost_risk_note_candidate",
            "costs_and_risk",
            "cost_risk_context_preservation",
            "Create a candidate to improve cost, slippage, risk, and limitation notes.",
            "planning_only",
            "No real-money risk claim.",
        ),
        (
            "report_language_guard_candidate",
            "report_safety",
            "report_language_guard",
            "Create a candidate to strengthen paper-only, no-winner, and no-profitability wording.",
            "planning_only",
            "No winning strategy selection.",
        ),
        (
            "regression_test_candidate",
            "testing",
            "regression_test_plan",
            "Create a candidate for required tests before any future improvement implementation.",
            "planning_only",
            "No untested logic change.",
        ),
        (
            "paper_rerun_candidate",
            "rerun_control",
            "paper_rerun_boundary",
            "Create a candidate for future recorded-data paper rerun guardrails.",
            "planning_only",
            "No broker execution.",
        ),
        (
            "generated_output_git_guard_candidate",
            "git_safety",
            "git_output_guard",
            "Create a candidate to preserve generated report/data ignore and commit safety.",
            "planning_only",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        PaperImprovementCandidateRegistryItem(
            item_index=index,
            candidate_name=candidate_name,
            candidate_area=candidate_area,
            evidence_source=evidence_source,
            candidate_instruction=candidate_instruction,
            implementation_status=implementation_status,
            safety_boundary=safety_boundary,
        )
        for index, (
            candidate_name,
            candidate_area,
            evidence_source,
            candidate_instruction,
            implementation_status,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_paper_improvement_candidate_registry_report(
    *,
    paper_improvement_readiness_launch_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperImprovementCandidateRegistryReport:
    launch, load_issues = _load_readiness_launch(paper_improvement_readiness_launch_path)

    issues: list[PaperImprovementCandidateRegistryIssue] = []
    issues.extend(load_issues)
    issues.extend(_readiness_launch_issues(launch, allow_warnings=allow_warnings))

    readiness_names = _readiness_item_names(launch)
    issues.extend(_readiness_issues(readiness_item_names=readiness_names))

    candidates = _candidate_registry_items()
    status = _status(issues)

    return PaperImprovementCandidateRegistryReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_improvement_readiness_launch_path=str(paper_improvement_readiness_launch_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_candidate_test_plan=status in {"pass", "warn"},
        selected_dataset_path=str((launch or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        candidate_registry_item_count=len(candidates),
        improvement_readiness_item_count=len(readiness_names),
        phase_4_close_checklist_item_count=int(
            (launch or {}).get("phase_4_close_checklist_item_count") or 0
        ),
        close_gate_item_count=int((launch or {}).get("close_gate_item_count") or 0),
        report_safety_language_item_count=int(
            (launch or {}).get("report_safety_language_item_count") or 0
        ),
        metrics_context_item_count=int((launch or {}).get("metrics_context_item_count") or 0),
        ledger_snapshot_item_count=int((launch or {}).get("ledger_snapshot_item_count") or 0),
        analysis_item_count=int((launch or {}).get("analysis_item_count") or 0),
        review_summary_item_count=int((launch or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((launch or {}).get("presence_check_count") or 0),
        expected_output_count=int((launch or {}).get("expected_output_count") or 0),
        present_required_file_count=int((launch or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((launch or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=94,
        completed_total_after_module=95,
        phase_5_pending_before_module=5,
        phase_5_pending_after_module=4,
        full_hqe_product_estimate_after_module="87-92%",
        recommended_next_action=(
            "Build candidate test plan next. Do not implement any candidate until test coverage, "
            "paper-only rerun boundaries, and safety language gates are created."
        ),
        issues=issues,
        candidate_registry_items=candidates,
        improvement_readiness_item_names=readiness_names,
    )


def write_paper_improvement_candidate_registry_report(
    report: PaperImprovementCandidateRegistryReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    registry_json = output_dir / "paper_improvement_candidate_registry_pack.json"
    registry_txt = output_dir / "paper_improvement_candidate_registry_pack.txt"
    items_csv = output_dir / "paper_improvement_candidate_registry_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["candidate_registry_items"] = [
        asdict(item) for item in report.candidate_registry_items
    ]
    registry_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with items_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "candidate_name",
                "candidate_area",
                "evidence_source",
                "candidate_instruction",
                "implementation_status",
                "safety_boundary",
            ]
        )
        for item in report.candidate_registry_items:
            writer.writerow(
                [
                    item.item_index,
                    item.candidate_name,
                    item.candidate_area,
                    item.evidence_source,
                    item.candidate_instruction,
                    item.implementation_status,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Paper Improvement Candidate Registry Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for candidate test plan: {report.ready_for_candidate_test_plan}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Candidate registry items: {report.candidate_registry_item_count}",
        f"Improvement readiness items carried forward: {report.improvement_readiness_item_count}",
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
        f"- Completed total before Module QQQQ: {report.completed_total_before_module} modules.",
        f"- Completed total after Module QQQQ: {report.completed_total_after_module} modules.",
        f"- Phase 5 pending before Module QQQQ: {report.phase_5_pending_before_module} modules.",
        f"- Phase 5 pending after Module QQQQ: {report.phase_5_pending_after_module} modules.",
        f"- Full HQE product estimate after Module QQQQ: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Candidate registry items:",
    ]

    for item in report.candidate_registry_items:
        lines.append(f"{item.item_index}. {item.candidate_name} [{item.candidate_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Instruction: {item.candidate_instruction}")
        lines.append(f"   Implementation status: {item.implementation_status}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Improvement readiness items carried forward:"])
    for item_name in report.improvement_readiness_item_names:
        lines.append(f"- {item_name}")

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
        lines.append("- PASS: Paper improvement candidate registry is ready.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {registry_json}",
            f"- {registry_txt}",
            f"- {items_csv}",
            f"- {manifest_json}",
        ]
    )
    registry_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "paper_improvement_candidate_registry_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_candidate_test_plan": report.ready_for_candidate_test_plan,
        "selected_dataset_path": report.selected_dataset_path,
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
            "paper_improvement_candidate_registry_pack_json": str(registry_json),
            "paper_improvement_candidate_registry_pack_txt": str(registry_txt),
            "paper_improvement_candidate_registry_items_csv": str(items_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_improvement_candidate_registry_pack_json": registry_json,
        "paper_improvement_candidate_registry_pack_txt": registry_txt,
        "paper_improvement_candidate_registry_items_csv": items_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_improvement_candidate_registry_report(
    *,
    paper_improvement_readiness_launch_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperImprovementCandidateRegistryReport, dict[str, Path]]:
    report = build_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=paper_improvement_readiness_launch_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_improvement_candidate_registry_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper improvement candidate registry pack."
    )
    parser.add_argument(
        "--paper-improvement-readiness-launch",
        default=(
            "reports/paper_trading/"
            "paper_improvement_readiness_launch_pack/"
            "paper_improvement_readiness_launch_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_improvement_candidate_registry_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=Path(
            args.paper_improvement_readiness_launch
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper improvement candidate registry pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for candidate test plan: {report.ready_for_candidate_test_plan}")
    print(f"Candidate registry: {outputs['paper_improvement_candidate_registry_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
