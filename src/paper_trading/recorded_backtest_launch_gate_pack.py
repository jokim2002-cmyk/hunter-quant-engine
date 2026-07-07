"""
Recorded backtest launch gate pack.

Module DDDD starts the post-dashboard recorded-data paper backtest review phase.

This module reads the Dashboard Sprint readiness close pack and creates a
paper-only launch gate plus operator steps for the first recorded-data paper
backtest review workflow.

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


REQUIRED_DASHBOARD_CLOSE_CHECKLIST_ITEMS = {
    "dashboard_input_index",
    "dashboard_overview_snapshot",
    "dashboard_section_registry",
    "dashboard_component_scaffold",
    "dashboard_app_shell",
    "dashboard_smoke_test_plan",
    "dashboard_dry_run_validation",
    "safety_boundary",
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
class RecordedBacktestLaunchStep:
    step_index: int
    step_name: str
    stage: str
    operator_action: str
    expected_result: str
    safety_boundary: str


@dataclass(frozen=True)
class RecordedBacktestLaunchGateIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class RecordedBacktestLaunchGateReport:
    generated_at_utc: str
    dashboard_sprint_close_path: str
    output_directory: str
    status: str
    ready_for_manual_recorded_backtest_run: bool
    selected_dataset_path: str
    safety_notice: str
    launch_step_count: int
    dashboard_close_checklist_item_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_3_pending_before_module: int
    phase_3_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_action: str
    issues: list[RecordedBacktestLaunchGateIssue]
    launch_steps: list[RecordedBacktestLaunchStep]
    dashboard_close_checklist_item_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation recorded backtest launch gate pack only. This pack "
        "creates a launch gate and operator steps for a recorded-data paper "
        "backtest review workflow. It does not start a dashboard UI, does not "
        "import or require Streamlit at runtime, does not run backtests, does "
        "not calculate profitability, does not select a winning strategy, does "
        "not modify strategy logic, does not connect to brokers, does not "
        "request live market data, does not place real orders, does not use "
        "real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> RecordedBacktestLaunchGateIssue:
    return RecordedBacktestLaunchGateIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[RecordedBacktestLaunchGateIssue]) -> str:
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


def _load_dashboard_sprint_close(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[RecordedBacktestLaunchGateIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "dashboard_sprint_readiness_close_pack_missing",
                1,
                f"Dashboard Sprint readiness close pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "dashboard_sprint_readiness_close_pack_invalid_json",
                1,
                f"Dashboard Sprint readiness close pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "dashboard_sprint_readiness_close_pack_invalid_shape",
                1,
                "Dashboard Sprint readiness close pack must be a JSON object.",
            )
        ]

    return payload, []


def _dashboard_close_issues(
    close_pack: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[RecordedBacktestLaunchGateIssue]:
    if close_pack is None:
        return []

    issues: list[RecordedBacktestLaunchGateIssue] = []

    status = str(close_pack.get("status") or "unknown").lower()
    closed = bool(close_pack.get("dashboard_sprint_closed"))
    ready = bool(close_pack.get("ready_for_recorded_backtest_review_workflow"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "dashboard_sprint_readiness_close_pack_warn",
                1,
                "Dashboard Sprint readiness close pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "dashboard_sprint_readiness_close_pack_not_pass",
                1,
                f"Dashboard Sprint readiness close pack status is not pass: {status}.",
            )
        )

    if not closed:
        issues.append(
            _issue(
                "fail",
                "dashboard_sprint_not_closed",
                1,
                "Dashboard Sprint is not closed.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "dashboard_sprint_not_ready_for_recorded_backtest_review",
                1,
                "Dashboard Sprint close is not ready for recorded-data backtest review workflow.",
            )
        )

    forbidden = _forbidden(close_pack)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "dashboard_sprint_close_forbidden_fields",
                len(forbidden),
                "Dashboard Sprint close pack contains forbidden broker/order/real-money fields.",
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
                    "dashboard_sprint_close_contains_fail_issues",
                    fail_count,
                    "Dashboard Sprint close pack contains fail issues.",
                )
            )

    return issues


def _checklist_item_names(close_pack: Mapping[str, Any] | None) -> list[str]:
    if close_pack is None:
        return []

    raw_items = close_pack.get("checklist")
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
    checklist_item_names: Sequence[str],
) -> list[RecordedBacktestLaunchGateIssue]:
    missing_items = REQUIRED_DASHBOARD_CLOSE_CHECKLIST_ITEMS - set(checklist_item_names)

    if missing_items:
        return [
            _issue(
                "fail",
                "required_dashboard_close_checklist_items_missing",
                len(missing_items),
                "Required dashboard close checklist items are missing.",
            )
        ]

    return []


def _launch_steps() -> list[RecordedBacktestLaunchStep]:
    raw_steps = [
        (
            "confirm_recorded_dataset",
            "dataset",
            "Confirm selected recorded dataset path before running any backtest.",
            "Operator has one recorded-data file selected for paper backtest.",
            "No live market data request.",
        ),
        (
            "confirm_paper_only_mode",
            "safety",
            "Confirm LONG = CE BUY paper plan only, SHORT = PE BUY paper plan only, NEUTRAL = no trade.",
            "Paper-only strategy boundary is confirmed.",
            "No option selling, no broker order, no real money.",
        ),
        (
            "review_dashboard_close",
            "dashboard_review",
            "Review Dashboard Sprint close output and dashboard dry-run validation.",
            "Dashboard review foundation is complete before recorded-data result review.",
            "Dashboard is not started and Streamlit is not required.",
        ),
        (
            "prepare_existing_backtest_runner",
            "execution_preparation",
            "Use existing HQE paper backtest runner only after dataset path is confirmed.",
            "Recorded-data paper backtest can be launched manually by operator.",
            "No broker connection and no live data.",
        ),
        (
            "run_recorded_backtest_manually",
            "manual_run",
            "Run the existing recorded-data paper backtest command in the next workflow step.",
            "Ledger, metrics, report, and readiness outputs are generated by paper runner.",
            "This launch gate itself does not run backtests.",
        ),
        (
            "verify_outputs_after_run",
            "verification",
            "Verify ledger, metrics, report, readiness gate, and dashboard review inputs after run.",
            "Backtest outputs can be reviewed without profitability claims.",
            "No strategy winner is selected.",
        ),
        (
            "preserve_generated_reports_ignored",
            "git_safety",
            "Keep generated reports/data ignored and do not commit run outputs.",
            "Only source, tests, docs, and shortcuts remain commit candidates.",
            "Secrets and generated report data stay out of Git.",
        ),
    ]

    return [
        RecordedBacktestLaunchStep(
            step_index=index,
            step_name=step_name,
            stage=stage,
            operator_action=operator_action,
            expected_result=expected_result,
            safety_boundary=safety_boundary,
        )
        for index, (
            step_name,
            stage,
            operator_action,
            expected_result,
            safety_boundary,
        ) in enumerate(raw_steps, start=1)
    ]


def build_recorded_backtest_launch_gate_report(
    *,
    dashboard_sprint_close_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> RecordedBacktestLaunchGateReport:
    close_pack, load_issues = _load_dashboard_sprint_close(dashboard_sprint_close_path)

    issues: list[RecordedBacktestLaunchGateIssue] = []
    issues.extend(load_issues)
    issues.extend(_dashboard_close_issues(close_pack, allow_warnings=allow_warnings))

    checklist_item_names = _checklist_item_names(close_pack)
    issues.extend(_readiness_issues(checklist_item_names=checklist_item_names))

    launch_steps = _launch_steps()
    status = _status(issues)

    return RecordedBacktestLaunchGateReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dashboard_sprint_close_path=str(dashboard_sprint_close_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_manual_recorded_backtest_run=status in {"pass", "warn"},
        selected_dataset_path=str((close_pack or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        launch_step_count=len(launch_steps),
        dashboard_close_checklist_item_count=len(checklist_item_names),
        completed_total_before_module=81,
        completed_total_after_module=82,
        phase_3_pending_before_module=6,
        phase_3_pending_after_module=5,
        full_hqe_product_estimate_after_module="74-79%",
        recommended_next_action=(
            "Run the existing HQE recorded-data paper backtest command manually in the next step, "
            "then verify ledger, metrics, report, and readiness outputs. This is not a profitability claim."
        ),
        issues=issues,
        launch_steps=launch_steps,
        dashboard_close_checklist_item_names=checklist_item_names,
    )


def write_recorded_backtest_launch_gate_report(
    report: RecordedBacktestLaunchGateReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    gate_json = output_dir / "recorded_backtest_launch_gate_pack.json"
    gate_txt = output_dir / "recorded_backtest_launch_gate_pack.txt"
    steps_csv = output_dir / "recorded_backtest_launch_steps.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["launch_steps"] = [asdict(step) for step in report.launch_steps]
    gate_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with steps_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "step_index",
                "step_name",
                "stage",
                "operator_action",
                "expected_result",
                "safety_boundary",
            ]
        )
        for step in report.launch_steps:
            writer.writerow(
                [
                    step.step_index,
                    step.step_name,
                    step.stage,
                    step.operator_action,
                    step.expected_result,
                    step.safety_boundary,
                ]
            )

    lines = [
        "HQE Recorded Backtest Launch Gate Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for manual recorded-data paper backtest run: {report.ready_for_manual_recorded_backtest_run}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Launch steps: {report.launch_step_count}",
        f"Dashboard close checklist items: {report.dashboard_close_checklist_item_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Post-v1.0 Phase 1: Real Backtest Usage Sprint complete.",
        "- Post-v1.0 Phase 2: Dashboard Sprint complete.",
        f"- Completed total before Module DDDD: {report.completed_total_before_module} modules.",
        f"- Completed total after Module DDDD: {report.completed_total_after_module} modules.",
        f"- Phase 3 pending before Module DDDD: {report.phase_3_pending_before_module} modules.",
        f"- Phase 3 pending after Module DDDD: {report.phase_3_pending_after_module} modules.",
        f"- Full HQE product estimate after Module DDDD: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Launch steps:",
    ]

    for step in report.launch_steps:
        lines.append(
            (
                f"{step.step_index}. {step.step_name} [{step.stage}] - "
                f"{step.operator_action} Expected={step.expected_result}"
            )
        )

    lines.extend(["", "Dashboard close checklist items:"])
    for item_name in report.dashboard_close_checklist_item_names:
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
        lines.append("- PASS: Recorded-data paper backtest launch gate is ready.")
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
            f"- {steps_csv}",
            f"- {manifest_json}",
        ]
    )
    gate_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_backtest_launch_gate_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_manual_recorded_backtest_run": report.ready_for_manual_recorded_backtest_run,
        "selected_dataset_path": report.selected_dataset_path,
        "launch_step_count": report.launch_step_count,
        "dashboard_close_checklist_item_count": report.dashboard_close_checklist_item_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_3_pending_after_module": report.phase_3_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "recorded_backtest_launch_gate_pack_json": str(gate_json),
            "recorded_backtest_launch_gate_pack_txt": str(gate_txt),
            "recorded_backtest_launch_steps_csv": str(steps_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "recorded_backtest_launch_gate_pack_json": gate_json,
        "recorded_backtest_launch_gate_pack_txt": gate_txt,
        "recorded_backtest_launch_steps_csv": steps_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_recorded_backtest_launch_gate_report(
    *,
    dashboard_sprint_close_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[RecordedBacktestLaunchGateReport, dict[str, Path]]:
    report = build_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=dashboard_sprint_close_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_recorded_backtest_launch_gate_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build recorded-data paper backtest launch gate pack."
    )
    parser.add_argument(
        "--dashboard-sprint-close",
        default=(
            "reports/paper_trading/"
            "dashboard_sprint_readiness_close_pack/"
            "dashboard_sprint_readiness_close_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_backtest_launch_gate_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=Path(args.dashboard_sprint_close),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded backtest launch gate pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for manual recorded-data paper backtest run: {report.ready_for_manual_recorded_backtest_run}")
    print(f"Recorded backtest launch gate: {outputs['recorded_backtest_launch_gate_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
