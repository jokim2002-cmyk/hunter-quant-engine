"""
Recorded backtest command plan pack.

Module EEEE in the post-dashboard recorded-data paper backtest review phase.

This module reads the recorded backtest launch gate pack and creates a paper-only
manual command plan for the recorded-data paper backtest workflow.

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


REQUIRED_LAUNCH_STEPS = {
    "confirm_recorded_dataset",
    "confirm_paper_only_mode",
    "review_dashboard_close",
    "prepare_existing_backtest_runner",
    "run_recorded_backtest_manually",
    "verify_outputs_after_run",
    "preserve_generated_reports_ignored",
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
class RecordedBacktestCommandStep:
    command_index: int
    command_name: str
    command_text: str
    stage: str
    expected_output: str
    safety_boundary: str


@dataclass(frozen=True)
class RecordedBacktestCommandPlanIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class RecordedBacktestCommandPlanReport:
    generated_at_utc: str
    recorded_backtest_launch_gate_path: str
    output_directory: str
    status: str
    ready_for_manual_operator_run: bool
    selected_dataset_path: str
    safety_notice: str
    command_step_count: int
    launch_step_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_3_pending_before_module: int
    phase_3_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_action: str
    issues: list[RecordedBacktestCommandPlanIssue]
    command_steps: list[RecordedBacktestCommandStep]
    launch_step_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation recorded backtest command plan pack only. This pack "
        "creates manual command steps for a recorded-data paper backtest review "
        "workflow. It does not start a dashboard UI, does not import or require "
        "Streamlit at runtime, does not run backtests, does not calculate "
        "profitability, does not select a winning strategy, does not modify "
        "strategy logic, does not connect to brokers, does not request live "
        "market data, does not place real orders, does not use real money, or "
        "prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> RecordedBacktestCommandPlanIssue:
    return RecordedBacktestCommandPlanIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[RecordedBacktestCommandPlanIssue]) -> str:
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


def _load_launch_gate(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[RecordedBacktestCommandPlanIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "recorded_backtest_launch_gate_pack_missing",
                1,
                f"Recorded backtest launch gate pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "recorded_backtest_launch_gate_pack_invalid_json",
                1,
                f"Recorded backtest launch gate pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "recorded_backtest_launch_gate_pack_invalid_shape",
                1,
                "Recorded backtest launch gate pack must be a JSON object.",
            )
        ]

    return payload, []


def _launch_gate_issues(
    launch_gate: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[RecordedBacktestCommandPlanIssue]:
    if launch_gate is None:
        return []

    issues: list[RecordedBacktestCommandPlanIssue] = []

    status = str(launch_gate.get("status") or "unknown").lower()
    ready = bool(launch_gate.get("ready_for_manual_recorded_backtest_run"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "recorded_backtest_launch_gate_pack_warn",
                1,
                "Recorded backtest launch gate pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_launch_gate_pack_not_pass",
                1,
                f"Recorded backtest launch gate pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_launch_gate_pack_not_ready",
                1,
                "Recorded backtest launch gate pack is not ready for manual recorded-data paper backtest run.",
            )
        )

    forbidden = _forbidden(launch_gate)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_launch_gate_forbidden_fields",
                len(forbidden),
                "Recorded backtest launch gate pack contains forbidden broker/order/real-money fields.",
            )
        )

    launch_issues = launch_gate.get("issues")
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
                    "recorded_backtest_launch_gate_contains_fail_issues",
                    fail_count,
                    "Recorded backtest launch gate pack contains fail issues.",
                )
            )

    return issues


def _launch_step_names(launch_gate: Mapping[str, Any] | None) -> list[str]:
    if launch_gate is None:
        return []

    raw_steps = launch_gate.get("launch_steps")
    if not isinstance(raw_steps, list):
        return []

    return sorted(
        {
            str(step.get("step_name") or "").strip().lower()
            for step in raw_steps
            if isinstance(step, Mapping) and str(step.get("step_name") or "").strip()
        }
    )


def _readiness_issues(
    *,
    launch_step_names: Sequence[str],
) -> list[RecordedBacktestCommandPlanIssue]:
    missing_steps = REQUIRED_LAUNCH_STEPS - set(launch_step_names)

    if missing_steps:
        return [
            _issue(
                "fail",
                "required_recorded_backtest_launch_steps_missing",
                len(missing_steps),
                "Required recorded backtest launch steps are missing.",
            )
        ]

    return []


def _safe_dataset_path(path: str) -> str:
    cleaned = str(path or "").strip()
    return cleaned or "data/recorded/REPLACE_WITH_RECORDED_DATASET.csv"


def _command_steps(selected_dataset_path: str) -> list[RecordedBacktestCommandStep]:
    dataset = _safe_dataset_path(selected_dataset_path)

    raw_commands = [
        (
            "confirm_git_clean",
            'git status --short',
            "preflight",
            "Working tree should be clean before manual recorded-data paper run.",
            "Generated reports/data must remain ignored and uncommitted.",
        ),
        (
            "build_real_dataset_input_pack",
            f'.\\hqe_real_dataset_backtest_input_pack.bat --dataset "{dataset}"',
            "input_pack",
            "Real dataset backtest input pack is generated for the selected recorded dataset.",
            "No live market data request.",
        ),
        (
            "build_first_real_dataset_run_pack",
            ".\\hqe_first_real_dataset_backtest_run_pack.bat",
            "run_pack",
            "First real dataset backtest run pack prepares operator-safe run order.",
            "This command plan does not execute broker/live orders.",
        ),
        (
            "run_existing_one_command_backtest",
            ".\\hqe_one_command_backtest_runner.bat",
            "manual_backtest_run",
            "Existing paper-only runner generates ledger, metrics, report, and readiness outputs.",
            "Paper/simulation only; no real money and no option selling.",
        ),
        (
            "verify_first_real_backtest_outputs",
            ".\\hqe_first_real_backtest_output_verification_pack.bat",
            "verification",
            "Expected recorded-data paper backtest outputs are verified.",
            "No profitability claim.",
        ),
        (
            "review_first_real_backtest_report",
            ".\\hqe_first_real_backtest_report_review_pack.bat",
            "review",
            "Backtest report review checklist is generated.",
            "No strategy winner is selected.",
        ),
        (
            "preserve_generated_outputs_ignored",
            "git status --short",
            "git_safety",
            "Generated reports/data should remain ignored; source/docs/tests only are committed.",
            "No secrets, no generated report data, and no broker data in Git.",
        ),
    ]

    return [
        RecordedBacktestCommandStep(
            command_index=index,
            command_name=command_name,
            command_text=command_text,
            stage=stage,
            expected_output=expected_output,
            safety_boundary=safety_boundary,
        )
        for index, (
            command_name,
            command_text,
            stage,
            expected_output,
            safety_boundary,
        ) in enumerate(raw_commands, start=1)
    ]


def build_recorded_backtest_command_plan_report(
    *,
    recorded_backtest_launch_gate_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> RecordedBacktestCommandPlanReport:
    launch_gate, load_issues = _load_launch_gate(recorded_backtest_launch_gate_path)

    issues: list[RecordedBacktestCommandPlanIssue] = []
    issues.extend(load_issues)
    issues.extend(_launch_gate_issues(launch_gate, allow_warnings=allow_warnings))

    launch_step_names = _launch_step_names(launch_gate)
    issues.extend(_readiness_issues(launch_step_names=launch_step_names))

    selected_dataset_path = str((launch_gate or {}).get("selected_dataset_path") or "")
    command_steps = _command_steps(selected_dataset_path)
    status = _status(issues)

    return RecordedBacktestCommandPlanReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        recorded_backtest_launch_gate_path=str(recorded_backtest_launch_gate_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_manual_operator_run=status in {"pass", "warn"},
        selected_dataset_path=_safe_dataset_path(selected_dataset_path),
        safety_notice=safety_notice(),
        command_step_count=len(command_steps),
        launch_step_count=len(launch_step_names),
        completed_total_before_module=82,
        completed_total_after_module=83,
        phase_3_pending_before_module=5,
        phase_3_pending_after_module=4,
        full_hqe_product_estimate_after_module="75-80%",
        recommended_next_action=(
            "Operator may run the generated command plan manually only with recorded data. "
            "Keep it paper-only and review outputs without profitability claims."
        ),
        issues=issues,
        command_steps=command_steps,
        launch_step_names=launch_step_names,
    )


def write_recorded_backtest_command_plan_report(
    report: RecordedBacktestCommandPlanReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_json = output_dir / "recorded_backtest_command_plan_pack.json"
    plan_txt = output_dir / "recorded_backtest_command_plan_pack.txt"
    commands_csv = output_dir / "recorded_backtest_commands.csv"
    commands_ps1 = output_dir / "recorded_backtest_manual_commands.ps1"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["command_steps"] = [asdict(step) for step in report.command_steps]
    plan_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with commands_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "command_index",
                "command_name",
                "command_text",
                "stage",
                "expected_output",
                "safety_boundary",
            ]
        )
        for step in report.command_steps:
            writer.writerow(
                [
                    step.command_index,
                    step.command_name,
                    step.command_text,
                    step.stage,
                    step.expected_output,
                    step.safety_boundary,
                ]
            )

    ps_lines = [
        "# HQE recorded-data paper backtest manual command plan",
        "# Generated by Module EEEE.",
        "# Paper/simulation only. This script is a plan; review before running.",
        "# No broker orders. No live market data. No real money. Not a profitability claim.",
        "",
        'Set-StrictMode -Version Latest',
        '$ErrorActionPreference = "Stop"',
        'Set-Location -LiteralPath "D:\\Hunter_Quant_Engine_PC_TRANSFER"',
        "",
    ]
    for step in report.command_steps:
        ps_lines.append(f'Write-Host "=== {step.command_index}. {step.command_name} ==="')
        ps_lines.append(step.command_text)
        ps_lines.append("")

    commands_ps1.write_text("\n".join(ps_lines), encoding="utf-8")

    lines = [
        "HQE Recorded Backtest Command Plan Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for manual operator run: {report.ready_for_manual_operator_run}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Command steps: {report.command_step_count}",
        f"Launch steps carried forward: {report.launch_step_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Post-v1.0 Phase 1: Real Backtest Usage Sprint complete.",
        "- Post-v1.0 Phase 2: Dashboard Sprint complete.",
        f"- Completed total before Module EEEE: {report.completed_total_before_module} modules.",
        f"- Completed total after Module EEEE: {report.completed_total_after_module} modules.",
        f"- Phase 3 pending before Module EEEE: {report.phase_3_pending_before_module} modules.",
        f"- Phase 3 pending after Module EEEE: {report.phase_3_pending_after_module} modules.",
        f"- Full HQE product estimate after Module EEEE: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Manual command plan:",
    ]

    for step in report.command_steps:
        lines.append(f"{step.command_index}. {step.command_name} [{step.stage}]")
        lines.append(f"   Command: {step.command_text}")
        lines.append(f"   Expected: {step.expected_output}")
        lines.append(f"   Safety: {step.safety_boundary}")

    lines.extend(["", "Launch steps carried forward:"])
    for step_name in report.launch_step_names:
        lines.append(f"- {step_name}")

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
        lines.append("- PASS: Recorded-data paper backtest command plan is ready.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {plan_json}",
            f"- {plan_txt}",
            f"- {commands_csv}",
            f"- {commands_ps1}",
            f"- {manifest_json}",
        ]
    )
    plan_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_backtest_command_plan_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_manual_operator_run": report.ready_for_manual_operator_run,
        "selected_dataset_path": report.selected_dataset_path,
        "command_step_count": report.command_step_count,
        "launch_step_count": report.launch_step_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_3_pending_after_module": report.phase_3_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "recorded_backtest_command_plan_pack_json": str(plan_json),
            "recorded_backtest_command_plan_pack_txt": str(plan_txt),
            "recorded_backtest_commands_csv": str(commands_csv),
            "recorded_backtest_manual_commands_ps1": str(commands_ps1),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "recorded_backtest_command_plan_pack_json": plan_json,
        "recorded_backtest_command_plan_pack_txt": plan_txt,
        "recorded_backtest_commands_csv": commands_csv,
        "recorded_backtest_manual_commands_ps1": commands_ps1,
        "manifest_json": manifest_json,
    }


def build_and_write_recorded_backtest_command_plan_report(
    *,
    recorded_backtest_launch_gate_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[RecordedBacktestCommandPlanReport, dict[str, Path]]:
    report = build_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=recorded_backtest_launch_gate_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_recorded_backtest_command_plan_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build recorded-data paper backtest command plan pack."
    )
    parser.add_argument(
        "--recorded-backtest-launch-gate",
        default=(
            "reports/paper_trading/"
            "recorded_backtest_launch_gate_pack/"
            "recorded_backtest_launch_gate_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_backtest_command_plan_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=Path(args.recorded_backtest_launch_gate),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded backtest command plan pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for manual operator run: {report.ready_for_manual_operator_run}")
    print(f"Recorded backtest command plan: {outputs['recorded_backtest_command_plan_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
