"""
Recorded backtest run output intake pack.

Module FFFF in the post-dashboard recorded-data paper backtest review phase.

This module reads the recorded backtest command plan pack and creates paper-only
post-run output intake expectations for the recorded-data paper backtest workflow.

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


REQUIRED_COMMAND_STEPS = {
    "confirm_git_clean",
    "build_real_dataset_input_pack",
    "build_first_real_dataset_run_pack",
    "run_existing_one_command_backtest",
    "verify_first_real_backtest_outputs",
    "review_first_real_backtest_report",
    "preserve_generated_outputs_ignored",
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
class RecordedBacktestOutputExpectation:
    expectation_index: int
    output_name: str
    expected_path_hint: str
    required_after_manual_run: bool
    producer_stage: str
    intake_check: str
    safety_boundary: str


@dataclass(frozen=True)
class RecordedBacktestRunOutputIntakeIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class RecordedBacktestRunOutputIntakeReport:
    generated_at_utc: str
    recorded_backtest_command_plan_path: str
    output_directory: str
    status: str
    ready_for_post_run_output_verification: bool
    selected_dataset_path: str
    safety_notice: str
    expected_output_count: int
    command_step_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_3_pending_before_module: int
    phase_3_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_action: str
    issues: list[RecordedBacktestRunOutputIntakeIssue]
    expected_outputs: list[RecordedBacktestOutputExpectation]
    command_step_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation recorded backtest run output intake pack only. This "
        "pack creates post-run output intake expectations for a recorded-data "
        "paper backtest review workflow. It does not start a dashboard UI, "
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
) -> RecordedBacktestRunOutputIntakeIssue:
    return RecordedBacktestRunOutputIntakeIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[RecordedBacktestRunOutputIntakeIssue]) -> str:
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


def _load_command_plan(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[RecordedBacktestRunOutputIntakeIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "recorded_backtest_command_plan_pack_missing",
                1,
                f"Recorded backtest command plan pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "recorded_backtest_command_plan_pack_invalid_json",
                1,
                f"Recorded backtest command plan pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "recorded_backtest_command_plan_pack_invalid_shape",
                1,
                "Recorded backtest command plan pack must be a JSON object.",
            )
        ]

    return payload, []


def _command_plan_issues(
    plan: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[RecordedBacktestRunOutputIntakeIssue]:
    if plan is None:
        return []

    issues: list[RecordedBacktestRunOutputIntakeIssue] = []

    status = str(plan.get("status") or "unknown").lower()
    ready = bool(plan.get("ready_for_manual_operator_run"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "recorded_backtest_command_plan_pack_warn",
                1,
                "Recorded backtest command plan pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_command_plan_pack_not_pass",
                1,
                f"Recorded backtest command plan pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_command_plan_pack_not_ready",
                1,
                "Recorded backtest command plan pack is not ready for manual operator run.",
            )
        )

    forbidden = _forbidden(plan)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_command_plan_forbidden_fields",
                len(forbidden),
                "Recorded backtest command plan contains forbidden broker/order/real-money fields.",
            )
        )

    plan_issues = plan.get("issues")
    if isinstance(plan_issues, list):
        fail_count = sum(
            1
            for item in plan_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "recorded_backtest_command_plan_contains_fail_issues",
                    fail_count,
                    "Recorded backtest command plan contains fail issues.",
                )
            )

    return issues


def _command_step_names(plan: Mapping[str, Any] | None) -> list[str]:
    if plan is None:
        return []

    raw_steps = plan.get("command_steps")
    if not isinstance(raw_steps, list):
        return []

    return sorted(
        {
            str(step.get("command_name") or "").strip().lower()
            for step in raw_steps
            if isinstance(step, Mapping) and str(step.get("command_name") or "").strip()
        }
    )


def _readiness_issues(
    *,
    command_step_names: Sequence[str],
) -> list[RecordedBacktestRunOutputIntakeIssue]:
    missing_steps = REQUIRED_COMMAND_STEPS - set(command_step_names)

    if missing_steps:
        return [
            _issue(
                "fail",
                "required_recorded_backtest_command_steps_missing",
                len(missing_steps),
                "Required recorded backtest command steps are missing.",
            )
        ]

    return []


def _safe_dataset_path(path: str) -> str:
    cleaned = str(path or "").strip()
    return cleaned or "data/recorded/REPLACE_WITH_RECORDED_DATASET.csv"


def _expected_outputs() -> list[RecordedBacktestOutputExpectation]:
    raw_outputs = [
        (
            "real_dataset_backtest_input_pack",
            "reports/paper_trading/real_dataset_backtest_input_pack/real_dataset_backtest_input_pack.json",
            True,
            "input_pack",
            "Confirm dataset path and paper-only input metadata are present.",
            "No live market data request.",
        ),
        (
            "first_real_dataset_backtest_run_pack",
            "reports/paper_trading/first_real_dataset_backtest_run_pack/first_real_dataset_backtest_run_pack.json",
            True,
            "run_pack",
            "Confirm manual run order and expected outputs were prepared.",
            "No broker order path.",
        ),
        (
            "backtest_trade_ledger",
            "reports/paper_trading/backtest_trade_ledger/backtest_trade_ledger.csv",
            True,
            "manual_backtest_run",
            "Confirm paper trade ledger exists after manual run.",
            "Paper-only CE/PE buy plans; no option selling.",
        ),
        (
            "backtest_metrics",
            "reports/paper_trading/backtest_metrics/backtest_metrics.json",
            True,
            "manual_backtest_run",
            "Confirm metrics artifact exists without profitability claim wording.",
            "Metrics are evidence only, not profit guarantee.",
        ),
        (
            "backtest_report",
            "reports/paper_trading/backtest_report/backtest_report.txt",
            True,
            "manual_backtest_run",
            "Confirm backtest report exists for operator review.",
            "No strategy winner is selected.",
        ),
        (
            "first_real_backtest_output_verification",
            "reports/paper_trading/first_real_backtest_output_verification_pack/first_real_backtest_output_verification_pack.json",
            True,
            "verification",
            "Confirm output verification pack can inspect expected files.",
            "No real money and no live execution.",
        ),
        (
            "first_real_backtest_report_review",
            "reports/paper_trading/first_real_backtest_report_review_pack/first_real_backtest_report_review_pack.json",
            True,
            "review",
            "Confirm report review checklist can be generated after manual run.",
            "This review is not a profitability claim.",
        ),
        (
            "git_generated_outputs_guard",
            "git status --short",
            True,
            "git_safety",
            "Confirm generated reports/data remain ignored and uncommitted.",
            "No secrets or generated report data in Git.",
        ),
    ]

    return [
        RecordedBacktestOutputExpectation(
            expectation_index=index,
            output_name=output_name,
            expected_path_hint=expected_path_hint,
            required_after_manual_run=required_after_manual_run,
            producer_stage=producer_stage,
            intake_check=intake_check,
            safety_boundary=safety_boundary,
        )
        for index, (
            output_name,
            expected_path_hint,
            required_after_manual_run,
            producer_stage,
            intake_check,
            safety_boundary,
        ) in enumerate(raw_outputs, start=1)
    ]


def build_recorded_backtest_run_output_intake_report(
    *,
    recorded_backtest_command_plan_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> RecordedBacktestRunOutputIntakeReport:
    plan, load_issues = _load_command_plan(recorded_backtest_command_plan_path)

    issues: list[RecordedBacktestRunOutputIntakeIssue] = []
    issues.extend(load_issues)
    issues.extend(_command_plan_issues(plan, allow_warnings=allow_warnings))

    command_step_names = _command_step_names(plan)
    issues.extend(_readiness_issues(command_step_names=command_step_names))

    selected_dataset_path = _safe_dataset_path(str((plan or {}).get("selected_dataset_path") or ""))
    expected_outputs = _expected_outputs()
    status = _status(issues)

    return RecordedBacktestRunOutputIntakeReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        recorded_backtest_command_plan_path=str(recorded_backtest_command_plan_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_post_run_output_verification=status in {"pass", "warn"},
        selected_dataset_path=selected_dataset_path,
        safety_notice=safety_notice(),
        expected_output_count=len(expected_outputs),
        command_step_count=len(command_step_names),
        completed_total_before_module=83,
        completed_total_after_module=84,
        phase_3_pending_before_module=4,
        phase_3_pending_after_module=3,
        full_hqe_product_estimate_after_module="76-81%",
        recommended_next_action=(
            "After the operator manually runs the recorded-data paper backtest command plan, "
            "use this intake pack to verify the ledger, metrics, report, verification, and review outputs."
        ),
        issues=issues,
        expected_outputs=expected_outputs,
        command_step_names=command_step_names,
    )


def write_recorded_backtest_run_output_intake_report(
    report: RecordedBacktestRunOutputIntakeReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    intake_json = output_dir / "recorded_backtest_run_output_intake_pack.json"
    intake_txt = output_dir / "recorded_backtest_run_output_intake_pack.txt"
    expectations_csv = output_dir / "recorded_backtest_expected_outputs.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["expected_outputs"] = [asdict(item) for item in report.expected_outputs]
    intake_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with expectations_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "expectation_index",
                "output_name",
                "expected_path_hint",
                "required_after_manual_run",
                "producer_stage",
                "intake_check",
                "safety_boundary",
            ]
        )
        for item in report.expected_outputs:
            writer.writerow(
                [
                    item.expectation_index,
                    item.output_name,
                    item.expected_path_hint,
                    item.required_after_manual_run,
                    item.producer_stage,
                    item.intake_check,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Recorded Backtest Run Output Intake Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for post-run output verification: {report.ready_for_post_run_output_verification}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Expected outputs: {report.expected_output_count}",
        f"Command steps carried forward: {report.command_step_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Post-v1.0 Phase 1: Real Backtest Usage Sprint complete.",
        "- Post-v1.0 Phase 2: Dashboard Sprint complete.",
        f"- Completed total before Module FFFF: {report.completed_total_before_module} modules.",
        f"- Completed total after Module FFFF: {report.completed_total_after_module} modules.",
        f"- Phase 3 pending before Module FFFF: {report.phase_3_pending_before_module} modules.",
        f"- Phase 3 pending after Module FFFF: {report.phase_3_pending_after_module} modules.",
        f"- Full HQE product estimate after Module FFFF: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Expected post-run outputs:",
    ]

    for item in report.expected_outputs:
        lines.append(f"{item.expectation_index}. {item.output_name} [{item.producer_stage}]")
        lines.append(f"   Path hint: {item.expected_path_hint}")
        lines.append(f"   Required after manual run: {item.required_after_manual_run}")
        lines.append(f"   Intake check: {item.intake_check}")
        lines.append(f"   Safety: {item.safety_boundary}")

    lines.extend(["", "Command steps carried forward:"])
    for step_name in report.command_step_names:
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
        lines.append("- PASS: Recorded-data paper backtest output intake is ready.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {intake_json}",
            f"- {intake_txt}",
            f"- {expectations_csv}",
            f"- {manifest_json}",
        ]
    )
    intake_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_backtest_run_output_intake_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_post_run_output_verification": report.ready_for_post_run_output_verification,
        "selected_dataset_path": report.selected_dataset_path,
        "expected_output_count": report.expected_output_count,
        "command_step_count": report.command_step_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_3_pending_after_module": report.phase_3_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "recorded_backtest_run_output_intake_pack_json": str(intake_json),
            "recorded_backtest_run_output_intake_pack_txt": str(intake_txt),
            "recorded_backtest_expected_outputs_csv": str(expectations_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "recorded_backtest_run_output_intake_pack_json": intake_json,
        "recorded_backtest_run_output_intake_pack_txt": intake_txt,
        "recorded_backtest_expected_outputs_csv": expectations_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_recorded_backtest_run_output_intake_report(
    *,
    recorded_backtest_command_plan_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[RecordedBacktestRunOutputIntakeReport, dict[str, Path]]:
    report = build_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=recorded_backtest_command_plan_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_recorded_backtest_run_output_intake_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build recorded-data paper backtest run output intake pack."
    )
    parser.add_argument(
        "--recorded-backtest-command-plan",
        default=(
            "reports/paper_trading/"
            "recorded_backtest_command_plan_pack/"
            "recorded_backtest_command_plan_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_backtest_run_output_intake_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=Path(args.recorded_backtest_command_plan),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded backtest run output intake pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for post-run output verification: {report.ready_for_post_run_output_verification}")
    print(f"Recorded backtest run output intake: {outputs['recorded_backtest_run_output_intake_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
