"""
Paper improvement readiness launch pack.

Module PPPP starts the post-v1.0 paper improvement readiness sprint.

This module reads the paper backtest evidence analysis sprint close pack and
creates a paper-only improvement readiness launch report.

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


REQUIRED_PHASE_4_CLOSE_CHECKLIST_ITEMS = {
    "paper_only_scope_closed",
    "dataset_context_closed",
    "descriptive_metrics_closed",
    "direction_mapping_closed",
    "neutral_filter_closed",
    "cost_assumption_closed",
    "risk_language_closed",
    "limitation_language_closed",
    "no_winner_closed",
    "git_generated_output_closed",
    "phase_4_closed",
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
class PaperImprovementReadinessItem:
    item_index: int
    item_name: str
    readiness_area: str
    evidence_source: str
    readiness_instruction: str
    safety_boundary: str


@dataclass(frozen=True)
class PaperImprovementReadinessLaunchIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperImprovementReadinessLaunchReport:
    generated_at_utc: str
    paper_backtest_evidence_analysis_sprint_close_path: str
    output_directory: str
    status: str
    ready_for_paper_improvement_readiness: bool
    selected_dataset_path: str
    safety_notice: str
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
    issues: list[PaperImprovementReadinessLaunchIssue]
    improvement_readiness_items: list[PaperImprovementReadinessItem]
    phase_4_close_checklist_item_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper improvement readiness launch pack only. This "
        "pack starts a paper-only improvement readiness sprint from the paper "
        "backtest evidence analysis sprint close evidence. It does not start a "
        "dashboard UI, does not import or require Streamlit at runtime, does "
        "not run backtests, does not calculate profitability, does not select "
        "a winning strategy, does not modify strategy logic, does not connect "
        "to brokers, does not request live market data, does not place real "
        "orders, does not use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> PaperImprovementReadinessLaunchIssue:
    return PaperImprovementReadinessLaunchIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperImprovementReadinessLaunchIssue]) -> str:
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


def _load_phase_4_close(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperImprovementReadinessLaunchIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_sprint_close_pack_missing",
                1,
                f"Paper backtest evidence analysis sprint close pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_sprint_close_pack_invalid_json",
                1,
                f"Paper backtest evidence analysis sprint close pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_sprint_close_pack_invalid_shape",
                1,
                "Paper backtest evidence analysis sprint close pack must be a JSON object.",
            )
        ]

    return payload, []


def _phase_4_close_issues(
    close_pack: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperImprovementReadinessLaunchIssue]:
    if close_pack is None:
        return []

    issues: list[PaperImprovementReadinessLaunchIssue] = []

    status = str(close_pack.get("status") or "unknown").lower()
    closed = bool(close_pack.get("paper_backtest_evidence_analysis_sprint_closed"))
    ready = bool(close_pack.get("ready_for_next_paper_improvement_phase"))
    missing_required = int(close_pack.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_backtest_evidence_analysis_sprint_close_pack_warn",
                1,
                "Paper backtest evidence analysis sprint close pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_sprint_close_pack_not_pass",
                1,
                f"Paper backtest evidence analysis sprint close pack status is not pass: {status}.",
            )
        )

    if not closed:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_sprint_not_closed",
                1,
                "Paper backtest evidence analysis sprint is not closed.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_sprint_not_ready_for_improvement",
                1,
                "Paper backtest evidence analysis sprint is not ready for paper improvement readiness.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_improvement_readiness_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(close_pack)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_sprint_close_forbidden_fields",
                len(forbidden),
                "Paper backtest evidence analysis sprint close pack contains forbidden broker/order fields.",
            )
        )

    close_issues = close_pack.get("issues")
    if isinstance(close_issues, list):
        fail_count = sum(
            1
            for item in close_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "paper_backtest_evidence_analysis_sprint_close_contains_fail_issues",
                    fail_count,
                    "Paper backtest evidence analysis sprint close pack contains fail issues.",
                )
            )

    return issues


def _phase_4_close_checklist_item_names(close_pack: Mapping[str, Any] | None) -> list[str]:
    if close_pack is None:
        return []

    raw_items = close_pack.get("close_checklist")
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
    phase_4_close_checklist_item_names: Sequence[str],
) -> list[PaperImprovementReadinessLaunchIssue]:
    missing_items = (
        REQUIRED_PHASE_4_CLOSE_CHECKLIST_ITEMS - set(phase_4_close_checklist_item_names)
    )

    if missing_items:
        return [
            _issue(
                "fail",
                "required_phase_4_close_checklist_items_missing",
                len(missing_items),
                "Required Phase 4 close checklist items are missing.",
            )
        ]

    return []


def _improvement_readiness_items() -> list[PaperImprovementReadinessItem]:
    raw_items = [
        (
            "evidence_baseline_freeze",
            "baseline",
            "phase_4_closed",
            "Freeze the current paper evidence baseline before proposing improvements.",
            "No strategy logic modification in this pack.",
        ),
        (
            "dataset_scope_preservation",
            "dataset",
            "dataset_context_closed",
            "Carry dataset path, scope, and limitations into improvement planning.",
            "No live market data request.",
        ),
        (
            "ledger_issue_review",
            "ledger",
            "direction_mapping_closed",
            "Review ledger issues and CE/PE/no-trade mapping before improvement ideas.",
            "LONG = CE BUY paper plan, SHORT = PE BUY paper plan, NEUTRAL = no trade.",
        ),
        (
            "metrics_context_preservation",
            "metrics",
            "descriptive_metrics_closed",
            "Preserve metrics context as descriptive evidence only.",
            "Not a profitability claim.",
        ),
        (
            "cost_risk_context_preservation",
            "costs_and_risk",
            "cost_assumption_closed",
            "Keep cost, slippage, and risk notes as paper assumptions/evidence.",
            "No real-money risk claim.",
        ),
        (
            "report_language_guard",
            "report_safety",
            "no_winner_closed",
            "Keep no-winner and no-profitability-claim language in any next plan.",
            "No winning strategy selection.",
        ),
        (
            "candidate_improvement_log",
            "planning",
            "limitation_language_closed",
            "Create improvement candidates as review items only, not code changes.",
            "No strategy code changes in this pack.",
        ),
        (
            "regression_test_plan",
            "testing",
            "paper_only_scope_closed",
            "Plan tests required before any future strategy or report change.",
            "No untested logic change.",
        ),
        (
            "paper_rerun_boundary",
            "rerun_control",
            "paper_only_scope_closed",
            "Future reruns must remain recorded-data paper/simulation unless separately gated.",
            "No broker execution.",
        ),
        (
            "git_output_guard",
            "git_safety",
            "git_generated_output_closed",
            "Generated reports/data must remain ignored and uncommitted.",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        PaperImprovementReadinessItem(
            item_index=index,
            item_name=item_name,
            readiness_area=readiness_area,
            evidence_source=evidence_source,
            readiness_instruction=readiness_instruction,
            safety_boundary=safety_boundary,
        )
        for index, (
            item_name,
            readiness_area,
            evidence_source,
            readiness_instruction,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_paper_improvement_readiness_launch_report(
    *,
    paper_backtest_evidence_analysis_sprint_close_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperImprovementReadinessLaunchReport:
    close_pack, load_issues = _load_phase_4_close(
        paper_backtest_evidence_analysis_sprint_close_path
    )

    issues: list[PaperImprovementReadinessLaunchIssue] = []
    issues.extend(load_issues)
    issues.extend(_phase_4_close_issues(close_pack, allow_warnings=allow_warnings))

    checklist_names = _phase_4_close_checklist_item_names(close_pack)
    issues.extend(
        _readiness_issues(phase_4_close_checklist_item_names=checklist_names)
    )

    readiness_items = _improvement_readiness_items()
    status = _status(issues)

    return PaperImprovementReadinessLaunchReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_backtest_evidence_analysis_sprint_close_path=str(
            paper_backtest_evidence_analysis_sprint_close_path
        ),
        output_directory=str(output_dir),
        status=status,
        ready_for_paper_improvement_readiness=status in {"pass", "warn"},
        selected_dataset_path=str((close_pack or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        improvement_readiness_item_count=len(readiness_items),
        phase_4_close_checklist_item_count=len(checklist_names),
        close_gate_item_count=int((close_pack or {}).get("close_gate_item_count") or 0),
        report_safety_language_item_count=int(
            (close_pack or {}).get("report_safety_language_item_count") or 0
        ),
        metrics_context_item_count=int((close_pack or {}).get("metrics_context_item_count") or 0),
        ledger_snapshot_item_count=int((close_pack or {}).get("ledger_snapshot_item_count") or 0),
        analysis_item_count=int((close_pack or {}).get("analysis_item_count") or 0),
        review_summary_item_count=int((close_pack or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((close_pack or {}).get("presence_check_count") or 0),
        expected_output_count=int((close_pack or {}).get("expected_output_count") or 0),
        present_required_file_count=int((close_pack or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((close_pack or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=93,
        completed_total_after_module=94,
        phase_5_pending_before_module=6,
        phase_5_pending_after_module=5,
        full_hqe_product_estimate_after_module="86-91%",
        recommended_next_action=(
            "Build paper improvement candidate registry next. Candidate items must be planning-only "
            "until tests and paper-only gates approve any future change."
        ),
        issues=issues,
        improvement_readiness_items=readiness_items,
        phase_4_close_checklist_item_names=checklist_names,
    )


def write_paper_improvement_readiness_launch_report(
    report: PaperImprovementReadinessLaunchReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    launch_json = output_dir / "paper_improvement_readiness_launch_pack.json"
    launch_txt = output_dir / "paper_improvement_readiness_launch_pack.txt"
    items_csv = output_dir / "paper_improvement_readiness_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["improvement_readiness_items"] = [
        asdict(item) for item in report.improvement_readiness_items
    ]
    launch_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with items_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "item_name",
                "readiness_area",
                "evidence_source",
                "readiness_instruction",
                "safety_boundary",
            ]
        )
        for item in report.improvement_readiness_items:
            writer.writerow(
                [
                    item.item_index,
                    item.item_name,
                    item.readiness_area,
                    item.evidence_source,
                    item.readiness_instruction,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Paper Improvement Readiness Launch Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for paper improvement readiness: {report.ready_for_paper_improvement_readiness}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Improvement readiness items: {report.improvement_readiness_item_count}",
        f"Phase 4 close checklist items carried forward: {report.phase_4_close_checklist_item_count}",
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
        f"- Completed total before Module PPPP: {report.completed_total_before_module} modules.",
        f"- Completed total after Module PPPP: {report.completed_total_after_module} modules.",
        f"- Phase 5 pending before Module PPPP: {report.phase_5_pending_before_module} modules.",
        f"- Phase 5 pending after Module PPPP: {report.phase_5_pending_after_module} modules.",
        f"- Full HQE product estimate after Module PPPP: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Improvement readiness items:",
    ]

    for item in report.improvement_readiness_items:
        lines.append(f"{item.item_index}. {item.item_name} [{item.readiness_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Instruction: {item.readiness_instruction}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Phase 4 close checklist items carried forward:"])
    for item_name in report.phase_4_close_checklist_item_names:
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
        lines.append("- PASS: Paper improvement readiness launch is ready.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {launch_json}",
            f"- {launch_txt}",
            f"- {items_csv}",
            f"- {manifest_json}",
        ]
    )
    launch_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "paper_improvement_readiness_launch_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_paper_improvement_readiness": report.ready_for_paper_improvement_readiness,
        "selected_dataset_path": report.selected_dataset_path,
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
            "paper_improvement_readiness_launch_pack_json": str(launch_json),
            "paper_improvement_readiness_launch_pack_txt": str(launch_txt),
            "paper_improvement_readiness_items_csv": str(items_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_improvement_readiness_launch_pack_json": launch_json,
        "paper_improvement_readiness_launch_pack_txt": launch_txt,
        "paper_improvement_readiness_items_csv": items_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_improvement_readiness_launch_report(
    *,
    paper_backtest_evidence_analysis_sprint_close_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperImprovementReadinessLaunchReport, dict[str, Path]]:
    report = build_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=paper_backtest_evidence_analysis_sprint_close_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_improvement_readiness_launch_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper improvement readiness launch pack."
    )
    parser.add_argument(
        "--paper-backtest-evidence-analysis-sprint-close",
        default=(
            "reports/paper_trading/"
            "paper_backtest_evidence_analysis_sprint_close_pack/"
            "paper_backtest_evidence_analysis_sprint_close_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_improvement_readiness_launch_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=Path(
            args.paper_backtest_evidence_analysis_sprint_close
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper improvement readiness launch pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for paper improvement readiness: {report.ready_for_paper_improvement_readiness}")
    print(f"Improvement readiness launch: {outputs['paper_improvement_readiness_launch_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
