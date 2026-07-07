"""
Recorded data backtest acceptance gate.

Module DDD in the fast-track v1.0 Testing Edition path.

This module validates the one-command paper backtest runner output before
future v1.0 testing-release readiness.

It does not connect to brokers, request live market data, place real orders,
use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPECTED_STAGE_NAMES = {
    "strategy_replay_sandbox",
    "strategy_decision_audit",
    "strategy_decision_acceptance",
    "paper_option_trade_plan_simulator",
    "paper_fill_exit_simulator",
    "backtest_trade_ledger",
    "backtest_metrics_engine",
    "backtest_report_writer",
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
class BacktestAcceptanceIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class BacktestAcceptanceReport:
    generated_at_utc: str
    runner_report_path: str
    output_directory: str
    status: str
    accepted_for_future_v1_testing_release_gate: bool
    min_stage_count_required: int
    min_passed_stage_count_required: int
    stage_count: int
    passed_stage_count: int
    warning_stage_count: int
    failed_stage_count: int
    final_backtest_report_path: str
    final_metrics_path: str
    final_trade_ledger_path: str
    safety_notice: str
    issues: list[BacktestAcceptanceIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation backtest acceptance gate only. This gate validates "
        "one-command recorded replay paper backtest evidence. It does not "
        "connect to brokers, request live market data, place real orders, use "
        "real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> BacktestAcceptanceIssue:
    return BacktestAcceptanceIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[BacktestAcceptanceIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _to_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _load_runner_report(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[BacktestAcceptanceIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "one_command_runner_report_missing",
                1,
                f"One-command backtest runner report missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "one_command_runner_report_invalid_json",
                1,
                f"One-command backtest runner report JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "one_command_runner_report_invalid_shape",
                1,
                "One-command backtest runner report must be a JSON object.",
            )
        ]

    return payload, []


def _runner_report_issues(
    payload: Mapping[str, Any] | None,
    *,
    min_stage_count: int,
    min_passed_stage_count: int,
    allow_warnings: bool,
    require_final_outputs_exist: bool,
) -> list[BacktestAcceptanceIssue]:
    if payload is None:
        return []

    issues: list[BacktestAcceptanceIssue] = []

    status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_backtest_acceptance_gate"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "one_command_runner_warn",
                1,
                "One-command backtest runner status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "one_command_runner_not_pass",
                1,
                f"One-command backtest runner status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "one_command_runner_not_ready",
                1,
                "One-command backtest runner is not ready for backtest acceptance gate.",
            )
        )

    forbidden = _forbidden(payload)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "one_command_runner_forbidden_fields",
                len(forbidden),
                "Runner report contains forbidden broker/order/real-money fields.",
            )
        )

    stage_count = _to_int(payload.get("stage_count")) or 0
    passed_stage_count = _to_int(payload.get("passed_stage_count")) or 0
    warning_stage_count = _to_int(payload.get("warning_stage_count")) or 0
    failed_stage_count = _to_int(payload.get("failed_stage_count")) or 0
    accepted_stage_count = (
        passed_stage_count + warning_stage_count
        if allow_warnings
        else passed_stage_count
    )

    if stage_count < min_stage_count:
        issues.append(
            _issue(
                "fail",
                "insufficient_runner_stages",
                min_stage_count - stage_count,
                f"Runner stage count below minimum. Required={min_stage_count}, actual={stage_count}.",
            )
        )

    if accepted_stage_count < min_passed_stage_count:
        issues.append(
            _issue(
                "fail",
                "insufficient_passed_runner_stages",
                min_passed_stage_count - accepted_stage_count,
                (
                    "Runner accepted-stage count below minimum. "
                    f"Required={min_passed_stage_count}, actual={accepted_stage_count}."
                ),
            )
        )

    if failed_stage_count:
        issues.append(
            _issue(
                "fail",
                "failed_runner_stages_present",
                failed_stage_count,
                "One-command runner has failed stages.",
            )
        )

    stages = payload.get("stages")
    if not isinstance(stages, list):
        issues.append(
            _issue(
                "fail",
                "runner_stages_missing",
                1,
                "One-command runner report must include stages list.",
            )
        )
    else:
        stage_names = {
            str(stage.get("stage_name") or "")
            for stage in stages
            if isinstance(stage, Mapping)
        }
        missing_stages = EXPECTED_STAGE_NAMES - stage_names
        if missing_stages:
            issues.append(
                _issue(
                    "fail",
                    "runner_expected_stages_missing",
                    len(missing_stages),
                    "One-command runner is missing expected paper backtest stages.",
                )
            )

        not_ready_count = sum(
            1
            for stage in stages
            if isinstance(stage, Mapping) and not bool(stage.get("ready"))
        )
        if not_ready_count:
            issues.append(
                _issue(
                    "fail",
                    "runner_stage_not_ready",
                    not_ready_count,
                    "One-command runner contains stages that are not ready.",
                )
            )

        bad_status_count = sum(
            1
            for stage in stages
            if isinstance(stage, Mapping)
            and str(stage.get("status") or "") not in {"pass", "warn"}
        )
        if bad_status_count:
            issues.append(
                _issue(
                    "fail",
                    "runner_stage_bad_status",
                    bad_status_count,
                    "One-command runner contains stage statuses outside pass/warn.",
                )
            )

    final_paths = [
        payload.get("final_backtest_report_path"),
        payload.get("final_metrics_path"),
        payload.get("final_trade_ledger_path"),
    ]
    missing_final_path_fields = [path for path in final_paths if not str(path or "").strip()]
    if missing_final_path_fields:
        issues.append(
            _issue(
                "fail",
                "runner_final_output_paths_missing",
                len(missing_final_path_fields),
                "Runner report must include final report, metrics, and trade ledger paths.",
            )
        )

    if require_final_outputs_exist:
        missing_outputs = [
            str(path)
            for path in final_paths
            if str(path or "").strip() and not Path(str(path)).exists()
        ]
        if missing_outputs:
            issues.append(
                _issue(
                    "fail",
                    "runner_final_outputs_missing_on_disk",
                    len(missing_outputs),
                    "Runner final output files are missing on disk.",
                )
            )

    return issues


def build_backtest_acceptance_report(
    *,
    runner_report_path: Path,
    output_dir: Path,
    min_stage_count: int = 8,
    min_passed_stage_count: int = 8,
    allow_warnings: bool = False,
    require_final_outputs_exist: bool = True,
) -> BacktestAcceptanceReport:
    min_stage_count = max(min_stage_count, 0)
    min_passed_stage_count = max(min_passed_stage_count, 0)

    issues: list[BacktestAcceptanceIssue] = []

    runner_report, load_issues = _load_runner_report(runner_report_path)
    issues.extend(load_issues)
    issues.extend(
        _runner_report_issues(
            runner_report,
            min_stage_count=min_stage_count,
            min_passed_stage_count=min_passed_stage_count,
            allow_warnings=allow_warnings,
            require_final_outputs_exist=require_final_outputs_exist,
        )
    )

    status = _status(issues)

    return BacktestAcceptanceReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        runner_report_path=str(runner_report_path),
        output_directory=str(output_dir),
        status=status,
        accepted_for_future_v1_testing_release_gate=status in {"pass", "warn"},
        min_stage_count_required=min_stage_count,
        min_passed_stage_count_required=min_passed_stage_count,
        stage_count=_to_int((runner_report or {}).get("stage_count")) or 0,
        passed_stage_count=_to_int((runner_report or {}).get("passed_stage_count")) or 0,
        warning_stage_count=_to_int((runner_report or {}).get("warning_stage_count")) or 0,
        failed_stage_count=_to_int((runner_report or {}).get("failed_stage_count")) or 0,
        final_backtest_report_path=str((runner_report or {}).get("final_backtest_report_path") or ""),
        final_metrics_path=str((runner_report or {}).get("final_metrics_path") or ""),
        final_trade_ledger_path=str((runner_report or {}).get("final_trade_ledger_path") or ""),
        safety_notice=safety_notice(),
        issues=issues,
    )


def write_backtest_acceptance_report(
    report: BacktestAcceptanceReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    acceptance_json = output_dir / "backtest_acceptance_gate.json"
    acceptance_txt = output_dir / "backtest_acceptance_gate.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]

    acceptance_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "HQE Recorded Data Backtest Acceptance Gate",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Accepted for future v1.0 testing release gate: {report.accepted_for_future_v1_testing_release_gate}",
        f"Stage count: {report.stage_count}",
        f"Passed stage count: {report.passed_stage_count}",
        f"Warning stage count: {report.warning_stage_count}",
        f"Failed stage count: {report.failed_stage_count}",
        "",
        "Final outputs:",
        f"- Backtest report: {report.final_backtest_report_path}",
        f"- Metrics: {report.final_metrics_path}",
        f"- Trade ledger: {report.final_trade_ledger_path}",
        "",
        "Safety:",
        "- LONG = CE BUY paper plan only.",
        "- SHORT = PE BUY paper plan only.",
        "- NEUTRAL = no trade.",
        "- No option selling.",
        "- No broker orders.",
        "- No live market data.",
        "- No real money.",
        "- This report is not a profitability claim.",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Backtest evidence is accepted for future v1.0 testing release gate.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {acceptance_json}",
            f"- {acceptance_txt}",
            f"- {manifest_json}",
        ]
    )
    acceptance_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_backtest_acceptance_gate",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted_for_future_v1_testing_release_gate": report.accepted_for_future_v1_testing_release_gate,
        "stage_count": report.stage_count,
        "passed_stage_count": report.passed_stage_count,
        "warning_stage_count": report.warning_stage_count,
        "failed_stage_count": report.failed_stage_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "backtest_acceptance_gate_json": str(acceptance_json),
            "backtest_acceptance_gate_txt": str(acceptance_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "backtest_acceptance_gate_json": acceptance_json,
        "backtest_acceptance_gate_txt": acceptance_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_backtest_acceptance_report(
    *,
    runner_report_path: Path,
    output_dir: Path,
    min_stage_count: int = 8,
    min_passed_stage_count: int = 8,
    allow_warnings: bool = False,
    require_final_outputs_exist: bool = True,
) -> tuple[BacktestAcceptanceReport, dict[str, Path]]:
    report = build_backtest_acceptance_report(
        runner_report_path=runner_report_path,
        output_dir=output_dir,
        min_stage_count=min_stage_count,
        min_passed_stage_count=min_passed_stage_count,
        allow_warnings=allow_warnings,
        require_final_outputs_exist=require_final_outputs_exist,
    )
    outputs = write_backtest_acceptance_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the recorded-data paper backtest runner output."
    )
    parser.add_argument(
        "--runner-report",
        default=(
            "reports/paper_trading/"
            "recorded_data_one_command_backtest_runner/"
            "one_command_backtest_runner.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_backtest_acceptance_gate",
    )
    parser.add_argument("--min-stage-count", type=int, default=8)
    parser.add_argument("--min-passed-stage-count", type=int, default=8)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument(
        "--skip-final-output-existence-check",
        action="store_true",
        help="Skip checking whether runner final output paths exist on disk.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_backtest_acceptance_report(
        runner_report_path=Path(args.runner_report),
        output_dir=Path(args.output_dir),
        min_stage_count=args.min_stage_count,
        min_passed_stage_count=args.min_passed_stage_count,
        allow_warnings=args.allow_warnings,
        require_final_outputs_exist=not args.skip_final_output_existence_check,
    )

    print("HQE recorded data backtest acceptance gate completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for future v1.0 testing release gate: {report.accepted_for_future_v1_testing_release_gate}")
    print(f"Backtest acceptance report: {outputs['backtest_acceptance_gate_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
