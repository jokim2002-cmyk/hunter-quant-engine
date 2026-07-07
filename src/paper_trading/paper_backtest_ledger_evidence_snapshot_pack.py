"""
Paper backtest ledger evidence snapshot pack.

Module KKKK in the post-v1.0 paper backtest evidence analysis sprint.

This module reads the paper backtest evidence analysis launch pack and creates
paper-only ledger evidence snapshot items.

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


REQUIRED_ANALYSIS_ITEMS = {
    "dataset_context_analysis",
    "ledger_integrity_analysis",
    "decision_mapping_review",
    "metrics_context_review",
    "cost_assumption_review",
    "report_safety_language_review",
    "verification_chain_review",
    "git_generated_output_guard_review",
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
class PaperBacktestLedgerSnapshotItem:
    item_index: int
    item_name: str
    ledger_area: str
    evidence_source: str
    snapshot_instruction: str
    safety_boundary: str


@dataclass(frozen=True)
class PaperBacktestLedgerEvidenceSnapshotIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperBacktestLedgerEvidenceSnapshotReport:
    generated_at_utc: str
    paper_backtest_evidence_analysis_launch_path: str
    output_directory: str
    status: str
    ready_for_metrics_context_snapshot: bool
    selected_dataset_path: str
    safety_notice: str
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
    issues: list[PaperBacktestLedgerEvidenceSnapshotIssue]
    ledger_snapshot_items: list[PaperBacktestLedgerSnapshotItem]
    analysis_item_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper backtest ledger evidence snapshot pack only. "
        "This pack creates ledger evidence snapshot items from paper-only "
        "evidence analysis launch data. It does not start a dashboard UI, "
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
) -> PaperBacktestLedgerEvidenceSnapshotIssue:
    return PaperBacktestLedgerEvidenceSnapshotIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperBacktestLedgerEvidenceSnapshotIssue]) -> str:
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


def _load_analysis_launch(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperBacktestLedgerEvidenceSnapshotIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_launch_pack_missing",
                1,
                f"Paper backtest evidence analysis launch pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_launch_pack_invalid_json",
                1,
                f"Paper backtest evidence analysis launch pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_launch_pack_invalid_shape",
                1,
                "Paper backtest evidence analysis launch pack must be a JSON object.",
            )
        ]

    return payload, []


def _analysis_launch_issues(
    launch: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperBacktestLedgerEvidenceSnapshotIssue]:
    if launch is None:
        return []

    issues: list[PaperBacktestLedgerEvidenceSnapshotIssue] = []

    status = str(launch.get("status") or "unknown").lower()
    ready = bool(launch.get("ready_for_paper_evidence_analysis"))
    missing_required = int(launch.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_backtest_evidence_analysis_launch_pack_warn",
                1,
                "Paper backtest evidence analysis launch pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_launch_pack_not_pass",
                1,
                f"Paper backtest evidence analysis launch pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_launch_pack_not_ready",
                1,
                "Paper backtest evidence analysis launch pack is not ready for evidence analysis.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_ledger_snapshot_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(launch)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_launch_forbidden_fields",
                len(forbidden),
                "Paper backtest evidence analysis launch pack contains forbidden broker/order fields.",
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
                    "paper_backtest_evidence_analysis_launch_contains_fail_issues",
                    fail_count,
                    "Paper backtest evidence analysis launch pack contains fail issues.",
                )
            )

    return issues


def _analysis_item_names(launch: Mapping[str, Any] | None) -> list[str]:
    if launch is None:
        return []

    raw_items = launch.get("analysis_items")
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
    analysis_item_names: Sequence[str],
) -> list[PaperBacktestLedgerEvidenceSnapshotIssue]:
    missing_items = REQUIRED_ANALYSIS_ITEMS - set(analysis_item_names)

    if missing_items:
        return [
            _issue(
                "fail",
                "required_paper_backtest_analysis_items_missing",
                len(missing_items),
                "Required paper backtest evidence analysis items are missing.",
            )
        ]

    return []


def _ledger_snapshot_items() -> list[PaperBacktestLedgerSnapshotItem]:
    raw_items = [
        (
            "ledger_file_context_snapshot",
            "ledger_context",
            "ledger_integrity_analysis",
            "Capture ledger path context, dataset linkage, and paper-only source notes.",
            "No live market data request.",
        ),
        (
            "ledger_schema_snapshot",
            "schema",
            "ledger_integrity_analysis",
            "Review expected ledger columns and identify missing columns as evidence notes only.",
            "No broker order fields required.",
        ),
        (
            "paper_direction_mapping_snapshot",
            "decision_mapping",
            "decision_mapping_review",
            "Confirm LONG means CE BUY paper plan, SHORT means PE BUY paper plan, and NEUTRAL means no trade.",
            "No option selling and no real orders.",
        ),
        (
            "neutral_no_trade_snapshot",
            "neutral_filter",
            "decision_mapping_review",
            "Review neutral decisions as no-trade evidence, not missed profit.",
            "Not a profitability claim.",
        ),
        (
            "entry_exit_trace_snapshot",
            "traceability",
            "ledger_integrity_analysis",
            "Review whether paper entry and exit references can be traced for operator review.",
            "Paper/simulation only.",
        ),
        (
            "cost_reference_snapshot",
            "costs",
            "cost_assumption_review",
            "Capture whether cost/slippage assumptions are labeled as assumptions, not live results.",
            "No live trading claim.",
        ),
        (
            "ledger_missing_data_snapshot",
            "data_quality",
            "ledger_integrity_analysis",
            "Capture missing rows, blank fields, or incomplete evidence as review notes.",
            "No strategy winner selection.",
        ),
        (
            "ledger_git_guard_snapshot",
            "git_safety",
            "git_generated_output_guard_review",
            "Confirm ledger/report outputs are generated artifacts and remain ignored unless explicitly allowed.",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        PaperBacktestLedgerSnapshotItem(
            item_index=index,
            item_name=item_name,
            ledger_area=ledger_area,
            evidence_source=evidence_source,
            snapshot_instruction=snapshot_instruction,
            safety_boundary=safety_boundary,
        )
        for index, (
            item_name,
            ledger_area,
            evidence_source,
            snapshot_instruction,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_paper_backtest_ledger_evidence_snapshot_report(
    *,
    paper_backtest_evidence_analysis_launch_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperBacktestLedgerEvidenceSnapshotReport:
    launch, load_issues = _load_analysis_launch(paper_backtest_evidence_analysis_launch_path)

    issues: list[PaperBacktestLedgerEvidenceSnapshotIssue] = []
    issues.extend(load_issues)
    issues.extend(_analysis_launch_issues(launch, allow_warnings=allow_warnings))

    analysis_item_names = _analysis_item_names(launch)
    issues.extend(_readiness_issues(analysis_item_names=analysis_item_names))

    snapshot_items = _ledger_snapshot_items()
    status = _status(issues)

    return PaperBacktestLedgerEvidenceSnapshotReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_backtest_evidence_analysis_launch_path=str(paper_backtest_evidence_analysis_launch_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_metrics_context_snapshot=status in {"pass", "warn"},
        selected_dataset_path=str((launch or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        ledger_snapshot_item_count=len(snapshot_items),
        analysis_item_count=len(analysis_item_names),
        review_summary_item_count=int((launch or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((launch or {}).get("presence_check_count") or 0),
        expected_output_count=int((launch or {}).get("expected_output_count") or 0),
        present_required_file_count=int((launch or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((launch or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=88,
        completed_total_after_module=89,
        phase_4_pending_before_module=5,
        phase_4_pending_after_module=4,
        full_hqe_product_estimate_after_module="81-86%",
        recommended_next_action=(
            "Build metrics context and evidence interpretation snapshots next. "
            "Keep ledger findings descriptive and avoid profitability claims or winner selection."
        ),
        issues=issues,
        ledger_snapshot_items=snapshot_items,
        analysis_item_names=analysis_item_names,
    )


def write_paper_backtest_ledger_evidence_snapshot_report(
    report: PaperBacktestLedgerEvidenceSnapshotReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_json = output_dir / "paper_backtest_ledger_evidence_snapshot_pack.json"
    snapshot_txt = output_dir / "paper_backtest_ledger_evidence_snapshot_pack.txt"
    items_csv = output_dir / "paper_backtest_ledger_snapshot_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["ledger_snapshot_items"] = [asdict(item) for item in report.ledger_snapshot_items]
    snapshot_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with items_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "item_name",
                "ledger_area",
                "evidence_source",
                "snapshot_instruction",
                "safety_boundary",
            ]
        )
        for item in report.ledger_snapshot_items:
            writer.writerow(
                [
                    item.item_index,
                    item.item_name,
                    item.ledger_area,
                    item.evidence_source,
                    item.snapshot_instruction,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Paper Backtest Ledger Evidence Snapshot Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for metrics context snapshot: {report.ready_for_metrics_context_snapshot}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Ledger snapshot items: {report.ledger_snapshot_item_count}",
        f"Analysis items carried forward: {report.analysis_item_count}",
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
        f"- Completed total before Module KKKK: {report.completed_total_before_module} modules.",
        f"- Completed total after Module KKKK: {report.completed_total_after_module} modules.",
        f"- Phase 4 pending before Module KKKK: {report.phase_4_pending_before_module} modules.",
        f"- Phase 4 pending after Module KKKK: {report.phase_4_pending_after_module} modules.",
        f"- Full HQE product estimate after Module KKKK: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Ledger evidence snapshot items:",
    ]

    for item in report.ledger_snapshot_items:
        lines.append(f"{item.item_index}. {item.item_name} [{item.ledger_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Instruction: {item.snapshot_instruction}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Analysis items carried forward:"])
    for item_name in report.analysis_item_names:
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
        lines.append("- PASS: Paper backtest ledger evidence snapshot is ready.")
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
        "report_type": "paper_backtest_ledger_evidence_snapshot_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_metrics_context_snapshot": report.ready_for_metrics_context_snapshot,
        "selected_dataset_path": report.selected_dataset_path,
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
            "paper_backtest_ledger_evidence_snapshot_pack_json": str(snapshot_json),
            "paper_backtest_ledger_evidence_snapshot_pack_txt": str(snapshot_txt),
            "paper_backtest_ledger_snapshot_items_csv": str(items_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_backtest_ledger_evidence_snapshot_pack_json": snapshot_json,
        "paper_backtest_ledger_evidence_snapshot_pack_txt": snapshot_txt,
        "paper_backtest_ledger_snapshot_items_csv": items_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_backtest_ledger_evidence_snapshot_report(
    *,
    paper_backtest_evidence_analysis_launch_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperBacktestLedgerEvidenceSnapshotReport, dict[str, Path]]:
    report = build_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=paper_backtest_evidence_analysis_launch_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_backtest_ledger_evidence_snapshot_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper backtest ledger evidence snapshot pack."
    )
    parser.add_argument(
        "--paper-backtest-evidence-analysis-launch",
        default=(
            "reports/paper_trading/"
            "paper_backtest_evidence_analysis_launch_pack/"
            "paper_backtest_evidence_analysis_launch_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_backtest_ledger_evidence_snapshot_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=Path(
            args.paper_backtest_evidence_analysis_launch
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper backtest ledger evidence snapshot pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for metrics context snapshot: {report.ready_for_metrics_context_snapshot}")
    print(f"Ledger evidence snapshot: {outputs['paper_backtest_ledger_evidence_snapshot_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
