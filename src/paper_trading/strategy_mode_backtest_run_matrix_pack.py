"""
Strategy mode backtest run matrix pack.

Module RRR in the post-v1.0 Real Backtest Usage Sprint.

This module reads the strategy mode comparison pack and creates a paper-only
run matrix for strict, balanced, and relaxed future recorded-data backtests.

It does not run a backtest, modify strategy logic, connect to brokers,
request live market data, place real orders, use real money, or prove
profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_MODES = {"strict", "balanced", "relaxed"}

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
class StrategyModeBacktestRun:
    run_index: int
    mode_name: str
    command: str
    mode_config_reference: str
    expected_output_directory: str
    purpose: str


@dataclass(frozen=True)
class StrategyModeBacktestRunMatrixIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class StrategyModeBacktestRunMatrixReport:
    generated_at_utc: str
    mode_comparison_pack_path: str
    output_directory: str
    status: str
    ready_for_future_mode_backtest_execution: bool
    selected_dataset_path: str
    safety_notice: str
    mode_count: int
    run_count: int
    issues: list[StrategyModeBacktestRunMatrixIssue]
    runs: list[StrategyModeBacktestRun]
    mode_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation strategy mode backtest run matrix pack only. This "
        "pack converts strict, balanced, and relaxed paper-only modes into a "
        "future recorded-data run matrix. It does not run a backtest, does "
        "not modify strategy logic, does not connect to brokers, request live "
        "market data, place real orders, use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> StrategyModeBacktestRunMatrixIssue:
    return StrategyModeBacktestRunMatrixIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[StrategyModeBacktestRunMatrixIssue]) -> str:
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


def _load_mode_comparison_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[StrategyModeBacktestRunMatrixIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "strategy_mode_comparison_pack_missing",
                1,
                f"Strategy mode comparison pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "strategy_mode_comparison_pack_invalid_json",
                1,
                f"Strategy mode comparison pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "strategy_mode_comparison_pack_invalid_shape",
                1,
                "Strategy mode comparison pack must be a JSON object.",
            )
        ]

    return payload, []


def _comparison_pack_issues(
    comparison: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[StrategyModeBacktestRunMatrixIssue]:
    if comparison is None:
        return []

    issues: list[StrategyModeBacktestRunMatrixIssue] = []

    status = str(comparison.get("status") or "unknown").lower()
    ready = bool(comparison.get("ready_for_future_paper_mode_backtest"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "strategy_mode_comparison_pack_warn",
                1,
                "Strategy mode comparison pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "strategy_mode_comparison_pack_not_pass",
                1,
                f"Strategy mode comparison pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "strategy_mode_comparison_pack_not_ready",
                1,
                "Strategy mode comparison pack is not ready for future paper mode backtest.",
            )
        )

    forbidden = _forbidden(comparison)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "strategy_mode_comparison_pack_forbidden_fields",
                len(forbidden),
                "Strategy mode comparison pack contains forbidden broker/order/real-money fields.",
            )
        )

    comparison_issues = comparison.get("issues")
    if isinstance(comparison_issues, list):
        fail_count = sum(
            1
            for item in comparison_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "strategy_mode_comparison_pack_contains_fail_issues",
                    fail_count,
                    "Strategy mode comparison pack contains fail issues.",
                )
            )

    return issues


def _mode_names(comparison: Mapping[str, Any] | None) -> list[str]:
    if comparison is None:
        return []

    raw_modes = comparison.get("modes")
    if not isinstance(raw_modes, list):
        return []

    names = sorted(
        {
            str(mode.get("mode_name") or "").strip().lower()
            for mode in raw_modes
            if isinstance(mode, Mapping) and str(mode.get("mode_name") or "").strip()
        }
    )
    return names


def _mode_issues(mode_names: Sequence[str]) -> list[StrategyModeBacktestRunMatrixIssue]:
    issues: list[StrategyModeBacktestRunMatrixIssue] = []
    mode_set = set(mode_names)

    missing = REQUIRED_MODES - mode_set
    extra = mode_set - REQUIRED_MODES

    if missing:
        issues.append(
            _issue(
                "fail",
                "required_strategy_modes_missing",
                len(missing),
                "Required strategy modes are missing from comparison pack.",
            )
        )

    if extra:
        issues.append(
            _issue(
                "warn",
                "unexpected_strategy_modes_present",
                len(extra),
                "Unexpected strategy modes are present and will not be part of the core matrix.",
            )
        )

    return issues


def _run_matrix(mode_names: Sequence[str]) -> list[StrategyModeBacktestRun]:
    ordered_modes = [mode for mode in ["strict", "balanced", "relaxed"] if mode in set(mode_names)]

    runs: list[StrategyModeBacktestRun] = []
    for index, mode_name in enumerate(ordered_modes, start=1):
        output_dir = f"reports/paper_trading/mode_backtests/{mode_name}"
        command = (
            ".\\hqe_recorded_data_one_command_backtest_runner.bat "
            f"--mode {mode_name} --output-dir {output_dir}"
        )
        runs.append(
            StrategyModeBacktestRun(
                run_index=index,
                mode_name=mode_name,
                command=command,
                mode_config_reference=f"strategy_mode_definitions.csv::{mode_name}",
                expected_output_directory=output_dir,
                purpose=(
                    f"Future paper-only recorded-data backtest run for {mode_name} mode. "
                    "This command is a planning matrix entry, not live execution."
                ),
            )
        )

    return runs


def build_strategy_mode_backtest_run_matrix_report(
    *,
    mode_comparison_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> StrategyModeBacktestRunMatrixReport:
    comparison, load_issues = _load_mode_comparison_pack(mode_comparison_pack_path)

    issues: list[StrategyModeBacktestRunMatrixIssue] = []
    issues.extend(load_issues)
    issues.extend(_comparison_pack_issues(comparison, allow_warnings=allow_warnings))

    names = _mode_names(comparison)
    issues.extend(_mode_issues(names))

    runs = _run_matrix(names)
    status = _status(issues)

    return StrategyModeBacktestRunMatrixReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        mode_comparison_pack_path=str(mode_comparison_pack_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_mode_backtest_execution=status in {"pass", "warn"},
        selected_dataset_path=str((comparison or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        mode_count=len(names),
        run_count=len(runs),
        issues=issues,
        runs=runs,
        mode_names=names,
    )


def write_strategy_mode_backtest_run_matrix_report(
    report: StrategyModeBacktestRunMatrixReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    matrix_json = output_dir / "strategy_mode_backtest_run_matrix_pack.json"
    matrix_txt = output_dir / "strategy_mode_backtest_run_matrix_pack.txt"
    matrix_csv = output_dir / "strategy_mode_backtest_run_matrix.csv"
    commands_bat = output_dir / "strategy_mode_backtest_run_matrix_commands.bat"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["runs"] = [asdict(run) for run in report.runs]
    matrix_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with matrix_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "run_index",
                "mode_name",
                "command",
                "mode_config_reference",
                "expected_output_directory",
                "purpose",
            ]
        )
        for run in report.runs:
            writer.writerow(
                [
                    run.run_index,
                    run.mode_name,
                    run.command,
                    run.mode_config_reference,
                    run.expected_output_directory,
                    run.purpose,
                ]
            )

    bat_lines = [
        "@echo off",
        "setlocal",
        "echo HQE strategy mode backtest run matrix",
        "echo Paper/simulation only. No broker orders. No real money.",
        "echo This command file is generated as a future run matrix.",
        "echo.",
    ]
    for run in report.runs:
        bat_lines.append(f"echo Future run {run.run_index}: {run.mode_name}")
        bat_lines.append(f"echo {run.command}")
    commands_bat.write_text("\n".join(bat_lines) + "\n", encoding="utf-8")

    lines = [
        "HQE Strategy Mode Backtest Run Matrix Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future mode backtest execution: {report.ready_for_future_mode_backtest_execution}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Modes: {report.mode_count}",
        f"Runs: {report.run_count}",
        "",
        "Run matrix:",
    ]

    if not report.runs:
        lines.append("- No run matrix entries were created.")
    else:
        for run in report.runs:
            lines.append(
                (
                    f"{run.run_index}. {run.mode_name}: {run.command} "
                    f"-> {run.expected_output_directory}"
                )
            )

    lines.extend(
        [
            "",
            "Safety:",
            "- This pack does not run a backtest.",
            "- This pack does not change strategy logic.",
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
        lines.append("- PASS: Strategy mode run matrix is ready for future paper-only mode backtests.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {matrix_json}",
            f"- {matrix_txt}",
            f"- {matrix_csv}",
            f"- {commands_bat}",
            f"- {manifest_json}",
        ]
    )
    matrix_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "strategy_mode_backtest_run_matrix_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_mode_backtest_execution": report.ready_for_future_mode_backtest_execution,
        "selected_dataset_path": report.selected_dataset_path,
        "mode_count": report.mode_count,
        "run_count": report.run_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "strategy_mode_backtest_run_matrix_pack_json": str(matrix_json),
            "strategy_mode_backtest_run_matrix_pack_txt": str(matrix_txt),
            "strategy_mode_backtest_run_matrix_csv": str(matrix_csv),
            "strategy_mode_backtest_run_matrix_commands_bat": str(commands_bat),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "strategy_mode_backtest_run_matrix_pack_json": matrix_json,
        "strategy_mode_backtest_run_matrix_pack_txt": matrix_txt,
        "strategy_mode_backtest_run_matrix_csv": matrix_csv,
        "strategy_mode_backtest_run_matrix_commands_bat": commands_bat,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_mode_backtest_run_matrix_report(
    *,
    mode_comparison_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[StrategyModeBacktestRunMatrixReport, dict[str, Path]]:
    report = build_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=mode_comparison_pack_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_strategy_mode_backtest_run_matrix_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build strategy mode backtest run matrix pack."
    )
    parser.add_argument(
        "--mode-comparison-pack",
        default=(
            "reports/paper_trading/"
            "strategy_mode_comparison_pack/"
            "strategy_mode_comparison_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/strategy_mode_backtest_run_matrix_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=Path(args.mode_comparison_pack),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE strategy mode backtest run matrix pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future mode backtest execution: {report.ready_for_future_mode_backtest_execution}")
    print(f"Runs: {report.run_count}")
    print(f"Run matrix pack: {outputs['strategy_mode_backtest_run_matrix_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
