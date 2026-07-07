"""
Paper backtest metrics context snapshot pack.

Module LLLL in the post-v1.0 paper backtest evidence analysis sprint.

This module reads the paper backtest ledger evidence snapshot pack and creates
paper-only metrics context snapshot items.

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


REQUIRED_LEDGER_SNAPSHOT_ITEMS = {
    "ledger_file_context_snapshot",
    "ledger_schema_snapshot",
    "paper_direction_mapping_snapshot",
    "neutral_no_trade_snapshot",
    "entry_exit_trace_snapshot",
    "cost_reference_snapshot",
    "ledger_missing_data_snapshot",
    "ledger_git_guard_snapshot",
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
class PaperBacktestMetricsContextItem:
    item_index: int
    item_name: str
    metrics_area: str
    evidence_source: str
    context_instruction: str
    safety_boundary: str


@dataclass(frozen=True)
class PaperBacktestMetricsContextSnapshotIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperBacktestMetricsContextSnapshotReport:
    generated_at_utc: str
    paper_backtest_ledger_evidence_snapshot_path: str
    output_directory: str
    status: str
    ready_for_report_safety_snapshot: bool
    selected_dataset_path: str
    safety_notice: str
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
    phase_4_pending_before_module: int
    phase_4_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_action: str
    issues: list[PaperBacktestMetricsContextSnapshotIssue]
    metrics_context_items: list[PaperBacktestMetricsContextItem]
    ledger_snapshot_item_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper backtest metrics context snapshot pack only. "
        "This pack creates metrics context snapshot items from paper-only "
        "ledger evidence snapshot data. It does not start a dashboard UI, "
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
) -> PaperBacktestMetricsContextSnapshotIssue:
    return PaperBacktestMetricsContextSnapshotIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperBacktestMetricsContextSnapshotIssue]) -> str:
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


def _load_ledger_snapshot(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperBacktestMetricsContextSnapshotIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_backtest_ledger_evidence_snapshot_pack_missing",
                1,
                f"Paper backtest ledger evidence snapshot pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_backtest_ledger_evidence_snapshot_pack_invalid_json",
                1,
                f"Paper backtest ledger evidence snapshot pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_backtest_ledger_evidence_snapshot_pack_invalid_shape",
                1,
                "Paper backtest ledger evidence snapshot pack must be a JSON object.",
            )
        ]

    return payload, []


def _ledger_snapshot_issues(
    snapshot: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperBacktestMetricsContextSnapshotIssue]:
    if snapshot is None:
        return []

    issues: list[PaperBacktestMetricsContextSnapshotIssue] = []

    status = str(snapshot.get("status") or "unknown").lower()
    ready = bool(snapshot.get("ready_for_metrics_context_snapshot"))
    missing_required = int(snapshot.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_backtest_ledger_evidence_snapshot_pack_warn",
                1,
                "Paper backtest ledger evidence snapshot pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_backtest_ledger_evidence_snapshot_pack_not_pass",
                1,
                f"Paper backtest ledger evidence snapshot pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_ledger_evidence_snapshot_pack_not_ready",
                1,
                "Paper backtest ledger evidence snapshot pack is not ready for metrics context snapshot.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_metrics_context_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(snapshot)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_ledger_evidence_snapshot_forbidden_fields",
                len(forbidden),
                "Paper backtest ledger evidence snapshot pack contains forbidden broker/order fields.",
            )
        )

    snapshot_issues = snapshot.get("issues")
    if isinstance(snapshot_issues, list):
        fail_count = sum(
            1
            for item in snapshot_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "paper_backtest_ledger_evidence_snapshot_contains_fail_issues",
                    fail_count,
                    "Paper backtest ledger evidence snapshot pack contains fail issues.",
                )
            )

    return issues


def _ledger_snapshot_item_names(snapshot: Mapping[str, Any] | None) -> list[str]:
    if snapshot is None:
        return []

    raw_items = snapshot.get("ledger_snapshot_items")
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
    ledger_snapshot_item_names: Sequence[str],
) -> list[PaperBacktestMetricsContextSnapshotIssue]:
    missing_items = REQUIRED_LEDGER_SNAPSHOT_ITEMS - set(ledger_snapshot_item_names)

    if missing_items:
        return [
            _issue(
                "fail",
                "required_paper_backtest_ledger_snapshot_items_missing",
                len(missing_items),
                "Required paper backtest ledger snapshot items are missing.",
            )
        ]

    return []


def _metrics_context_items() -> list[PaperBacktestMetricsContextItem]:
    raw_items = [
        (
            "metrics_file_context_snapshot",
            "metrics_context",
            "metrics_context_review",
            "Capture metrics artifact path context and confirm metrics are reviewed as descriptive evidence only.",
            "Not a profitability claim.",
        ),
        (
            "sample_size_context_snapshot",
            "sample_size",
            "ledger_file_context_snapshot",
            "Review trade count and dataset coverage context before interpreting any metric.",
            "No profit guarantee.",
        ),
        (
            "trade_count_context_snapshot",
            "trade_count",
            "ledger_schema_snapshot",
            "Capture paper trade count context and note if low sample size limits interpretation.",
            "Descriptive evidence only.",
        ),
        (
            "direction_distribution_context_snapshot",
            "direction_distribution",
            "paper_direction_mapping_snapshot",
            "Review LONG/SHORT/NEUTRAL distribution as behavior evidence, not performance proof.",
            "LONG = CE BUY paper plan, SHORT = PE BUY paper plan, NEUTRAL = no trade.",
        ),
        (
            "neutral_filter_context_snapshot",
            "neutral_filter",
            "neutral_no_trade_snapshot",
            "Review neutral/no-trade frequency as filter behavior context.",
            "Neutral does not imply missed profit.",
        ),
        (
            "cost_slippage_context_snapshot",
            "costs",
            "cost_reference_snapshot",
            "Confirm cost and slippage references are labeled as assumptions or evidence notes, not live results.",
            "No live trading claim.",
        ),
        (
            "risk_metric_context_snapshot",
            "risk_context",
            "entry_exit_trace_snapshot",
            "Review drawdown, adverse movement, or exit-related metrics only as paper evidence context.",
            "No real-money risk claim.",
        ),
        (
            "metrics_limitation_context_snapshot",
            "limitations",
            "ledger_missing_data_snapshot",
            "Capture missing data, incomplete rows, or reporting limitations before deeper analysis.",
            "No strategy winner selection.",
        ),
        (
            "metrics_git_guard_snapshot",
            "git_safety",
            "ledger_git_guard_snapshot",
            "Confirm metrics and generated reports remain ignored and uncommitted unless explicitly allowed.",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        PaperBacktestMetricsContextItem(
            item_index=index,
            item_name=item_name,
            metrics_area=metrics_area,
            evidence_source=evidence_source,
            context_instruction=context_instruction,
            safety_boundary=safety_boundary,
        )
        for index, (
            item_name,
            metrics_area,
            evidence_source,
            context_instruction,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_paper_backtest_metrics_context_snapshot_report(
    *,
    paper_backtest_ledger_evidence_snapshot_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperBacktestMetricsContextSnapshotReport:
    snapshot, load_issues = _load_ledger_snapshot(paper_backtest_ledger_evidence_snapshot_path)

    issues: list[PaperBacktestMetricsContextSnapshotIssue] = []
    issues.extend(load_issues)
    issues.extend(_ledger_snapshot_issues(snapshot, allow_warnings=allow_warnings))

    ledger_snapshot_item_names = _ledger_snapshot_item_names(snapshot)
    issues.extend(
        _readiness_issues(ledger_snapshot_item_names=ledger_snapshot_item_names)
    )

    context_items = _metrics_context_items()
    status = _status(issues)

    return PaperBacktestMetricsContextSnapshotReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_backtest_ledger_evidence_snapshot_path=str(paper_backtest_ledger_evidence_snapshot_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_report_safety_snapshot=status in {"pass", "warn"},
        selected_dataset_path=str((snapshot or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        metrics_context_item_count=len(context_items),
        ledger_snapshot_item_count=len(ledger_snapshot_item_names),
        analysis_item_count=int((snapshot or {}).get("analysis_item_count") or 0),
        review_summary_item_count=int((snapshot or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((snapshot or {}).get("presence_check_count") or 0),
        expected_output_count=int((snapshot or {}).get("expected_output_count") or 0),
        present_required_file_count=int((snapshot or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((snapshot or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=89,
        completed_total_after_module=90,
        phase_4_pending_before_module=4,
        phase_4_pending_after_module=3,
        full_hqe_product_estimate_after_module="82-87%",
        recommended_next_action=(
            "Build report safety and evidence language snapshot next. Keep metrics contextual, "
            "descriptive, and free of profitability claims or strategy winner selection."
        ),
        issues=issues,
        metrics_context_items=context_items,
        ledger_snapshot_item_names=ledger_snapshot_item_names,
    )


def write_paper_backtest_metrics_context_snapshot_report(
    report: PaperBacktestMetricsContextSnapshotReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_json = output_dir / "paper_backtest_metrics_context_snapshot_pack.json"
    snapshot_txt = output_dir / "paper_backtest_metrics_context_snapshot_pack.txt"
    items_csv = output_dir / "paper_backtest_metrics_context_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["metrics_context_items"] = [asdict(item) for item in report.metrics_context_items]
    snapshot_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with items_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "item_name",
                "metrics_area",
                "evidence_source",
                "context_instruction",
                "safety_boundary",
            ]
        )
        for item in report.metrics_context_items:
            writer.writerow(
                [
                    item.item_index,
                    item.item_name,
                    item.metrics_area,
                    item.evidence_source,
                    item.context_instruction,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Paper Backtest Metrics Context Snapshot Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for report safety snapshot: {report.ready_for_report_safety_snapshot}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Metrics context items: {report.metrics_context_item_count}",
        f"Ledger snapshot items carried forward: {report.ledger_snapshot_item_count}",
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
        f"- Completed total before Module LLLL: {report.completed_total_before_module} modules.",
        f"- Completed total after Module LLLL: {report.completed_total_after_module} modules.",
        f"- Phase 4 pending before Module LLLL: {report.phase_4_pending_before_module} modules.",
        f"- Phase 4 pending after Module LLLL: {report.phase_4_pending_after_module} modules.",
        f"- Full HQE product estimate after Module LLLL: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Metrics context snapshot items:",
    ]

    for item in report.metrics_context_items:
        lines.append(f"{item.item_index}. {item.item_name} [{item.metrics_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Instruction: {item.context_instruction}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Ledger snapshot items carried forward:"])
    for item_name in report.ledger_snapshot_item_names:
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
        lines.append("- PASS: Paper backtest metrics context snapshot is ready.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {snapshot_json}",
            f"- {snapshot_txt}",
            f"- {items_csv}",
            f"- {manifest_json}",
        ]
    )
    snapshot_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "paper_backtest_metrics_context_snapshot_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_report_safety_snapshot": report.ready_for_report_safety_snapshot,
        "selected_dataset_path": report.selected_dataset_path,
        "metrics_context_item_count": report.metrics_context_item_count,
        "ledger_snapshot_item_count": report.ledger_snapshot_item_count,
        "analysis_item_count": report.analysis_item_count,
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
            "paper_backtest_metrics_context_snapshot_pack_json": str(snapshot_json),
            "paper_backtest_metrics_context_snapshot_pack_txt": str(snapshot_txt),
            "paper_backtest_metrics_context_items_csv": str(items_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_backtest_metrics_context_snapshot_pack_json": snapshot_json,
        "paper_backtest_metrics_context_snapshot_pack_txt": snapshot_txt,
        "paper_backtest_metrics_context_items_csv": items_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_backtest_metrics_context_snapshot_report(
    *,
    paper_backtest_ledger_evidence_snapshot_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperBacktestMetricsContextSnapshotReport, dict[str, Path]]:
    report = build_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=paper_backtest_ledger_evidence_snapshot_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_backtest_metrics_context_snapshot_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper backtest metrics context snapshot pack."
    )
    parser.add_argument(
        "--paper-backtest-ledger-evidence-snapshot",
        default=(
            "reports/paper_trading/"
            "paper_backtest_ledger_evidence_snapshot_pack/"
            "paper_backtest_ledger_evidence_snapshot_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_backtest_metrics_context_snapshot_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=Path(
            args.paper_backtest_ledger_evidence_snapshot
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper backtest metrics context snapshot pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for report safety snapshot: {report.ready_for_report_safety_snapshot}")
    print(f"Metrics context snapshot: {outputs['paper_backtest_metrics_context_snapshot_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
