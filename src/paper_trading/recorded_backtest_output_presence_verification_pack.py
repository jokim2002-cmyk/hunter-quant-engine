"""
Recorded backtest output presence verification pack.

Module GGGG in the post-dashboard recorded-data paper backtest review phase.

This module reads the recorded backtest run output intake pack and verifies
whether the expected post-run paper backtest output files are present.

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


REQUIRED_EXPECTED_OUTPUTS = {
    "real_dataset_backtest_input_pack",
    "first_real_dataset_backtest_run_pack",
    "backtest_trade_ledger",
    "backtest_metrics",
    "backtest_report",
    "first_real_backtest_output_verification",
    "first_real_backtest_report_review",
    "git_generated_outputs_guard",
}

NON_FILE_OUTPUTS = {"git_generated_outputs_guard"}

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
class RecordedBacktestOutputPresenceCheck:
    check_index: int
    output_name: str
    expected_path_hint: str
    resolved_path: str
    required_after_manual_run: bool
    exists: bool
    check_status: str
    intake_check: str
    safety_boundary: str


@dataclass(frozen=True)
class RecordedBacktestOutputPresenceIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class RecordedBacktestOutputPresenceReport:
    generated_at_utc: str
    recorded_backtest_run_output_intake_path: str
    project_root: str
    output_directory: str
    status: str
    ready_for_recorded_backtest_review_summary: bool
    selected_dataset_path: str
    safety_notice: str
    expected_output_count: int
    presence_check_count: int
    present_required_file_count: int
    missing_required_file_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_3_pending_before_module: int
    phase_3_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_action: str
    issues: list[RecordedBacktestOutputPresenceIssue]
    presence_checks: list[RecordedBacktestOutputPresenceCheck]
    expected_output_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation recorded backtest output presence verification pack "
        "only. This pack verifies whether expected recorded-data paper backtest "
        "output files are present after a manual run. It does not start a "
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
) -> RecordedBacktestOutputPresenceIssue:
    return RecordedBacktestOutputPresenceIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[RecordedBacktestOutputPresenceIssue]) -> str:
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


def _load_intake_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[RecordedBacktestOutputPresenceIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "recorded_backtest_run_output_intake_pack_missing",
                1,
                f"Recorded backtest run output intake pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "recorded_backtest_run_output_intake_pack_invalid_json",
                1,
                f"Recorded backtest run output intake pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "recorded_backtest_run_output_intake_pack_invalid_shape",
                1,
                "Recorded backtest run output intake pack must be a JSON object.",
            )
        ]

    return payload, []


def _intake_pack_issues(
    intake: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[RecordedBacktestOutputPresenceIssue]:
    if intake is None:
        return []

    issues: list[RecordedBacktestOutputPresenceIssue] = []

    status = str(intake.get("status") or "unknown").lower()
    ready = bool(intake.get("ready_for_post_run_output_verification"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "recorded_backtest_run_output_intake_pack_warn",
                1,
                "Recorded backtest run output intake pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_run_output_intake_pack_not_pass",
                1,
                f"Recorded backtest run output intake pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_run_output_intake_pack_not_ready",
                1,
                "Recorded backtest run output intake pack is not ready for output verification.",
            )
        )

    forbidden = _forbidden(intake)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "recorded_backtest_run_output_intake_forbidden_fields",
                len(forbidden),
                "Recorded backtest run output intake pack contains forbidden broker/order fields.",
            )
        )

    intake_issues = intake.get("issues")
    if isinstance(intake_issues, list):
        fail_count = sum(
            1
            for item in intake_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "recorded_backtest_run_output_intake_contains_fail_issues",
                    fail_count,
                    "Recorded backtest run output intake pack contains fail issues.",
                )
            )

    return issues


def _expected_output_records(intake: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if intake is None:
        return []

    raw_outputs = intake.get("expected_outputs")
    if not isinstance(raw_outputs, list):
        return []

    return [item for item in raw_outputs if isinstance(item, Mapping)]


def _expected_output_names(intake: Mapping[str, Any] | None) -> list[str]:
    return sorted(
        {
            str(item.get("output_name") or "").strip().lower()
            for item in _expected_output_records(intake)
            if str(item.get("output_name") or "").strip()
        }
    )


def _readiness_issues(
    *,
    expected_output_names: Sequence[str],
) -> list[RecordedBacktestOutputPresenceIssue]:
    missing_outputs = REQUIRED_EXPECTED_OUTPUTS - set(expected_output_names)

    if missing_outputs:
        return [
            _issue(
                "fail",
                "required_recorded_backtest_expected_outputs_missing",
                len(missing_outputs),
                "Required recorded backtest expected outputs are missing from intake pack.",
            )
        ]

    return []


def _resolve_path(project_root: Path, path_hint: str) -> Path:
    path = Path(str(path_hint).strip())
    if path.is_absolute():
        return path
    return project_root / path


def _presence_checks(
    *,
    expected_outputs: Sequence[Mapping[str, Any]],
    project_root: Path,
) -> list[RecordedBacktestOutputPresenceCheck]:
    checks: list[RecordedBacktestOutputPresenceCheck] = []

    for index, item in enumerate(expected_outputs, start=1):
        output_name = str(item.get("output_name") or "").strip().lower()
        path_hint = str(item.get("expected_path_hint") or "").strip()
        required = bool(item.get("required_after_manual_run"))
        intake_check = str(item.get("intake_check") or "").strip()
        safety_boundary = str(item.get("safety_boundary") or "").strip()

        if output_name in NON_FILE_OUTPUTS or path_hint.lower() == "git status --short":
            resolved = path_hint or "manual_git_status_check"
            exists = True
            check_status = "manual_check"
        else:
            resolved_path = _resolve_path(project_root, path_hint)
            resolved = str(resolved_path)
            exists = resolved_path.exists()
            check_status = "present" if exists else "missing"

        checks.append(
            RecordedBacktestOutputPresenceCheck(
                check_index=index,
                output_name=output_name,
                expected_path_hint=path_hint,
                resolved_path=resolved,
                required_after_manual_run=required,
                exists=exists,
                check_status=check_status,
                intake_check=intake_check,
                safety_boundary=safety_boundary,
            )
        )

    return checks


def _presence_issues(
    checks: Sequence[RecordedBacktestOutputPresenceCheck],
) -> list[RecordedBacktestOutputPresenceIssue]:
    missing_required = [
        check
        for check in checks
        if check.required_after_manual_run
        and check.output_name not in NON_FILE_OUTPUTS
        and not check.exists
    ]

    if missing_required:
        return [
            _issue(
                "fail",
                "required_recorded_backtest_output_files_missing",
                len(missing_required),
                "Required recorded-data paper backtest output files are missing after manual run.",
            )
        ]

    return []


def build_recorded_backtest_output_presence_report(
    *,
    recorded_backtest_run_output_intake_path: Path,
    output_dir: Path,
    project_root: Path | None = None,
    allow_warnings: bool = False,
) -> RecordedBacktestOutputPresenceReport:
    root = Path.cwd() if project_root is None else project_root
    intake, load_issues = _load_intake_pack(recorded_backtest_run_output_intake_path)

    issues: list[RecordedBacktestOutputPresenceIssue] = []
    issues.extend(load_issues)
    issues.extend(_intake_pack_issues(intake, allow_warnings=allow_warnings))

    expected_output_names = _expected_output_names(intake)
    issues.extend(_readiness_issues(expected_output_names=expected_output_names))

    expected_outputs = _expected_output_records(intake)
    checks = _presence_checks(expected_outputs=expected_outputs, project_root=root)
    issues.extend(_presence_issues(checks))

    present_required_files = sum(
        1
        for check in checks
        if check.required_after_manual_run
        and check.output_name not in NON_FILE_OUTPUTS
        and check.exists
    )
    missing_required_files = sum(
        1
        for check in checks
        if check.required_after_manual_run
        and check.output_name not in NON_FILE_OUTPUTS
        and not check.exists
    )

    status = _status(issues)

    return RecordedBacktestOutputPresenceReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        recorded_backtest_run_output_intake_path=str(recorded_backtest_run_output_intake_path),
        project_root=str(root),
        output_directory=str(output_dir),
        status=status,
        ready_for_recorded_backtest_review_summary=status in {"pass", "warn"},
        selected_dataset_path=str((intake or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        expected_output_count=len(expected_output_names),
        presence_check_count=len(checks),
        present_required_file_count=present_required_files,
        missing_required_file_count=missing_required_files,
        completed_total_before_module=84,
        completed_total_after_module=85,
        phase_3_pending_before_module=3,
        phase_3_pending_after_module=2,
        full_hqe_product_estimate_after_module="77-82%",
        recommended_next_action=(
            "If all required post-run files are present, build the recorded backtest "
            "review summary next. Missing files mean the manual paper backtest run "
            "or output verification must be completed first."
        ),
        issues=issues,
        presence_checks=checks,
        expected_output_names=expected_output_names,
    )


def write_recorded_backtest_output_presence_report(
    report: RecordedBacktestOutputPresenceReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    presence_json = output_dir / "recorded_backtest_output_presence_verification_pack.json"
    presence_txt = output_dir / "recorded_backtest_output_presence_verification_pack.txt"
    checks_csv = output_dir / "recorded_backtest_output_presence_checks.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["presence_checks"] = [asdict(check) for check in report.presence_checks]
    presence_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with checks_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "check_index",
                "output_name",
                "expected_path_hint",
                "resolved_path",
                "required_after_manual_run",
                "exists",
                "check_status",
                "intake_check",
                "safety_boundary",
            ]
        )
        for check in report.presence_checks:
            writer.writerow(
                [
                    check.check_index,
                    check.output_name,
                    check.expected_path_hint,
                    check.resolved_path,
                    check.required_after_manual_run,
                    check.exists,
                    check.check_status,
                    check.intake_check,
                    check.safety_boundary,
                ]
            )

    lines = [
        "HQE Recorded Backtest Output Presence Verification Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for recorded backtest review summary: {report.ready_for_recorded_backtest_review_summary}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Project root: {report.project_root}",
        f"Expected outputs: {report.expected_output_count}",
        f"Presence checks: {report.presence_check_count}",
        f"Present required files: {report.present_required_file_count}",
        f"Missing required files: {report.missing_required_file_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Post-v1.0 Phase 1: Real Backtest Usage Sprint complete.",
        "- Post-v1.0 Phase 2: Dashboard Sprint complete.",
        f"- Completed total before Module GGGG: {report.completed_total_before_module} modules.",
        f"- Completed total after Module GGGG: {report.completed_total_after_module} modules.",
        f"- Phase 3 pending before Module GGGG: {report.phase_3_pending_before_module} modules.",
        f"- Phase 3 pending after Module GGGG: {report.phase_3_pending_after_module} modules.",
        f"- Full HQE product estimate after Module GGGG: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next action:",
        report.recommended_next_action,
        "",
        "Presence checks:",
    ]

    for check in report.presence_checks:
        lines.append(f"{check.check_index}. {check.output_name} [{check.check_status}]")
        lines.append(f"   Path hint: {check.expected_path_hint}")
        lines.append(f"   Resolved path: {check.resolved_path}")
        lines.append(f"   Required after manual run: {check.required_after_manual_run}")
        lines.append(f"   Exists: {check.exists}")
        lines.append(f"   Safety: {check.safety_boundary}")

    lines.extend(["", "Expected output names:"])
    for output_name in report.expected_output_names:
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
        lines.append("- PASS: Recorded-data paper backtest output presence verification passed.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {presence_json}",
            f"- {presence_txt}",
            f"- {checks_csv}",
            f"- {manifest_json}",
        ]
    )
    presence_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_backtest_output_presence_verification_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_recorded_backtest_review_summary": report.ready_for_recorded_backtest_review_summary,
        "selected_dataset_path": report.selected_dataset_path,
        "expected_output_count": report.expected_output_count,
        "presence_check_count": report.presence_check_count,
        "present_required_file_count": report.present_required_file_count,
        "missing_required_file_count": report.missing_required_file_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_3_pending_after_module": report.phase_3_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_action": report.recommended_next_action,
        "safety_notice": report.safety_notice,
        "outputs": {
            "recorded_backtest_output_presence_verification_pack_json": str(presence_json),
            "recorded_backtest_output_presence_verification_pack_txt": str(presence_txt),
            "recorded_backtest_output_presence_checks_csv": str(checks_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "recorded_backtest_output_presence_verification_pack_json": presence_json,
        "recorded_backtest_output_presence_verification_pack_txt": presence_txt,
        "recorded_backtest_output_presence_checks_csv": checks_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_recorded_backtest_output_presence_report(
    *,
    recorded_backtest_run_output_intake_path: Path,
    output_dir: Path,
    project_root: Path | None = None,
    allow_warnings: bool = False,
) -> tuple[RecordedBacktestOutputPresenceReport, dict[str, Path]]:
    report = build_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=recorded_backtest_run_output_intake_path,
        output_dir=output_dir,
        project_root=project_root,
        allow_warnings=allow_warnings,
    )
    outputs = write_recorded_backtest_output_presence_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build recorded-data paper backtest output presence verification pack."
    )
    parser.add_argument(
        "--recorded-backtest-run-output-intake",
        default=(
            "reports/paper_trading/"
            "recorded_backtest_run_output_intake_pack/"
            "recorded_backtest_run_output_intake_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_backtest_output_presence_verification_pack",
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=Path(args.recorded_backtest_run_output_intake),
        output_dir=Path(args.output_dir),
        project_root=Path(args.project_root),
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded backtest output presence verification pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Missing required files: {report.missing_required_file_count}")
    print(f"Output presence verification: {outputs['recorded_backtest_output_presence_verification_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
