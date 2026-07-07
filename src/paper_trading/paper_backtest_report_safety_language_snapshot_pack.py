"""
Paper backtest report safety language snapshot pack.

Module MMMM in the post-v1.0 paper backtest evidence analysis sprint.

This module reads the paper backtest metrics context snapshot pack and creates
paper-only report safety language snapshot items.

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


REQUIRED_METRICS_CONTEXT_ITEMS = {
    "metrics_file_context_snapshot",
    "sample_size_context_snapshot",
    "trade_count_context_snapshot",
    "direction_distribution_context_snapshot",
    "neutral_filter_context_snapshot",
    "cost_slippage_context_snapshot",
    "risk_metric_context_snapshot",
    "metrics_limitation_context_snapshot",
    "metrics_git_guard_snapshot",
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
class PaperBacktestReportSafetyLanguageItem:
    item_index: int
    item_name: str
    language_area: str
    evidence_source: str
    wording_instruction: str
    safety_boundary: str


@dataclass(frozen=True)
class PaperBacktestReportSafetyLanguageSnapshotIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperBacktestReportSafetyLanguageSnapshotReport:
    generated_at_utc: str
    paper_backtest_metrics_context_snapshot_path: str
    output_directory: str
    status: str
    ready_for_evidence_analysis_close: bool
    selected_dataset_path: str
    safety_notice: str
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
    phase_4_pending_before_module: int
    phase_4_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_action: str
    issues: list[PaperBacktestReportSafetyLanguageSnapshotIssue]
    report_safety_language_items: list[PaperBacktestReportSafetyLanguageItem]
    metrics_context_item_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper backtest report safety language snapshot pack "
        "only. This pack creates report wording and safety language snapshot "
        "items from paper-only metrics context data. It does not start a "
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
) -> PaperBacktestReportSafetyLanguageSnapshotIssue:
    return PaperBacktestReportSafetyLanguageSnapshotIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperBacktestReportSafetyLanguageSnapshotIssue]) -> str:
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


def _load_metrics_context(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperBacktestReportSafetyLanguageSnapshotIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_backtest_metrics_context_snapshot_pack_missing",
                1,
                f"Paper backtest metrics context snapshot pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_backtest_metrics_context_snapshot_pack_invalid_json",
                1,
                f"Paper backtest metrics context snapshot pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_backtest_metrics_context_snapshot_pack_invalid_shape",
                1,
                "Paper backtest metrics context snapshot pack must be a JSON object.",
            )
        ]

    return payload, []


def _metrics_context_issues(
    metrics_context: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperBacktestReportSafetyLanguageSnapshotIssue]:
    if metrics_context is None:
        return []

    issues: list[PaperBacktestReportSafetyLanguageSnapshotIssue] = []

    status = str(metrics_context.get("status") or "unknown").lower()
    ready = bool(metrics_context.get("ready_for_report_safety_snapshot"))
    missing_required = int(metrics_context.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_backtest_metrics_context_snapshot_pack_warn",
                1,
                "Paper backtest metrics context snapshot pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_backtest_metrics_context_snapshot_pack_not_pass",
                1,
                f"Paper backtest metrics context snapshot pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_metrics_context_snapshot_pack_not_ready",
                1,
                "Paper backtest metrics context snapshot pack is not ready for report safety snapshot.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_report_safety_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(metrics_context)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_metrics_context_forbidden_fields",
                len(forbidden),
                "Paper backtest metrics context snapshot pack contains forbidden broker/order fields.",
            )
        )

    context_issues = metrics_context.get("issues")
    if isinstance(context_issues, list):
        fail_count = sum(
            1
            for item in context_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "paper_backtest_metrics_context_contains_fail_issues",
                    fail_count,
                    "Paper backtest metrics context snapshot pack contains fail issues.",
                )
            )

    return issues


def _metrics_context_item_names(metrics_context: Mapping[str, Any] | None) -> list[str]:
    if metrics_context is None:
        return []

    raw_items = metrics_context.get("metrics_context_items")
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
    metrics_context_item_names: Sequence[str],
) -> list[PaperBacktestReportSafetyLanguageSnapshotIssue]:
    missing_items = REQUIRED_METRICS_CONTEXT_ITEMS - set(metrics_context_item_names)

    if missing_items:
        return [
            _issue(
                "fail",
                "required_paper_backtest_metrics_context_items_missing",
                len(missing_items),
                "Required paper backtest metrics context items are missing.",
            )
        ]

    return []


def _report_safety_language_items() -> list[PaperBacktestReportSafetyLanguageItem]:
    raw_items = [
        (
            "paper_only_header_language",
            "header",
            "metrics_file_context_snapshot",
            "Report header must say paper/simulation evidence only.",
            "No live trading claim.",
        ),
        (
            "dataset_context_language",
            "dataset_context",
            "sample_size_context_snapshot",
            "Report should include dataset scope and sample-size context before metrics.",
            "No broad market claim.",
        ),
        (
            "descriptive_metrics_language",
            "metrics_language",
            "trade_count_context_snapshot",
            "Metrics must be described as descriptive paper evidence, not proof of profitability.",
            "Not a profitability claim.",
        ),
        (
            "direction_mapping_language",
            "decision_mapping",
            "direction_distribution_context_snapshot",
            "Report should state LONG = CE BUY paper plan, SHORT = PE BUY paper plan, and NEUTRAL = no trade.",
            "No option selling.",
        ),
        (
            "neutral_filter_language",
            "neutral_filter",
            "neutral_filter_context_snapshot",
            "Neutral/no-trade items must be described as filter behavior, not missed profit.",
            "No profit hindsight claim.",
        ),
        (
            "cost_assumption_language",
            "costs",
            "cost_slippage_context_snapshot",
            "Cost/slippage wording must say assumptions or paper evidence, not live execution results.",
            "No live-market execution claim.",
        ),
        (
            "risk_language",
            "risk_context",
            "risk_metric_context_snapshot",
            "Risk wording must be paper-only context and must not imply real-money drawdown or safety.",
            "No real-money risk claim.",
        ),
        (
            "limitation_language",
            "limitations",
            "metrics_limitation_context_snapshot",
            "Limitations and missing-data notes must appear before any operator interpretation.",
            "No strategy winner selection.",
        ),
        (
            "no_winner_language",
            "strategy_selection",
            "metrics_limitation_context_snapshot",
            "Report must not select a winning strategy from one paper evidence snapshot.",
            "No winning strategy selection.",
        ),
        (
            "git_generated_output_language",
            "git_safety",
            "metrics_git_guard_snapshot",
            "Report must remind operator that generated reports/data remain ignored and uncommitted.",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        PaperBacktestReportSafetyLanguageItem(
            item_index=index,
            item_name=item_name,
            language_area=language_area,
            evidence_source=evidence_source,
            wording_instruction=wording_instruction,
            safety_boundary=safety_boundary,
        )
        for index, (
            item_name,
            language_area,
            evidence_source,
            wording_instruction,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_paper_backtest_report_safety_language_snapshot_report(
    *,
    paper_backtest_metrics_context_snapshot_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperBacktestReportSafetyLanguageSnapshotReport:
    metrics_context, load_issues = _load_metrics_context(
        paper_backtest_metrics_context_snapshot_path
    )

    issues: list[PaperBacktestReportSafetyLanguageSnapshotIssue] = []
    issues.extend(load_issues)
    issues.extend(_metrics_context_issues(metrics_context, allow_warnings=allow_warnings))

    metrics_context_item_names = _metrics_context_item_names(metrics_context)
    issues.extend(
        _readiness_issues(metrics_context_item_names=metrics_context_item_names)
    )

    language_items = _report_safety_language_items()
    status = _status(issues)

    return PaperBacktestReportSafetyLanguageSnapshotReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_backtest_metrics_context_snapshot_path=str(paper_backtest_metrics_context_snapshot_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_evidence_analysis_close=status in {"pass", "warn"},
        selected_dataset_path=str((metrics_context or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        report_safety_language_item_count=len(language_items),
        metrics_context_item_count=len(metrics_context_item_names),
        ledger_snapshot_item_count=int((metrics_context or {}).get("ledger_snapshot_item_count") or 0),
        analysis_item_count=int((metrics_context or {}).get("analysis_item_count") or 0),
        review_summary_item_count=int((metrics_context or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((metrics_context or {}).get("presence_check_count") or 0),
        expected_output_count=int((metrics_context or {}).get("expected_output_count") or 0),
        present_required_file_count=int((metrics_context or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((metrics_context or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=90,
        completed_total_after_module=91,
        phase_4_pending_before_module=3,
        phase_4_pending_after_module=2,
        full_hqe_product_estimate_after_module="83-88%",
        recommended_next_action=(
            "Build paper evidence analysis close gate next. Keep report language paper-only, "
            "contextual, and free of profitability claims or winning-strategy selection."
        ),
        issues=issues,
        report_safety_language_items=language_items,
        metrics_context_item_names=metrics_context_item_names,
    )


def write_paper_backtest_report_safety_language_snapshot_report(
    report: PaperBacktestReportSafetyLanguageSnapshotReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_json = output_dir / "paper_backtest_report_safety_language_snapshot_pack.json"
    snapshot_txt = output_dir / "paper_backtest_report_safety_language_snapshot_pack.txt"
    items_csv = output_dir / "paper_backtest_report_safety_language_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["report_safety_language_items"] = [
        asdict(item) for item in report.report_safety_language_items
    ]
    snapshot_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with items_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "item_name",
                "language_area",
                "evidence_source",
                "wording_instruction",
                "safety_boundary",
            ]
        )
        for item in report.report_safety_language_items:
            writer.writerow(
                [
                    item.item_index,
                    item.item_name,
                    item.language_area,
                    item.evidence_source,
                    item.wording_instruction,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Paper Backtest Report Safety Language Snapshot Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for evidence analysis close: {report.ready_for_evidence_analysis_close}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Report safety language items: {report.report_safety_language_item_count}",
        f"Metrics context items carried forward: {report.metrics_context_item_count}",
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
        f"- Completed total before Module MMMM: {report.completed_total_before_module} modules.",
        f"- Completed total after Module MMMM: {report.completed_total_after_module} modules.",
        f"- Phase 4 pending before Module MMMM: {report.phase_4_pending_before_module} modules.",
        f"- Phase 4 pending after Module MMMM: {report.phase_4_pending_after_module} modules.",
        f"- Full HQE product estimate after Module MMMM: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Report safety language snapshot items:",
    ]

    for item in report.report_safety_language_items:
        lines.append(f"{item.item_index}. {item.item_name} [{item.language_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Instruction: {item.wording_instruction}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Metrics context items carried forward:"])
    for item_name in report.metrics_context_item_names:
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
        lines.append("- PASS: Paper backtest report safety language snapshot is ready.")
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
        "report_type": "paper_backtest_report_safety_language_snapshot_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_evidence_analysis_close": report.ready_for_evidence_analysis_close,
        "selected_dataset_path": report.selected_dataset_path,
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
        "phase_4_pending_after_module": report.phase_4_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_backtest_report_safety_language_snapshot_pack_json": str(snapshot_json),
            "paper_backtest_report_safety_language_snapshot_pack_txt": str(snapshot_txt),
            "paper_backtest_report_safety_language_items_csv": str(items_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_backtest_report_safety_language_snapshot_pack_json": snapshot_json,
        "paper_backtest_report_safety_language_snapshot_pack_txt": snapshot_txt,
        "paper_backtest_report_safety_language_items_csv": items_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_backtest_report_safety_language_snapshot_report(
    *,
    paper_backtest_metrics_context_snapshot_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperBacktestReportSafetyLanguageSnapshotReport, dict[str, Path]]:
    report = build_paper_backtest_report_safety_language_snapshot_report(
        paper_backtest_metrics_context_snapshot_path=paper_backtest_metrics_context_snapshot_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_backtest_report_safety_language_snapshot_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper backtest report safety language snapshot pack."
    )
    parser.add_argument(
        "--paper-backtest-metrics-context-snapshot",
        default=(
            "reports/paper_trading/"
            "paper_backtest_metrics_context_snapshot_pack/"
            "paper_backtest_metrics_context_snapshot_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_backtest_report_safety_language_snapshot_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_backtest_report_safety_language_snapshot_report(
        paper_backtest_metrics_context_snapshot_path=Path(
            args.paper_backtest_metrics_context_snapshot
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper backtest report safety language snapshot pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for evidence analysis close: {report.ready_for_evidence_analysis_close}")
    print(f"Report safety language snapshot: {outputs['paper_backtest_report_safety_language_snapshot_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
