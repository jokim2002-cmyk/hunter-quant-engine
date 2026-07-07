"""
Paper backtest evidence analysis sprint close pack.

Module OOOO closes the post-v1.0 paper backtest evidence analysis sprint.

This module reads the paper backtest evidence analysis close gate pack and
creates a paper-only sprint close report.

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


REQUIRED_CLOSE_GATE_ITEMS = {
    "paper_only_scope_gate",
    "dataset_context_gate",
    "descriptive_metrics_gate",
    "direction_mapping_gate",
    "neutral_filter_gate",
    "cost_assumption_gate",
    "risk_language_gate",
    "limitation_language_gate",
    "no_winner_gate",
    "git_generated_output_gate",
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
class PaperBacktestEvidenceAnalysisSprintCloseChecklistItem:
    item_index: int
    item_name: str
    status: str
    evidence: str
    next_instruction: str


@dataclass(frozen=True)
class PaperBacktestEvidenceAnalysisSprintCloseIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperBacktestEvidenceAnalysisSprintCloseReport:
    generated_at_utc: str
    paper_backtest_evidence_analysis_close_gate_path: str
    output_directory: str
    status: str
    paper_backtest_evidence_analysis_sprint_closed: bool
    ready_for_next_paper_improvement_phase: bool
    selected_dataset_path: str
    safety_notice: str
    close_checklist_item_count: int
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
    recommended_next_phase: str
    issues: list[PaperBacktestEvidenceAnalysisSprintCloseIssue]
    close_checklist: list[PaperBacktestEvidenceAnalysisSprintCloseChecklistItem]
    close_gate_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation paper backtest evidence analysis sprint close pack "
        "only. This pack closes the paper backtest evidence analysis sprint "
        "from paper-only close gate evidence. It does not start a dashboard UI, "
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
) -> PaperBacktestEvidenceAnalysisSprintCloseIssue:
    return PaperBacktestEvidenceAnalysisSprintCloseIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperBacktestEvidenceAnalysisSprintCloseIssue]) -> str:
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


def _load_close_gate(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[PaperBacktestEvidenceAnalysisSprintCloseIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_close_gate_pack_missing",
                1,
                f"Paper backtest evidence analysis close gate pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_close_gate_pack_invalid_json",
                1,
                f"Paper backtest evidence analysis close gate pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_close_gate_pack_invalid_shape",
                1,
                "Paper backtest evidence analysis close gate pack must be a JSON object.",
            )
        ]

    return payload, []


def _close_gate_issues(
    close_gate: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperBacktestEvidenceAnalysisSprintCloseIssue]:
    if close_gate is None:
        return []

    issues: list[PaperBacktestEvidenceAnalysisSprintCloseIssue] = []

    status = str(close_gate.get("status") or "unknown").lower()
    ready = bool(close_gate.get("ready_for_phase_4_close"))
    missing_required = int(close_gate.get("missing_required_file_count") or 0)

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "paper_backtest_evidence_analysis_close_gate_pack_warn",
                1,
                "Paper backtest evidence analysis close gate pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_close_gate_pack_not_pass",
                1,
                f"Paper backtest evidence analysis close gate pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_close_gate_pack_not_ready",
                1,
                "Paper backtest evidence analysis close gate pack is not ready for Phase 4 close.",
            )
        )

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_sprint_close_missing_required_files",
                missing_required,
                "Required paper backtest files are still missing.",
            )
        )

    forbidden = _forbidden(close_gate)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_backtest_evidence_analysis_close_gate_forbidden_fields",
                len(forbidden),
                "Paper backtest evidence analysis close gate pack contains forbidden broker/order fields.",
            )
        )

    close_gate_issues = close_gate.get("issues")
    if isinstance(close_gate_issues, list):
        fail_count = sum(
            1
            for item in close_gate_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "paper_backtest_evidence_analysis_close_gate_contains_fail_issues",
                    fail_count,
                    "Paper backtest evidence analysis close gate pack contains fail issues.",
                )
            )

    return issues


def _close_gate_names(close_gate: Mapping[str, Any] | None) -> list[str]:
    if close_gate is None:
        return []

    raw_items = close_gate.get("close_gate_items")
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
    close_gate_names: Sequence[str],
) -> list[PaperBacktestEvidenceAnalysisSprintCloseIssue]:
    missing_gates = REQUIRED_CLOSE_GATE_ITEMS - set(close_gate_names)

    if missing_gates:
        return [
            _issue(
                "fail",
                "required_paper_backtest_evidence_analysis_close_gates_missing",
                len(missing_gates),
                "Required paper backtest evidence analysis close gates are missing.",
            )
        ]

    return []


def _close_checklist(status: str) -> list[PaperBacktestEvidenceAnalysisSprintCloseChecklistItem]:
    checklist_status = "closed" if status in {"pass", "warn"} else "blocked"

    raw_items = [
        (
            "paper_only_scope_closed",
            checklist_status,
            "Paper-only scope gate is present.",
            "Keep next phase paper-only unless a separate live-readiness path is created.",
        ),
        (
            "dataset_context_closed",
            checklist_status,
            "Dataset context gate is present.",
            "Carry dataset scope forward into any next evidence or improvement plan.",
        ),
        (
            "descriptive_metrics_closed",
            checklist_status,
            "Descriptive metrics gate is present.",
            "Use metrics as descriptive evidence only.",
        ),
        (
            "direction_mapping_closed",
            checklist_status,
            "Direction mapping gate is present.",
            "Preserve LONG = CE BUY paper plan, SHORT = PE BUY paper plan, NEUTRAL = no trade.",
        ),
        (
            "neutral_filter_closed",
            checklist_status,
            "Neutral filter gate is present.",
            "Treat neutral/no-trade as filter behavior, not missed profit.",
        ),
        (
            "cost_assumption_closed",
            checklist_status,
            "Cost assumption gate is present.",
            "Keep costs/slippage labeled as assumptions or paper evidence.",
        ),
        (
            "risk_language_closed",
            checklist_status,
            "Risk language gate is present.",
            "Do not imply real-money risk reduction or safety.",
        ),
        (
            "limitation_language_closed",
            checklist_status,
            "Limitation language gate is present.",
            "Carry missing-data and limitation notes forward.",
        ),
        (
            "no_winner_closed",
            checklist_status,
            "No-winner gate is present.",
            "Do not select a winning strategy from this sprint.",
        ),
        (
            "git_generated_output_closed",
            checklist_status,
            "Generated output Git gate is present.",
            "Keep generated reports/data ignored and uncommitted.",
        ),
        (
            "phase_4_closed",
            checklist_status,
            "All Phase 4 evidence analysis gates are present.",
            "Next module can start a new paper-only improvement/readiness phase.",
        ),
    ]

    return [
        PaperBacktestEvidenceAnalysisSprintCloseChecklistItem(
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


def build_paper_backtest_evidence_analysis_sprint_close_report(
    *,
    paper_backtest_evidence_analysis_close_gate_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> PaperBacktestEvidenceAnalysisSprintCloseReport:
    close_gate, load_issues = _load_close_gate(
        paper_backtest_evidence_analysis_close_gate_path
    )

    issues: list[PaperBacktestEvidenceAnalysisSprintCloseIssue] = []
    issues.extend(load_issues)
    issues.extend(_close_gate_issues(close_gate, allow_warnings=allow_warnings))

    gate_names = _close_gate_names(close_gate)
    issues.extend(_readiness_issues(close_gate_names=gate_names))

    status = _status(issues)
    checklist = _close_checklist(status)

    return PaperBacktestEvidenceAnalysisSprintCloseReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        paper_backtest_evidence_analysis_close_gate_path=str(
            paper_backtest_evidence_analysis_close_gate_path
        ),
        output_directory=str(output_dir),
        status=status,
        paper_backtest_evidence_analysis_sprint_closed=status in {"pass", "warn"},
        ready_for_next_paper_improvement_phase=status in {"pass", "warn"},
        selected_dataset_path=str((close_gate or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        close_checklist_item_count=len(checklist),
        close_gate_item_count=len(gate_names),
        report_safety_language_item_count=int(
            (close_gate or {}).get("report_safety_language_item_count") or 0
        ),
        metrics_context_item_count=int((close_gate or {}).get("metrics_context_item_count") or 0),
        ledger_snapshot_item_count=int((close_gate or {}).get("ledger_snapshot_item_count") or 0),
        analysis_item_count=int((close_gate or {}).get("analysis_item_count") or 0),
        review_summary_item_count=int((close_gate or {}).get("review_summary_item_count") or 0),
        presence_check_count=int((close_gate or {}).get("presence_check_count") or 0),
        expected_output_count=int((close_gate or {}).get("expected_output_count") or 0),
        present_required_file_count=int((close_gate or {}).get("present_required_file_count") or 0),
        missing_required_file_count=int((close_gate or {}).get("missing_required_file_count") or 0),
        completed_total_before_module=92,
        completed_total_after_module=93,
        phase_4_pending_before_module=1,
        phase_4_pending_after_module=0,
        full_hqe_product_estimate_after_module="85-90%",
        recommended_next_phase=(
            "Begin the next paper-only improvement/readiness phase from descriptive evidence. "
            "Do not introduce broker execution, live market data, real money, profitability claims, "
            "or winning-strategy selection without a separate tested safety path."
        ),
        issues=issues,
        close_checklist=checklist,
        close_gate_names=gate_names,
    )


def write_paper_backtest_evidence_analysis_sprint_close_report(
    report: PaperBacktestEvidenceAnalysisSprintCloseReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    close_json = output_dir / "paper_backtest_evidence_analysis_sprint_close_pack.json"
    close_txt = output_dir / "paper_backtest_evidence_analysis_sprint_close_pack.txt"
    checklist_csv = output_dir / "paper_backtest_evidence_analysis_sprint_close_checklist.csv"
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
        "HQE Paper Backtest Evidence Analysis Sprint Close Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Paper backtest evidence analysis sprint closed: {report.paper_backtest_evidence_analysis_sprint_closed}",
        f"Ready for next paper improvement phase: {report.ready_for_next_paper_improvement_phase}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Close checklist items: {report.close_checklist_item_count}",
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
        f"- Completed total before Module OOOO: {report.completed_total_before_module} modules.",
        f"- Completed total after Module OOOO: {report.completed_total_after_module} modules.",
        f"- Phase 4 pending before Module OOOO: {report.phase_4_pending_before_module} module.",
        f"- Phase 4 pending after Module OOOO: {report.phase_4_pending_after_module} modules.",
        f"- Full HQE product estimate after Module OOOO: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next phase:",
        report.recommended_next_phase,
        "",
        "Sprint close checklist:",
    ]

    for item in report.close_checklist:
        lines.append(
            (
                f"{item.item_index}. {item.item_name} [{item.status}] - "
                f"{item.evidence} Next={item.next_instruction}"
            )
        )

    lines.extend(["", "Close gate names:"])
    for gate_name in report.close_gate_names:
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
        lines.append("- PASS: Paper backtest evidence analysis sprint is closed.")
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
        "report_type": "paper_backtest_evidence_analysis_sprint_close_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "paper_backtest_evidence_analysis_sprint_closed": report.paper_backtest_evidence_analysis_sprint_closed,
        "ready_for_next_paper_improvement_phase": report.ready_for_next_paper_improvement_phase,
        "selected_dataset_path": report.selected_dataset_path,
        "close_checklist_item_count": report.close_checklist_item_count,
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
        "recommended_next_phase": report.recommended_next_phase,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_backtest_evidence_analysis_sprint_close_pack_json": str(close_json),
            "paper_backtest_evidence_analysis_sprint_close_pack_txt": str(close_txt),
            "paper_backtest_evidence_analysis_sprint_close_checklist_csv": str(checklist_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_backtest_evidence_analysis_sprint_close_pack_json": close_json,
        "paper_backtest_evidence_analysis_sprint_close_pack_txt": close_txt,
        "paper_backtest_evidence_analysis_sprint_close_checklist_csv": checklist_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_backtest_evidence_analysis_sprint_close_report(
    *,
    paper_backtest_evidence_analysis_close_gate_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[PaperBacktestEvidenceAnalysisSprintCloseReport, dict[str, Path]]:
    report = build_paper_backtest_evidence_analysis_sprint_close_report(
        paper_backtest_evidence_analysis_close_gate_path=paper_backtest_evidence_analysis_close_gate_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_backtest_evidence_analysis_sprint_close_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper backtest evidence analysis sprint close pack."
    )
    parser.add_argument(
        "--paper-backtest-evidence-analysis-close-gate",
        default=(
            "reports/paper_trading/"
            "paper_backtest_evidence_analysis_close_gate_pack/"
            "paper_backtest_evidence_analysis_close_gate_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/paper_backtest_evidence_analysis_sprint_close_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_paper_backtest_evidence_analysis_sprint_close_report(
        paper_backtest_evidence_analysis_close_gate_path=Path(
            args.paper_backtest_evidence_analysis_close_gate
        ),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE paper backtest evidence analysis sprint close pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Paper backtest evidence analysis sprint closed: {report.paper_backtest_evidence_analysis_sprint_closed}")
    print(f"Sprint close report: {outputs['paper_backtest_evidence_analysis_sprint_close_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
