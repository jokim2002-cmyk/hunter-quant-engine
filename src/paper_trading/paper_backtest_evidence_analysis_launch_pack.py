"""
Paper backtest evidence analysis launch pack.

Module JJJJ starts the post-v1.0 paper backtest evidence analysis sprint.

This module reads the recorded backtest review workflow close pack and creates a
paper-only evidence analysis launch report.

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


REQUIRED_CLOSE_CHECKLIST_ITEMS = {
    "dataset_input_review_closed",
    "run_order_review_closed",
    "trade_ledger_review_closed",
    "metrics_review_closed",
    "report_review_closed",
    "verification_review_closed",
    "git_guard_review_closed",
    "safety_boundary_closed",
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
class PaperBacktestEvidenceAnalysisItem:
    item_index: int
    item_name: str
    analysis_area: str
    evidence_source: str
    analysis_instruction: str
    safety_boundary: str


@dataclass(frozen=True)
class PaperBacktestEvidenceAnalysisLaunchIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperBacktestEvidenceAnalysisLaunchReport:
    generated_at_utc: str
    recorded_backtest_review_workflow_close_path: str
    output_directory: str
    status: str
    ready_for_paper_evidence_analysis: bool
    selected_dataset_path: str
    safety_notice: str
    analysis_item_count: int
    close_checklist_item_count: int
    review_summary_item_count: int
    presence_check_count: int
    expected_output_count: int
    present_required_file_count: int
    missing_required_file_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_4_pending_before_module: int
    phase_4_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_action: str
    issues: list[PaperBacktestEvidenceAnalysisLaunchIssue]
    analysis_items: list[PaperBacktestEvidenceAnalysisItem]
    close_checklist_item_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper backtest evidence analysis launch pack only. "
        "This pack starts a paper-only evidence analysis sprint from the "
        "recorded-data paper backtest review workflow close evidence. It does "
        "not start a dashboard UI, does not import or require Streamlit at "
        "runtime, does not run backtests, does not calculate profitability, "
        "does not select a winning strategy, does not modify strategy logic, "
        "does not connect to brokers, does not request live market data, does "
        "not place real orders, does not use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> PaperBacktestEvidenceAnalysisLaunchIssue:
    return PaperBacktestEvidenceAnalysisLaunchIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperBacktestEvidenceAnalysisLaunchIssue]) -> str:
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


def _load_workflow_close(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperBacktestEvidenceAnalysisLaunchIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "recorded_backtest_review_workflow_close_pack_missing",
                1,
                f"Recorded backtest review workflow close pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "recorded_backtest_review_workflow_close_pack_invalid_json",
                1,
                f"Recorded backtest review workflow close pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "recorded_backtest_review_workflow_close_pack_invalid_shape",
                1,
                "Recorded backtest review workflow close pack must be a JSON object.",
            )
        ]

    return payload, []


def _workflow_close_issues(
    close_pack: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperBacktestEvidenceAnalysisLaunchIssue]:
    if close_pack is None:
        return []

    issues: list[PaperBacktestEvidenceAnalysisLaunchIssue] = []

    status = str(close_pack.get("status") or "unknown").lower()
    closed = bool(close_pack.get("recorded_backtest_review_workflow_closed"))
    ready = bool(close_pack.get("ready_for_next_paper_analysis_phase"))
    missing_required = int(close_pack.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "recorded_backtest_review_workflow_close_pack_warn",
                1,
                "Recorded backtest review workflow close pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_review_workflow_close_pack_not_pass",
                1,
                f"Recorded backtest review workflow close pack status is not pass: {status}.",
            )
        )

    if not closed:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_review_workflow_not_closed",
                1,
                "Recorded backtest review workflow is not closed.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_review_workflow_not_ready_for_analysis",
                1,
                "Recorded backtest review workflow is not ready for next paper analysis phase.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_evidence_analysis_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(close_pack)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_review_workflow_close_forbidden_fields",
                len(forbidden),
                "Recorded backtest review workflow close pack contains forbidden broker/order fields.",
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
                    "recorded_backtest_review_workflow_close_contains_fail_issues",
                    fail_count,
                    "Recorded backtest review workflow close pack contains fail issues.",
                )
            )

    return issues


def _close_checklist_item_names(close_pack: Mapping[str, Any] | None) -> list[str]:
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
    close_checklist_item_names: Sequence[str],
) -> list[PaperBacktestEvidenceAnalysisLaunchIssue]:
    missing_items = REQUIRED_CLOSE_CHECKLIST_ITEMS - set(close_checklist_item_names)

    if missing_items:
        return [
            _issue(
                "fail",
                "required_recorded_backtest_close_checklist_items_missing",
                len(missing_items),
                "Required recorded backtest close checklist items are missing.",
            )
        ]

    return []


def _analysis_items() -> list[PaperBacktestEvidenceAnalysisItem]:
    raw_items = [
        (
            "dataset_context_analysis",
            "dataset",
            "dataset_input_review_closed",
            "Review dataset scope, date range, symbol assumptions, and recorded-data source context.",
            "No live market data request.",
        ),
        (
            "ledger_integrity_analysis",
            "ledger",
            "trade_ledger_review_closed",
            "Check ledger completeness, paper trade rows, CE/PE buy-plan mapping, and neutral no-trade handling.",
            "No real orders and no option selling.",
        ),
        (
            "decision_mapping_review",
            "decision_logic",
            "trade_ledger_review_closed",
            "Review whether LONG maps to CE BUY paper plan, SHORT maps to PE BUY paper plan, and NEUTRAL maps to no trade.",
            "Paper-only decision review.",
        ),
        (
            "metrics_context_review",
            "metrics",
            "metrics_review_closed",
            "Review metrics as descriptive evidence with dataset context and no guarantee wording.",
            "Not a profitability claim.",
        ),
        (
            "cost_assumption_review",
            "costs",
            "metrics_review_closed",
            "Review whether any cost/slippage assumptions are clearly labeled and not presented as live results.",
            "No live trading claim.",
        ),
        (
            "report_safety_language_review",
            "report",
            "report_review_closed",
            "Review report wording for paper-only boundary, missing-output notes, and no winner selection.",
            "No winning strategy selection.",
        ),
        (
            "verification_chain_review",
            "verification",
            "verification_review_closed",
            "Review verification chain completeness before deeper paper-only analysis.",
            "No broker connection.",
        ),
        (
            "git_generated_output_guard_review",
            "git_safety",
            "git_guard_review_closed",
            "Confirm generated reports/data remain ignored and uncommitted before continuing analysis.",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        PaperBacktestEvidenceAnalysisItem(
            item_index=index,
            item_name=item_name,
            analysis_area=analysis_area,
            evidence_source=evidence_source,
            analysis_instruction=analysis_instruction,
            safety_boundary=safety_boundary,
        )
        for index, (
            item_name,
            analysis_area,
            evidence_source,
            analysis_instruction,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_paper_backtest_evidence_analysis_launch_report(
    *,
    recorded_backtest_review_workflow_close_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperBacktestEvidenceAnalysisLaunchReport:
    close_pack, load_issues = _load_workflow_close(recorded_backtest_review_workflow_close_path)

    issues: list[PaperBacktestEvidenceAnalysisLaunchIssue] = []
    issues.extend(load_issues)
    issues.extend(_workflow_close_issues(close_pack, allow_warnings=allow_warnings))

    close_checklist_item_names = _close_checklist_item_names(close_pack)
    issues.extend(
        _readiness_issues(close_checklist_item_names=close_checklist_item_names)
    )

    analysis_items = _analysis_items()
    status = _status(issues)

    return PaperBacktestEvidenceAnalysisLaunchReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        recorded_backtest_review_workflow_close_path=str(recorded_backtest_review_workflow_close_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_paper_evidence_analysis=status in {"pass", "warn"},
        selected_dataset_path=str((close_pack or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        analysis_item_count=len(analysis_items),
        close_checklist_item_count=len(close_checklist_item_names),
        review_summary_item_count=int((close_pack or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((close_pack or {}).get("presence_check_count") or 0),
        expected_output_count=int((close_pack or {}).get("expected_output_count") or 0),
        present_required_file_count=int((close_pack or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((close_pack or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=87,
        completed_total_after_module=88,
        phase_4_pending_before_module=6,
        phase_4_pending_after_module=5,
        full_hqe_product_estimate_after_module="80-85%",
        recommended_next_action=(
            "Build paper-only evidence analysis snapshots from dataset, ledger, metrics, report, "
            "verification, and Git safety evidence. Do not make profitability claims or select a winner."
        ),
        issues=issues,
        analysis_items=analysis_items,
        close_checklist_item_names=close_checklist_item_names,
    )


def write_paper_backtest_evidence_analysis_launch_report(
    report: PaperBacktestEvidenceAnalysisLaunchReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    launch_json = output_dir / "paper_backtest_evidence_analysis_launch_pack.json"
    launch_txt = output_dir / "paper_backtest_evidence_analysis_launch_pack.txt"
    items_csv = output_dir / "paper_backtest_evidence_analysis_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["analysis_items"] = [asdict(item) for item in report.analysis_items]
    launch_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with items_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "item_name",
                "analysis_area",
                "evidence_source",
                "analysis_instruction",
                "safety_boundary",
            ]
        )
        for item in report.analysis_items:
            writer.writerow(
                [
                    item.item_index,
                    item.item_name,
                    item.analysis_area,
                    item.evidence_source,
                    item.analysis_instruction,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Paper Backtest Evidence Analysis Launch Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for paper evidence analysis: {report.ready_for_paper_evidence_analysis}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Analysis items: {report.analysis_item_count}",
        f"Close checklist items: {report.close_checklist_item_count}",
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
        f"- Completed total before Module JJJJ: {report.completed_total_before_module} modules.",
        f"- Completed total after Module JJJJ: {report.completed_total_after_module} modules.",
        f"- Phase 4 pending before Module JJJJ: {report.phase_4_pending_before_module} modules.",
        f"- Phase 4 pending after Module JJJJ: {report.phase_4_pending_after_module} modules.",
        f"- Full HQE product estimate after Module JJJJ: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Evidence analysis items:",
    ]

    for item in report.analysis_items:
        lines.append(f"{item.item_index}. {item.item_name} [{item.analysis_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Instruction: {item.analysis_instruction}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Close checklist items carried forward:"])
    for item_name in report.close_checklist_item_names:
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
        lines.append("- PASS: Paper backtest evidence analysis launch is ready.")
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
        "report_type": "paper_backtest_evidence_analysis_launch_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_paper_evidence_analysis": report.ready_for_paper_evidence_analysis,
        "selected_dataset_path": report.selected_dataset_path,
        "analysis_item_count": report.analysis_item_count,
        "close_checklist_item_count": report.close_checklist_item_count,
        "review_summary_item_count": report.review_summary_item_count,
        "presence_check_count": report.presence_check_count,
        "expected_output_count": report.expected_output_count,
        "present_required_file_count": report.present_required_file_count,
        "missing_required_file_count": report.missing_required_file_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_4_pending_after_module": report.phase_4_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_backtest_evidence_analysis_launch_pack_json": str(launch_json),
            "paper_backtest_evidence_analysis_launch_pack_txt": str(launch_txt),
            "paper_backtest_evidence_analysis_items_csv": str(items_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_backtest_evidence_analysis_launch_pack_json": launch_json,
        "paper_backtest_evidence_analysis_launch_pack_txt": launch_txt,
        "paper_backtest_evidence_analysis_items_csv": items_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_backtest_evidence_analysis_launch_report(
    *,
    recorded_backtest_review_workflow_close_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperBacktestEvidenceAnalysisLaunchReport, dict[str, Path]]:
    report = build_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=recorded_backtest_review_workflow_close_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_backtest_evidence_analysis_launch_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper backtest evidence analysis launch pack."
    )
    parser.add_argument(
        "--recorded-backtest-review-workflow-close",
        default=(
            "reports/paper_trading/"
            "recorded_backtest_review_workflow_close_pack/"
            "recorded_backtest_review_workflow_close_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_backtest_evidence_analysis_launch_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=Path(
            args.recorded_backtest_review_workflow_close
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper backtest evidence analysis launch pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for paper evidence analysis: {report.ready_for_paper_evidence_analysis}")
    print(f"Evidence analysis launch: {outputs['paper_backtest_evidence_analysis_launch_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
