"""
Recorded backtest review workflow close pack.

Module IIII closes the post-dashboard recorded-data paper backtest review phase.

This module reads the recorded backtest review summary pack and creates a
paper-only workflow close report.

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


REQUIRED_REVIEW_ITEMS = {
    "dataset_input_review",
    "run_order_review",
    "trade_ledger_review",
    "metrics_review",
    "report_review",
    "verification_review",
    "operator_review_checklist",
    "git_guard_review",
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
class RecordedBacktestReviewWorkflowCloseChecklistItem:
    item_index: int
    item_name: str
    status: str
    evidence: str
    next_instruction: str


@dataclass(frozen=True)
class RecordedBacktestReviewWorkflowCloseIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class RecordedBacktestReviewWorkflowCloseReport:
    generated_at_utc: str
    recorded_backtest_review_summary_path: str
    output_directory: str
    status: str
    recorded_backtest_review_workflow_closed: bool
    ready_for_next_paper_analysis_phase: bool
    selected_dataset_path: str
    safety_notice: str
    close_checklist_item_count: int
    review_summary_item_count: int
    presence_check_count: int
    expected_output_count: int
    present_required_file_count: int
    missing_required_file_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_3_pending_before_module: int
    phase_3_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_phase: str
    issues: list[RecordedBacktestReviewWorkflowCloseIssue]
    close_checklist: list[RecordedBacktestReviewWorkflowCloseChecklistItem]
    review_item_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation recorded backtest review workflow close pack only. "
        "This pack closes the recorded-data paper backtest review workflow "
        "from operator-safe review summary evidence. It does not start a "
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
) -> RecordedBacktestReviewWorkflowCloseIssue:
    return RecordedBacktestReviewWorkflowCloseIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[RecordedBacktestReviewWorkflowCloseIssue]) -> str:
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


def _load_review_summary(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[RecordedBacktestReviewWorkflowCloseIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "recorded_backtest_review_summary_pack_missing",
                1,
                f"Recorded backtest review summary pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "recorded_backtest_review_summary_pack_invalid_json",
                1,
                f"Recorded backtest review summary pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "recorded_backtest_review_summary_pack_invalid_shape",
                1,
                "Recorded backtest review summary pack must be a JSON object.",
            )
        ]

    return payload, []


def _summary_issues(
    summary: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[RecordedBacktestReviewWorkflowCloseIssue]:
    if summary is None:
        return []

    issues: list[RecordedBacktestReviewWorkflowCloseIssue] = []

    status = str(summary.get("status") or "unknown").lower()
    ready = bool(summary.get("ready_for_recorded_backtest_review_close"))
    missing_required = int(summary.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "recorded_backtest_review_summary_pack_warn",
                1,
                "Recorded backtest review summary pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_review_summary_pack_not_pass",
                1,
                f"Recorded backtest review summary pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_review_summary_pack_not_ready",
                1,
                "Recorded backtest review summary pack is not ready for workflow close.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_review_close_missing_required_files",
                missing_required,
                "Recorded-data paper backtest required files are still missing.",
            )
        )

    forbidden = _forbidden(summary)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_review_summary_forbidden_fields",
                len(forbidden),
                "Recorded backtest review summary contains forbidden broker/order fields.",
            )
        )

    summary_issues = summary.get("issues")
    if isinstance(summary_issues, list):
        fail_count = sum(
            1
            for item in summary_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "recorded_backtest_review_summary_contains_fail_issues",
                    fail_count,
                    "Recorded backtest review summary contains fail issues.",
                )
            )

    return issues


def _review_item_names(summary: Mapping[str, Any] | None) -> list[str]:
    if summary is None:
        return []

    raw_items = summary.get("review_items")
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
    review_item_names: Sequence[str],
) -> list[RecordedBacktestReviewWorkflowCloseIssue]:
    missing_items = REQUIRED_REVIEW_ITEMS - set(review_item_names)

    if missing_items:
        return [
            _issue(
                "fail",
                "required_recorded_backtest_review_items_missing",
                len(missing_items),
                "Required recorded backtest review items are missing from summary pack.",
            )
        ]

    return []


def _close_checklist(status: str) -> list[RecordedBacktestReviewWorkflowCloseChecklistItem]:
    checklist_status = "closed" if status in {"pass", "warn"} else "blocked"

    raw_items = [
        (
            "dataset_input_review_closed",
            checklist_status,
            "Dataset input review item exists in Module HHHH summary.",
            "Use same recorded dataset context for any next paper-only analysis.",
        ),
        (
            "run_order_review_closed",
            checklist_status,
            "Run order review item exists in Module HHHH summary.",
            "Keep future run steps operator-controlled and paper-only.",
        ),
        (
            "trade_ledger_review_closed",
            checklist_status,
            "Trade ledger review item exists in Module HHHH summary.",
            "Review CE/PE buy-plan mapping without real orders.",
        ),
        (
            "metrics_review_closed",
            checklist_status,
            "Metrics review item exists in Module HHHH summary.",
            "Treat metrics as evidence only, not a profit guarantee.",
        ),
        (
            "report_review_closed",
            checklist_status,
            "Report review item exists in Module HHHH summary.",
            "Do not select a winning strategy from one review pack.",
        ),
        (
            "verification_review_closed",
            checklist_status,
            "Verification review item exists in Module HHHH summary.",
            "Keep output verification before deeper paper-only analysis.",
        ),
        (
            "git_guard_review_closed",
            checklist_status,
            "Git guard review item exists in Module HHHH summary.",
            "Generated reports/data remain ignored and uncommitted.",
        ),
        (
            "safety_boundary_closed",
            checklist_status,
            "No broker orders, no live market data, no real money, no profitability claim.",
            "Next phase must remain paper-only until a separate live-readiness path is built.",
        ),
    ]

    return [
        RecordedBacktestReviewWorkflowCloseChecklistItem(
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


def build_recorded_backtest_review_workflow_close_report(
    *,
    recorded_backtest_review_summary_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> RecordedBacktestReviewWorkflowCloseReport:
    summary, load_issues = _load_review_summary(recorded_backtest_review_summary_path)

    issues: list[RecordedBacktestReviewWorkflowCloseIssue] = []
    issues.extend(load_issues)
    issues.extend(_summary_issues(summary, allow_warnings=allow_warnings))

    review_item_names = _review_item_names(summary)
    issues.extend(_readiness_issues(review_item_names=review_item_names))

    status = _status(issues)
    checklist = _close_checklist(status)

    return RecordedBacktestReviewWorkflowCloseReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        recorded_backtest_review_summary_path=str(recorded_backtest_review_summary_path),
        output_directory=str(output_dir),
        status=status,
        recorded_backtest_review_workflow_closed=status in {"pass", "warn"},
        ready_for_next_paper_analysis_phase=status in {"pass", "warn"},
        selected_dataset_path=str((summary or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        close_checklist_item_count=len(checklist),
        review_summary_item_count=int((summary or {}).get("review_summary_item_count") or len(review_item_names)),
        presence_check_count=int((summary or {}).get("presence_check_count") or 0),
        expected_output_count=int((summary or {}).get("expected_output_count") or 0),
        present_required_file_count=int((summary or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((summary or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=86,
        completed_total_after_module=87,
        phase_3_pending_before_module=1,
        phase_3_pending_after_module=0,
        full_hqe_product_estimate_after_module="79-84%",
        recommended_next_phase=(
            "Begin the next paper-only analysis phase only after confirming dataset scope, "
            "generated reports remain ignored, and no profitability claim or live execution path is introduced."
        ),
        issues=issues,
        close_checklist=checklist,
        review_item_names=review_item_names,
    )


def write_recorded_backtest_review_workflow_close_report(
    report: RecordedBacktestReviewWorkflowCloseReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    close_json = output_dir / "recorded_backtest_review_workflow_close_pack.json"
    close_txt = output_dir / "recorded_backtest_review_workflow_close_pack.txt"
    checklist_csv = output_dir / "recorded_backtest_review_workflow_close_checklist.csv"
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
        "HQE Recorded Backtest Review Workflow Close Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Recorded backtest review workflow closed: {report.recorded_backtest_review_workflow_closed}",
        f"Ready for next paper analysis phase: {report.ready_for_next_paper_analysis_phase}",
        f"Selected dataset path: {report.selected_dataset_path}",
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
        f"- Completed total before Module IIII: {report.completed_total_before_module} modules.",
        f"- Completed total after Module IIII: {report.completed_total_after_module} modules.",
        f"- Phase 3 pending before Module IIII: {report.phase_3_pending_before_module} module.",
        f"- Phase 3 pending after Module IIII: {report.phase_3_pending_after_module} modules.",
        f"- Full HQE product estimate after Module IIII: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next phase:",
        report.recommended_next_phase,
        "",
        "Close checklist:",
    ]

    for item in report.close_checklist:
        lines.append(
            (
                f"{item.item_index}. {item.item_name} [{item.status}] - "
                f"{item.evidence} Next={item.next_instruction}"
            )
        )

    lines.extend(["", "Review item names:"])
    for item_name in report.review_item_names:
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
        lines.append("- PASS: Recorded-data paper backtest review workflow is closed.")
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
        "report_type": "recorded_backtest_review_workflow_close_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "recorded_backtest_review_workflow_closed": report.recorded_backtest_review_workflow_closed,
        "ready_for_next_paper_analysis_phase": report.ready_for_next_paper_analysis_phase,
        "selected_dataset_path": report.selected_dataset_path,
        "close_checklist_item_count": report.close_checklist_item_count,
        "review_summary_item_count": report.review_summary_item_count,
        "presence_check_count": report.presence_check_count,
        "expected_output_count": report.expected_output_count,
        "present_required_file_count": report.present_required_file_count,
        "missing_required_file_count": report.missing_required_file_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_3_pending_after_module": report.phase_3_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_phase": report.recommended_next_phase,
        "safety_notice": report.safety_notice,
        "outputs": {
            "recorded_backtest_review_workflow_close_pack_json": str(close_json),
            "recorded_backtest_review_workflow_close_pack_txt": str(close_txt),
            "recorded_backtest_review_workflow_close_checklist_csv": str(checklist_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "recorded_backtest_review_workflow_close_pack_json": close_json,
        "recorded_backtest_review_workflow_close_pack_txt": close_txt,
        "recorded_backtest_review_workflow_close_checklist_csv": checklist_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_recorded_backtest_review_workflow_close_report(
    *,
    recorded_backtest_review_summary_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[RecordedBacktestReviewWorkflowCloseReport, dict[str, Path]]:
    report = build_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=recorded_backtest_review_summary_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_recorded_backtest_review_workflow_close_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build recorded-data paper backtest review workflow close pack."
    )
    parser.add_argument(
        "--recorded-backtest-review-summary",
        default=(
            "reports/paper_trading/"
            "recorded_backtest_review_summary_pack/"
            "recorded_backtest_review_summary_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_backtest_review_workflow_close_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=Path(args.recorded_backtest_review_summary),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded backtest review workflow close pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Recorded backtest review workflow closed: {report.recorded_backtest_review_workflow_closed}")
    print(f"Workflow close report: {outputs['recorded_backtest_review_workflow_close_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
