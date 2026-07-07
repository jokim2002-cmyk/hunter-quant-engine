"""
Paper backtest evidence analysis close gate pack.

Module NNNN in the post-v1.0 paper backtest evidence analysis sprint.

This module reads the paper backtest report safety language snapshot pack and
creates a paper-only close gate for the evidence analysis sprint.

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


REQUIRED_REPORT_SAFETY_LANGUAGE_ITEMS = {
    "paper_only_header_language",
    "dataset_context_language",
    "descriptive_metrics_language",
    "direction_mapping_language",
    "neutral_filter_language",
    "cost_assumption_language",
    "risk_language",
    "limitation_language",
    "no_winner_language",
    "git_generated_output_language",
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
class PaperBacktestEvidenceAnalysisCloseGateItem:
    item_index: int
    gate_name: str
    gate_area: str
    evidence_source: str
    gate_requirement: str
    safety_boundary: str


@dataclass(frozen=True)
class PaperBacktestEvidenceAnalysisCloseGateIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperBacktestEvidenceAnalysisCloseGateReport:
    generated_at_utc: str
    paper_backtest_report_safety_language_snapshot_path: str
    output_directory: str
    status: str
    ready_for_phase_4_close: bool
    selected_dataset_path: str
    safety_notice: str
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
    phase_4_pending_before_module: int
    phase_4_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_action: str
    issues: list[PaperBacktestEvidenceAnalysisCloseGateIssue]
    close_gate_items: list[PaperBacktestEvidenceAnalysisCloseGateItem]
    report_safety_language_item_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper backtest evidence analysis close gate pack only. "
        "This pack creates the final paper-only close gate before closing the "
        "paper backtest evidence analysis sprint. It does not start a dashboard "
        "UI, does not import or require Streamlit at runtime, does not run "
        "backtests, does not calculate profitability, does not select a winning "
        "strategy, does not modify strategy logic, does not connect to brokers, "
        "does not request live market data, does not place real orders, does "
        "not use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> PaperBacktestEvidenceAnalysisCloseGateIssue:
    return PaperBacktestEvidenceAnalysisCloseGateIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperBacktestEvidenceAnalysisCloseGateIssue]) -> str:
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


def _load_report_safety_snapshot(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperBacktestEvidenceAnalysisCloseGateIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_backtest_report_safety_language_snapshot_pack_missing",
                1,
                f"Paper backtest report safety language snapshot pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_backtest_report_safety_language_snapshot_pack_invalid_json",
                1,
                f"Paper backtest report safety language snapshot pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_backtest_report_safety_language_snapshot_pack_invalid_shape",
                1,
                "Paper backtest report safety language snapshot pack must be a JSON object.",
            )
        ]

    return payload, []


def _report_safety_snapshot_issues(
    snapshot: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperBacktestEvidenceAnalysisCloseGateIssue]:
    if snapshot is None:
        return []

    issues: list[PaperBacktestEvidenceAnalysisCloseGateIssue] = []

    status = str(snapshot.get("status") or "unknown").lower()
    ready = bool(snapshot.get("ready_for_evidence_analysis_close"))
    missing_required = int(snapshot.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_backtest_report_safety_language_snapshot_pack_warn",
                1,
                "Paper backtest report safety language snapshot pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_backtest_report_safety_language_snapshot_pack_not_pass",
                1,
                f"Paper backtest report safety language snapshot pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_report_safety_language_snapshot_pack_not_ready",
                1,
                "Paper backtest report safety language snapshot pack is not ready for evidence analysis close.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_close_gate_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(snapshot)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_report_safety_language_snapshot_forbidden_fields",
                len(forbidden),
                "Paper backtest report safety language snapshot pack contains forbidden broker/order fields.",
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
                    "paper_backtest_report_safety_language_snapshot_contains_fail_issues",
                    fail_count,
                    "Paper backtest report safety language snapshot pack contains fail issues.",
                )
            )

    return issues


def _report_safety_language_item_names(snapshot: Mapping[str, Any] | None) -> list[str]:
    if snapshot is None:
        return []

    raw_items = snapshot.get("report_safety_language_items")
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
    report_safety_language_item_names: Sequence[str],
) -> list[PaperBacktestEvidenceAnalysisCloseGateIssue]:
    missing_items = REQUIRED_REPORT_SAFETY_LANGUAGE_ITEMS - set(report_safety_language_item_names)

    if missing_items:
        return [
            _issue(
                "fail",
                "required_paper_backtest_report_safety_language_items_missing",
                len(missing_items),
                "Required paper backtest report safety language items are missing.",
            )
        ]

    return []


def _close_gate_items() -> list[PaperBacktestEvidenceAnalysisCloseGateItem]:
    raw_items = [
        (
            "paper_only_scope_gate",
            "scope",
            "paper_only_header_language",
            "Evidence analysis output must remain paper/simulation only.",
            "No live trading claim.",
        ),
        (
            "dataset_context_gate",
            "dataset",
            "dataset_context_language",
            "Dataset context must be visible before interpretation.",
            "No broad market claim.",
        ),
        (
            "descriptive_metrics_gate",
            "metrics",
            "descriptive_metrics_language",
            "Metrics must be framed as descriptive paper evidence.",
            "Not a profitability claim.",
        ),
        (
            "direction_mapping_gate",
            "decision_mapping",
            "direction_mapping_language",
            "LONG/SHORT/NEUTRAL mapping must remain CE BUY, PE BUY, and no-trade respectively.",
            "No option selling.",
        ),
        (
            "neutral_filter_gate",
            "neutral_filter",
            "neutral_filter_language",
            "Neutral/no-trade language must avoid hindsight or missed-profit claims.",
            "No missed profit claim.",
        ),
        (
            "cost_assumption_gate",
            "costs",
            "cost_assumption_language",
            "Cost/slippage language must stay assumption/evidence based.",
            "No live execution result claim.",
        ),
        (
            "risk_language_gate",
            "risk",
            "risk_language",
            "Risk language must remain paper-only and not imply real-money safety.",
            "No real-money risk claim.",
        ),
        (
            "limitation_language_gate",
            "limitations",
            "limitation_language",
            "Limitations and missing-data notes must be retained.",
            "No overfitting or certainty claim.",
        ),
        (
            "no_winner_gate",
            "strategy_selection",
            "no_winner_language",
            "No winning strategy can be selected from this paper evidence analysis sprint.",
            "No winning strategy selection.",
        ),
        (
            "git_generated_output_gate",
            "git_safety",
            "git_generated_output_language",
            "Generated reports/data must remain ignored and uncommitted unless explicitly allowed.",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        PaperBacktestEvidenceAnalysisCloseGateItem(
            item_index=index,
            gate_name=gate_name,
            gate_area=gate_area,
            evidence_source=evidence_source,
            gate_requirement=gate_requirement,
            safety_boundary=safety_boundary,
        )
        for index, (
            gate_name,
            gate_area,
            evidence_source,
            gate_requirement,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_paper_backtest_evidence_analysis_close_gate_report(
    *,
    paper_backtest_report_safety_language_snapshot_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperBacktestEvidenceAnalysisCloseGateReport:
    snapshot, load_issues = _load_report_safety_snapshot(
        paper_backtest_report_safety_language_snapshot_path
    )

    issues: list[PaperBacktestEvidenceAnalysisCloseGateIssue] = []
    issues.extend(load_issues)
    issues.extend(
        _report_safety_snapshot_issues(snapshot, allow_warnings=allow_warnings)
    )

    item_names = _report_safety_language_item_names(snapshot)
    issues.extend(_readiness_issues(report_safety_language_item_names=item_names))

    gate_items = _close_gate_items()
    status = _status(issues)

    return PaperBacktestEvidenceAnalysisCloseGateReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_backtest_report_safety_language_snapshot_path=str(
            paper_backtest_report_safety_language_snapshot_path
        ),
        output_directory=str(output_dir),
        status=status,
        ready_for_phase_4_close=status in {"pass", "warn"},
        selected_dataset_path=str((snapshot or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        close_gate_item_count=len(gate_items),
        report_safety_language_item_count=len(item_names),
        metrics_context_item_count=int((snapshot or {}).get("metrics_context_item_count") or 0),
        ledger_snapshot_item_count=int((snapshot or {}).get("ledger_snapshot_item_count") or 0),
        analysis_item_count=int((snapshot or {}).get("analysis_item_count") or 0),
        review_summary_item_count=int((snapshot or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((snapshot or {}).get("presence_check_count") or 0),
        expected_output_count=int((snapshot or {}).get("expected_output_count") or 0),
        present_required_file_count=int((snapshot or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((snapshot or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=91,
        completed_total_after_module=92,
        phase_4_pending_before_module=2,
        phase_4_pending_after_module=1,
        full_hqe_product_estimate_after_module="84-89%",
        recommended_next_action=(
            "Close Phase 4 Paper Backtest Evidence Analysis Sprint next only if this gate is pass "
            "and safety language remains free of profitability claims or winner selection."
        ),
        issues=issues,
        close_gate_items=gate_items,
        report_safety_language_item_names=item_names,
    )


def write_paper_backtest_evidence_analysis_close_gate_report(
    report: PaperBacktestEvidenceAnalysisCloseGateReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    gate_json = output_dir / "paper_backtest_evidence_analysis_close_gate_pack.json"
    gate_txt = output_dir / "paper_backtest_evidence_analysis_close_gate_pack.txt"
    gate_csv = output_dir / "paper_backtest_evidence_analysis_close_gate_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["close_gate_items"] = [asdict(item) for item in report.close_gate_items]
    gate_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with gate_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "gate_name",
                "gate_area",
                "evidence_source",
                "gate_requirement",
                "safety_boundary",
            ]
        )
        for item in report.close_gate_items:
            writer.writerow(
                [
                    item.item_index,
                    item.gate_name,
                    item.gate_area,
                    item.evidence_source,
                    item.gate_requirement,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Paper Backtest Evidence Analysis Close Gate Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for Phase 4 close: {report.ready_for_phase_4_close}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Close gate items: {report.close_gate_item_count}",
        f"Report safety language items carried forward: {report.report_safety_language_item_count}",
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
        f"- Completed total before Module NNNN: {report.completed_total_before_module} modules.",
        f"- Completed total after Module NNNN: {report.completed_total_after_module} modules.",
        f"- Phase 4 pending before Module NNNN: {report.phase_4_pending_before_module} modules.",
        f"- Phase 4 pending after Module NNNN: {report.phase_4_pending_after_module} module.",
        f"- Full HQE product estimate after Module NNNN: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Close gate items:",
    ]

    for item in report.close_gate_items:
        lines.append(f"{item.item_index}. {item.gate_name} [{item.gate_area}]")
        lines.append(f"   Evidence: {item.evidence_source}")
        lines.append(f"   Requirement: {item.gate_requirement}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Report safety language items carried forward:"])
    for item_name in report.report_safety_language_item_names:
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
        lines.append("- PASS: Paper backtest evidence analysis close gate is ready.")
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
            f"- {gate_csv}",
            f"- {manifest_json}",
        ]
    )
    gate_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "paper_backtest_evidence_analysis_close_gate_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_phase_4_close": report.ready_for_phase_4_close,
        "selected_dataset_path": report.selected_dataset_path,
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
        "phase_4_pending_after_module": report.phase_4_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_backtest_evidence_analysis_close_gate_pack_json": str(gate_json),
            "paper_backtest_evidence_analysis_close_gate_pack_txt": str(gate_txt),
            "paper_backtest_evidence_analysis_close_gate_items_csv": str(gate_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_backtest_evidence_analysis_close_gate_pack_json": gate_json,
        "paper_backtest_evidence_analysis_close_gate_pack_txt": gate_txt,
        "paper_backtest_evidence_analysis_close_gate_items_csv": gate_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_backtest_evidence_analysis_close_gate_report(
    *,
    paper_backtest_report_safety_language_snapshot_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperBacktestEvidenceAnalysisCloseGateReport, dict[str, Path]]:
    report = build_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=paper_backtest_report_safety_language_snapshot_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_backtest_evidence_analysis_close_gate_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper backtest evidence analysis close gate pack."
    )
    parser.add_argument(
        "--paper-backtest-report-safety-language-snapshot",
        default=(
            "reports/paper_trading/"
            "paper_backtest_report_safety_language_snapshot_pack/"
            "paper_backtest_report_safety_language_snapshot_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_backtest_evidence_analysis_close_gate_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=Path(
            args.paper_backtest_report_safety_language_snapshot
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper backtest evidence analysis close gate pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for Phase 4 close: {report.ready_for_phase_4_close}")
    print(f"Close gate report: {outputs['paper_backtest_evidence_analysis_close_gate_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
