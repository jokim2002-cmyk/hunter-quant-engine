"""
Paper improvement acceptance gate pack.

Module TTTT in the post-v1.0 paper improvement readiness sprint.

This module reads the paper improvement rerun readiness gate pack and creates a
paper-only acceptance gate before the sprint close.

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


REQUIRED_RERUN_READINESS_GATES = {
    "git_clean_before_rerun_gate",
    "baseline_frozen_before_rerun_gate",
    "dataset_scope_before_rerun_gate",
    "ledger_quality_before_rerun_gate",
    "direction_mapping_before_rerun_gate",
    "metrics_context_before_rerun_gate",
    "cost_risk_before_rerun_gate",
    "report_language_before_rerun_gate",
    "regression_tests_before_rerun_gate",
    "paper_only_rerun_boundary_gate",
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
class PaperImprovementAcceptanceGateItem:
    item_index: int
    acceptance_gate_name: str
    acceptance_area: str
    evidence_source: str
    acceptance_requirement: str
    acceptance_status: str
    safety_boundary: str


@dataclass(frozen=True)
class PaperImprovementAcceptanceGateIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperImprovementAcceptanceGateReport:
    generated_at_utc: str
    paper_improvement_rerun_readiness_gate_path: str
    output_directory: str
    status: str
    ready_for_paper_improvement_readiness_close: bool
    selected_dataset_path: str
    safety_notice: str
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
    recommended_next_action: str
    issues: list[PaperImprovementAcceptanceGateIssue]
    acceptance_gate_items: list[PaperImprovementAcceptanceGateItem]
    rerun_readiness_gate_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper improvement acceptance gate pack only. This "
        "pack creates a paper-only acceptance gate from rerun readiness gate "
        "evidence before sprint close. It does not start a dashboard UI, does "
        "not import or require Streamlit at runtime, does not run backtests, "
        "does not calculate profitability, does not select a winning strategy, "
        "does not modify strategy logic, does not connect to brokers, does not "
        "request live market data, does not place real orders, does not use "
        "real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> PaperImprovementAcceptanceGateIssue:
    return PaperImprovementAcceptanceGateIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperImprovementAcceptanceGateIssue]) -> str:
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


def _load_rerun_readiness_gate(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperImprovementAcceptanceGateIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_improvement_rerun_readiness_gate_pack_missing",
                1,
                f"Paper improvement rerun readiness gate pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_improvement_rerun_readiness_gate_pack_invalid_json",
                1,
                f"Paper improvement rerun readiness gate pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_improvement_rerun_readiness_gate_pack_invalid_shape",
                1,
                "Paper improvement rerun readiness gate pack must be a JSON object.",
            )
        ]

    return payload, []


def _rerun_readiness_gate_issues(
    gate: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperImprovementAcceptanceGateIssue]:
    if gate is None:
        return []

    issues: list[PaperImprovementAcceptanceGateIssue] = []

    status = str(gate.get("status") or "unknown").lower()
    ready = bool(gate.get("ready_for_paper_improvement_acceptance_gate"))
    missing_required = int(gate.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_improvement_rerun_readiness_gate_pack_warn",
                1,
                "Paper improvement rerun readiness gate pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_improvement_rerun_readiness_gate_pack_not_pass",
                1,
                f"Paper improvement rerun readiness gate pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_rerun_readiness_gate_pack_not_ready",
                1,
                "Paper improvement rerun readiness gate pack is not ready for acceptance gate.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_acceptance_gate_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(gate)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_rerun_readiness_gate_forbidden_fields",
                len(forbidden),
                "Paper improvement rerun readiness gate pack contains forbidden broker/order fields.",
            )
        )

    gate_issues = gate.get("issues")
    if isinstance(gate_issues, list):
        fail_count = sum(
            1
            for item in gate_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "paper_improvement_rerun_readiness_gate_contains_fail_issues",
                    fail_count,
                    "Paper improvement rerun readiness gate pack contains fail issues.",
                )
            )

    return issues


def _rerun_readiness_gate_names(gate: Mapping[str, Any] | None) -> list[str]:
    if gate is None:
        return []

    raw_items = gate.get("rerun_readiness_gate_items")
    if not isinstance(raw_items, list):
        return []

    return sorted(
        {
            str(item.get("gate_name") or "").strip().lower()
            for item in raw_items
            if isinstance(item, Mapping) and str(item.get("gate_name") or "").strip()
        }
    )


def _readiness_issues(
    *,
    rerun_readiness_gate_names: Sequence[str],
) -> list[PaperImprovementAcceptanceGateIssue]:
    missing_gates = REQUIRED_RERUN_READINESS_GATES - set(rerun_readiness_gate_names)

    if missing_gates:
        return [
            _issue(
                "fail",
                "required_paper_improvement_rerun_readiness_gates_missing",
                len(missing_gates),
                "Required paper improvement rerun readiness gates are missing.",
            )
        ]

    return []


def _acceptance_gate_items() -> list[PaperImprovementAcceptanceGateItem]:
    raw_items = [
        (
            "paper_only_acceptance_gate",
            "scope",
            "paper_only_rerun_boundary_gate",
            "Sprint acceptance must remain paper/simulation only.",
            "accepted_when_source_gate_passes",
            "No broker execution.",
        ),
        (
            "no_backtest_rerun_acceptance_gate",
            "execution_boundary",
            "paper_only_rerun_boundary_gate",
            "This sprint must not execute a rerun or backtest.",
            "accepted_when_source_gate_passes",
            "No backtest execution in this pack.",
        ),
        (
            "no_strategy_change_acceptance_gate",
            "strategy_boundary",
            "baseline_frozen_before_rerun_gate",
            "Candidate planning must not modify strategy logic.",
            "accepted_when_source_gate_passes",
            "No strategy logic modification.",
        ),
        (
            "dataset_scope_acceptance_gate",
            "dataset",
            "dataset_scope_before_rerun_gate",
            "Dataset scope and recorded-data path must be preserved for future planning.",
            "accepted_when_source_gate_passes",
            "No live market data request.",
        ),
        (
            "ledger_quality_acceptance_gate",
            "ledger",
            "ledger_quality_before_rerun_gate",
            "Ledger quality notes must stay descriptive and paper-only.",
            "accepted_when_source_gate_passes",
            "No broker order fields and no real orders.",
        ),
        (
            "direction_mapping_acceptance_gate",
            "decision_mapping",
            "direction_mapping_before_rerun_gate",
            "LONG/SHORT/NEUTRAL mapping must remain CE BUY, PE BUY, and no-trade.",
            "accepted_when_source_gate_passes",
            "No option selling.",
        ),
        (
            "metrics_language_acceptance_gate",
            "metrics",
            "metrics_context_before_rerun_gate",
            "Metrics must remain descriptive evidence and not performance proof.",
            "accepted_when_source_gate_passes",
            "Not a profitability claim.",
        ),
        (
            "cost_risk_acceptance_gate",
            "costs_and_risk",
            "cost_risk_before_rerun_gate",
            "Cost, slippage, and risk wording must remain assumption/paper evidence.",
            "accepted_when_source_gate_passes",
            "No real-money risk claim.",
        ),
        (
            "report_safety_acceptance_gate",
            "report_safety",
            "report_language_before_rerun_gate",
            "Paper-only, no-winner, and no-profitability language must remain present.",
            "accepted_when_source_gate_passes",
            "No winning strategy selection.",
        ),
        (
            "test_guard_acceptance_gate",
            "testing",
            "regression_tests_before_rerun_gate",
            "Future implementation must require targeted tests, smoke tests, and full quick check.",
            "accepted_when_source_gate_passes",
            "No untested logic change.",
        ),
        (
            "git_output_acceptance_gate",
            "git_safety",
            "git_clean_before_rerun_gate",
            "Generated reports/data must remain ignored and uncommitted.",
            "accepted_when_source_gate_passes",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        PaperImprovementAcceptanceGateItem(
            item_index=index,
            acceptance_gate_name=gate_name,
            acceptance_area=area,
            evidence_source=evidence_source,
            acceptance_requirement=requirement,
            acceptance_status=status,
            safety_boundary=safety_boundary,
        )
        for index, (
            gate_name,
            area,
            evidence_source,
            requirement,
            status,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_paper_improvement_acceptance_gate_report(
    *,
    paper_improvement_rerun_readiness_gate_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperImprovementAcceptanceGateReport:
    gate, load_issues = _load_rerun_readiness_gate(
        paper_improvement_rerun_readiness_gate_path
    )

    issues: list[PaperImprovementAcceptanceGateIssue] = []
    issues.extend(load_issues)
    issues.extend(_rerun_readiness_gate_issues(gate, allow_warnings=allow_warnings))

    gate_names = _rerun_readiness_gate_names(gate)
    issues.extend(_readiness_issues(rerun_readiness_gate_names=gate_names))

    acceptance_items = _acceptance_gate_items()
    status = _status(issues)

    return PaperImprovementAcceptanceGateReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_improvement_rerun_readiness_gate_path=str(paper_improvement_rerun_readiness_gate_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_paper_improvement_readiness_close=status in {"pass", "warn"},
        selected_dataset_path=str((gate or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        acceptance_gate_item_count=len(acceptance_items),
        rerun_readiness_gate_item_count=len(gate_names),
        test_plan_item_count=int((gate or {}).get("test_plan_item_count") or 0),
        candidate_registry_item_count=int((gate or {}).get("candidate_registry_item_count") or 0),
        improvement_readiness_item_count=int((gate or {}).get("improvement_readiness_item_count") or 0),
        phase_4_close_checklist_item_count=int(
            (gate or {}).get("phase_4_close_checklist_item_count") or 0
        ),
        close_gate_item_count=int((gate or {}).get("close_gate_item_count") or 0),
        report_safety_language_item_count=int(
            (gate or {}).get("report_safety_language_item_count") or 0
        ),
        metrics_context_item_count=int((gate or {}).get("metrics_context_item_count") or 0),
        ledger_snapshot_item_count=int((gate or {}).get("ledger_snapshot_item_count") or 0),
        analysis_item_count=int((gate or {}).get("analysis_item_count") or 0),
        review_summary_item_count=int((gate or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((gate or {}).get("presence_check_count") or 0),
        expected_output_count=int((gate or {}).get("expected_output_count") or 0),
        present_required_file_count=int((gate or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((gate or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=97,
        completed_total_after_module=98,
        phase_5_pending_before_module=2,
        phase_5_pending_after_module=1,
        full_hqe_product_estimate_after_module="90-95%",
        recommended_next_action=(
            "Close Phase 5 Paper Improvement Readiness Sprint next if this acceptance gate is pass. "
            "Do not run backtests, implement candidates, or change strategy logic in the close pack."
        ),
        issues=issues,
        acceptance_gate_items=acceptance_items,
        rerun_readiness_gate_names=gate_names,
    )


def write_paper_improvement_acceptance_gate_report(
    report: PaperImprovementAcceptanceGateReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    gate_json = output_dir / "paper_improvement_acceptance_gate_pack.json"
    gate_txt = output_dir / "paper_improvement_acceptance_gate_pack.txt"
    items_csv = output_dir / "paper_improvement_acceptance_gate_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["acceptance_gate_items"] = [
        asdict(item) for item in report.acceptance_gate_items
    ]
    gate_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with items_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "acceptance_gate_name",
                "acceptance_area",
                "evidence_source",
                "acceptance_requirement",
                "acceptance_status",
                "safety_boundary",
            ]
        )
        for item in report.acceptance_gate_items:
            writer.writerow(
                [
                    item.item_index,
                    item.acceptance_gate_name,
                    item.acceptance_area,
                    item.evidence_source,
                    item.acceptance_requirement,
                    item.acceptance_status,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Paper Improvement Acceptance Gate Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for paper improvement readiness close: {report.ready_for_paper_improvement_readiness_close}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Acceptance gate items: {report.acceptance_gate_item_count}",
        f"Rerun readiness gate items carried forward: {report.rerun_readiness_gate_item_count}",
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
        f"- Completed total before Module TTTT: {report.completed_total_before_module} modules.",
        f"- Completed total after Module TTTT: {report.completed_total_after_module} modules.",
        f"- Phase 5 pending before Module TTTT: {report.phase_5_pending_before_module} modules.",
        f"- Phase 5 pending after Module TTTT: {report.phase_5_pending_after_module} module.",
        f"- Full HQE product estimate after Module TTTT: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Acceptance gate items:",
    ]

    for item in report.acceptance_gate_items:
        lines.append(f"{item.item_index}. {item.acceptance_gate_name} [{item.acceptance_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Requirement: {item.acceptance_requirement}")
        lines.append(f"   Acceptance status: {item.acceptance_status}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Rerun readiness gate names carried forward:"])
    for gate_name in report.rerun_readiness_gate_names:
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
        lines.append("- PASS: Paper improvement acceptance gate is ready.")
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
        "report_type": "paper_improvement_acceptance_gate_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_paper_improvement_readiness_close": report.ready_for_paper_improvement_readiness_close,
        "selected_dataset_path": report.selected_dataset_path,
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
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_improvement_acceptance_gate_pack_json": str(gate_json),
            "paper_improvement_acceptance_gate_pack_txt": str(gate_txt),
            "paper_improvement_acceptance_gate_items_csv": str(items_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_improvement_acceptance_gate_pack_json": gate_json,
        "paper_improvement_acceptance_gate_pack_txt": gate_txt,
        "paper_improvement_acceptance_gate_items_csv": items_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_improvement_acceptance_gate_report(
    *,
    paper_improvement_rerun_readiness_gate_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperImprovementAcceptanceGateReport, dict[str, Path]]:
    report = build_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=paper_improvement_rerun_readiness_gate_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_improvement_acceptance_gate_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper improvement acceptance gate pack."
    )
    parser.add_argument(
        "--paper-improvement-rerun-readiness-gate",
        default=(
            "reports/paper_trading/"
            "paper_improvement_rerun_readiness_gate_pack/"
            "paper_improvement_rerun_readiness_gate_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_improvement_acceptance_gate_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=Path(
            args.paper_improvement_rerun_readiness_gate
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper improvement acceptance gate pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for paper improvement readiness close: {report.ready_for_paper_improvement_readiness_close}")
    print(f"Acceptance gate: {outputs['paper_improvement_acceptance_gate_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
