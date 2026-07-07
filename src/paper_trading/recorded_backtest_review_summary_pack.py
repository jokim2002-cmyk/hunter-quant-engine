"""
Recorded backtest review summary pack.

Module HHHH in the post-dashboard recorded-data paper backtest review phase.

This module reads the recorded backtest output presence verification pack and
creates a paper-only operator review summary.

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


REQUIRED_PRESENCE_OUTPUTS = {
    "real_dataset_backtest_input_pack",
    "first_real_dataset_backtest_run_pack",
    "backtest_trade_ledger",
    "backtest_metrics",
    "backtest_report",
    "first_real_backtest_output_verification",
    "first_real_backtest_report_review",
    "git_generated_outputs_guard",
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
class RecordedBacktestReviewSummaryItem:
    item_index: int
    item_name: str
    review_area: str
    evidence_source: str
    review_instruction: str
    safety_boundary: str


@dataclass(frozen=True)
class RecordedBacktestReviewSummaryIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class RecordedBacktestReviewSummaryReport:
    generated_at_utc: str
    recorded_backtest_output_presence_path: str
    output_directory: str
    status: str
    ready_for_recorded_backtest_review_close: bool
    selected_dataset_path: str
    safety_notice: str
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
    recommended_next_action: str
    issues: list[RecordedBacktestReviewSummaryIssue]
    review_items: list[RecordedBacktestReviewSummaryItem]
    presence_output_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation recorded backtest review summary pack only. This "
        "pack creates an operator review summary from verified recorded-data "
        "paper backtest output presence evidence. It does not start a dashboard "
        "UI, does not import or require Streamlit at runtime, does not run "
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
) -> RecordedBacktestReviewSummaryIssue:
    return RecordedBacktestReviewSummaryIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[RecordedBacktestReviewSummaryIssue]) -> str:
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


def _load_presence_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[RecordedBacktestReviewSummaryIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "recorded_backtest_output_presence_verification_pack_missing",
                1,
                f"Recorded backtest output presence verification pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "recorded_backtest_output_presence_verification_pack_invalid_json",
                1,
                f"Recorded backtest output presence verification pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "recorded_backtest_output_presence_verification_pack_invalid_shape",
                1,
                "Recorded backtest output presence verification pack must be a JSON object.",
            )
        ]

    return payload, []


def _presence_pack_issues(
    presence: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[RecordedBacktestReviewSummaryIssue]:
    if presence is None:
        return []

    issues: list[RecordedBacktestReviewSummaryIssue] = []

    status = str(presence.get("status") or "unknown").lower()
    ready = bool(presence.get("ready_for_recorded_backtest_review_summary"))
    missing_required = int(presence.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "recorded_backtest_output_presence_verification_pack_warn",
                1,
                "Recorded backtest output presence verification pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_output_presence_verification_pack_not_pass",
                1,
                f"Recorded backtest output presence verification pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_output_presence_verification_pack_not_ready",
                1,
                "Recorded backtest output presence verification pack is not ready for review summary.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_required_files_still_missing",
                missing_required,
                "Recorded-data paper backtest required files are still missing.",
            )
        )

    forbidden = _forbidden(presence)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_output_presence_forbidden_fields",
                len(forbidden),
                "Recorded backtest output presence pack contains forbidden broker/order fields.",
            )
        )

    presence_issues = presence.get("issues")
    if isinstance(presence_issues, list):
        fail_count = sum(
            1
            for item in presence_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "recorded_backtest_output_presence_contains_fail_issues",
                    fail_count,
                    "Recorded backtest output presence pack contains fail issues.",
                )
            )

    return issues


def _presence_output_names(presence: Mapping[str, Any] | None) -> list[str]:
    if presence is None:
        return []

    raw_checks = presence.get("presence_checks")
    if not isinstance(raw_checks, list):
        return []

    return sorted(
        {
            str(item.get("output_name") or "").strip().lower()
            for item in raw_checks
            if isinstance(item, Mapping) and str(item.get("output_name") or "").strip()
        }
    )


def _readiness_issues(
    *,
    presence_output_names: Sequence[str],
) -> list[RecordedBacktestReviewSummaryIssue]:
    missing_outputs = REQUIRED_PRESENCE_OUTPUTS - set(presence_output_names)

    if missing_outputs:
        return [
            _issue(
                "fail",
                "required_recorded_backtest_presence_outputs_missing",
                len(missing_outputs),
                "Required recorded backtest presence outputs are missing from verification pack.",
            )
        ]

    return []


def _review_items() -> list[RecordedBacktestReviewSummaryItem]:
    raw_items = [
        (
            "dataset_input_review",
            "dataset",
            "real_dataset_backtest_input_pack",
            "Confirm selected dataset path and recorded-data metadata are clear.",
            "No live market data request.",
        ),
        (
            "run_order_review",
            "workflow",
            "first_real_dataset_backtest_run_pack",
            "Confirm manual run order was prepared and followed.",
            "Paper-only workflow only.",
        ),
        (
            "trade_ledger_review",
            "ledger",
            "backtest_trade_ledger",
            "Review paper trade ledger completeness and CE/PE buy-plan mapping.",
            "No option selling and no real orders.",
        ),
        (
            "metrics_review",
            "metrics",
            "backtest_metrics",
            "Review metrics as evidence only without profit guarantee wording.",
            "Not a profitability claim.",
        ),
        (
            "report_review",
            "report",
            "backtest_report",
            "Review report text for safety boundary, dataset context, and missing-output notes.",
            "No winning strategy selection.",
        ),
        (
            "verification_review",
            "verification",
            "first_real_backtest_output_verification",
            "Confirm post-run verification pack inspected expected outputs.",
            "No broker connection.",
        ),
        (
            "operator_review_checklist",
            "review",
            "first_real_backtest_report_review",
            "Use report review checklist before deciding next paper-only analysis steps.",
            "No real money and no live execution.",
        ),
        (
            "git_guard_review",
            "git_safety",
            "git_generated_outputs_guard",
            "Confirm generated reports/data remain ignored and uncommitted.",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        RecordedBacktestReviewSummaryItem(
            item_index=index,
            item_name=item_name,
            review_area=review_area,
            evidence_source=evidence_source,
            review_instruction=review_instruction,
            safety_boundary=safety_boundary,
        )
        for index, (
            item_name,
            review_area,
            evidence_source,
            review_instruction,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_recorded_backtest_review_summary_report(
    *,
    recorded_backtest_output_presence_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> RecordedBacktestReviewSummaryReport:
    presence, load_issues = _load_presence_pack(recorded_backtest_output_presence_path)

    issues: list[RecordedBacktestReviewSummaryIssue] = []
    issues.extend(load_issues)
    issues.extend(_presence_pack_issues(presence, allow_warnings=allow_warnings))

    output_names = _presence_output_names(presence)
    issues.extend(_readiness_issues(presence_output_names=output_names))

    review_items = _review_items()
    status = _status(issues)

    return RecordedBacktestReviewSummaryReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        recorded_backtest_output_presence_path=str(recorded_backtest_output_presence_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_recorded_backtest_review_close=status in {"pass", "warn"},
        selected_dataset_path=str((presence or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        review_summary_item_count=len(review_items),
        presence_check_count=int((presence or {}).get("presence_check_count") or len(output_names)),
        expected_output_count=int((presence or {}).get("expected_output_count") or len(output_names)),
        present_required_file_count=int((presence or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((presence or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=85,
        completed_total_after_module=86,
        phase_3_pending_before_module=2,
        phase_3_pending_after_module=1,
        full_hqe_product_estimate_after_module="78-83%",
        recommended_next_action=(
            "Close the recorded-data paper backtest review workflow after confirming this "
            "summary remains paper-only and contains no profitability claim or strategy winner."
        ),
        issues=issues,
        review_items=review_items,
        presence_output_names=output_names,
    )


def write_recorded_backtest_review_summary_report(
    report: RecordedBacktestReviewSummaryReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_json = output_dir / "recorded_backtest_review_summary_pack.json"
    summary_txt = output_dir / "recorded_backtest_review_summary_pack.txt"
    summary_csv = output_dir / "recorded_backtest_review_summary_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["review_items"] = [asdict(item) for item in report.review_items]
    summary_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "item_name",
                "review_area",
                "evidence_source",
                "review_instruction",
                "safety_boundary",
            ]
        )
        for item in report.review_items:
            writer.writerow(
                [
                    item.item_index,
                    item.item_name,
                    item.review_area,
                    item.evidence_source,
                    item.review_instruction,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Recorded Backtest Review Summary Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for recorded backtest review close: {report.ready_for_recorded_backtest_review_close}",
        f"Selected dataset path: {report.selected_dataset_path}",
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
        f"- Completed total before Module HHHH: {report.completed_total_before_module} modules.",
        f"- Completed total after Module HHHH: {report.completed_total_after_module} modules.",
        f"- Phase 3 pending before Module HHHH: {report.phase_3_pending_before_module} modules.",
        f"- Phase 3 pending after Module HHHH: {report.phase_3_pending_after_module} module.",
        f"- Full HQE product estimate after Module HHHH: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Review summary items:",
    ]

    for item in report.review_items:
        lines.append(f"{item.item_index}. {item.item_name} [{item.review_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Instruction: {item.review_instruction}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Presence output names:"])
    for output_name in report.presence_output_names:
        lines.append(f"- {output_name}")

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
        lines.append("- PASS: Recorded-data paper backtest review summary is ready.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {summary_json}",
            f"- {summary_txt}",
            f"- {summary_csv}",
            f"- {manifest_json}",
        ]
    )
    summary_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_backtest_review_summary_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_recorded_backtest_review_close": report.ready_for_recorded_backtest_review_close,
        "selected_dataset_path": report.selected_dataset_path,
        "review_summary_item_count": report.review_summary_item_count,
        "presence_check_count": report.presence_check_count,
        "expected_output_count": report.expected_output_count,
        "present_required_file_count": report.present_required_file_count,
        "missing_required_file_count": report.missing_required_file_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_3_pending_after_module": report.phase_3_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "recorded_backtest_review_summary_pack_json": str(summary_json),
            "recorded_backtest_review_summary_pack_txt": str(summary_txt),
            "recorded_backtest_review_summary_items_csv": str(summary_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "recorded_backtest_review_summary_pack_json": summary_json,
        "recorded_backtest_review_summary_pack_txt": summary_txt,
        "recorded_backtest_review_summary_items_csv": summary_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_recorded_backtest_review_summary_report(
    *,
    recorded_backtest_output_presence_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[RecordedBacktestReviewSummaryReport, dict[str, Path]]:
    report = build_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=recorded_backtest_output_presence_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_recorded_backtest_review_summary_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build recorded-data paper backtest review summary pack."
    )
    parser.add_argument(
        "--recorded-backtest-output-presence",
        default=(
            "reports/paper_trading/"
            "recorded_backtest_output_presence_verification_pack/"
            "recorded_backtest_output_presence_verification_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_backtest_review_summary_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=Path(args.recorded_backtest_output_presence),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded backtest review summary pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for recorded backtest review close: {report.ready_for_recorded_backtest_review_close}")
    print(f"Recorded backtest review summary: {outputs['recorded_backtest_review_summary_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
