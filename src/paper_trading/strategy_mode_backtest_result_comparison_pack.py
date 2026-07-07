"""
Strategy mode backtest result comparison pack.

Module SSS in the post-v1.0 Real Backtest Usage Sprint.

This module reads the strategy mode backtest run matrix pack and verifies
strict, balanced, and relaxed paper-only mode backtest result outputs for
future review and comparison.

It does not run backtests, does not calculate profitability, does not modify
strategy logic, does not connect to brokers, does not request live market data,
does not place real orders, does not use real money, or prove profitability.
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

RESULT_CATEGORIES = {
    "ledger": "backtest_trade_ledger.json",
    "metrics": "backtest_metrics.json",
    "report": "backtest_report.json",
    "readiness": "backtest_readiness_gate.json",
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
class ModeBacktestResultPath:
    mode_name: str
    category: str
    path: str
    exists: bool
    required: bool


@dataclass(frozen=True)
class ModeBacktestResultSummary:
    mode_name: str
    expected_output_count: int
    existing_output_count: int
    missing_output_count: int


@dataclass(frozen=True)
class ModeBacktestResultComparisonIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class ModeBacktestResultComparisonReport:
    generated_at_utc: str
    run_matrix_pack_path: str
    output_directory: str
    status: str
    ready_for_future_cost_adjusted_mode_comparison: bool
    selected_dataset_path: str
    safety_notice: str
    mode_count: int
    expected_result_path_count: int
    existing_result_path_count: int
    missing_result_path_count: int
    issues: list[ModeBacktestResultComparisonIssue]
    result_paths: list[ModeBacktestResultPath]
    mode_summaries: list[ModeBacktestResultSummary]
    mode_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation strategy mode backtest result comparison pack only. "
        "This pack verifies strict, balanced, and relaxed paper-only mode "
        "backtest outputs for future review. It does not run backtests, does "
        "not calculate profitability, does not modify strategy logic, does "
        "not connect to brokers, does not request live market data, does not "
        "place real orders, does not use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> ModeBacktestResultComparisonIssue:
    return ModeBacktestResultComparisonIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[ModeBacktestResultComparisonIssue]) -> str:
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


def _load_run_matrix_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[ModeBacktestResultComparisonIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "strategy_mode_backtest_run_matrix_pack_missing",
                1,
                f"Strategy mode backtest run matrix pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "strategy_mode_backtest_run_matrix_pack_invalid_json",
                1,
                f"Strategy mode backtest run matrix pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "strategy_mode_backtest_run_matrix_pack_invalid_shape",
                1,
                "Strategy mode backtest run matrix pack must be a JSON object.",
            )
        ]

    return payload, []


def _run_matrix_issues(
    run_matrix: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[ModeBacktestResultComparisonIssue]:
    if run_matrix is None:
        return []

    issues: list[ModeBacktestResultComparisonIssue] = []

    status = str(run_matrix.get("status") or "unknown").lower()
    ready = bool(run_matrix.get("ready_for_future_mode_backtest_execution"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "strategy_mode_backtest_run_matrix_pack_warn",
                1,
                "Strategy mode backtest run matrix pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "strategy_mode_backtest_run_matrix_pack_not_pass",
                1,
                f"Strategy mode backtest run matrix pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "strategy_mode_backtest_run_matrix_pack_not_ready",
                1,
                "Strategy mode backtest run matrix pack is not ready for future mode backtest execution.",
            )
        )

    forbidden = _forbidden(run_matrix)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "strategy_mode_backtest_run_matrix_pack_forbidden_fields",
                len(forbidden),
                "Strategy mode backtest run matrix pack contains forbidden broker/order/real-money fields.",
            )
        )

    matrix_issues = run_matrix.get("issues")
    if isinstance(matrix_issues, list):
        fail_count = sum(
            1
            for item in matrix_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "strategy_mode_backtest_run_matrix_pack_contains_fail_issues",
                    fail_count,
                    "Strategy mode backtest run matrix pack contains fail issues.",
                )
            )

    return issues


def _runs_by_mode(run_matrix: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    if run_matrix is None:
        return {}

    raw_runs = run_matrix.get("runs")
    if not isinstance(raw_runs, list):
        return {}

    runs: dict[str, Mapping[str, Any]] = {}
    for item in raw_runs:
        if not isinstance(item, Mapping):
            continue

        mode_name = str(item.get("mode_name") or "").strip().lower()
        if not mode_name:
            continue

        runs[mode_name] = item

    return runs


def _mode_issues(mode_names: Sequence[str]) -> list[ModeBacktestResultComparisonIssue]:
    mode_set = set(mode_names)
    missing = REQUIRED_MODES - mode_set

    if missing:
        return [
            _issue(
                "fail",
                "required_strategy_mode_result_runs_missing",
                len(missing),
                "Required strict, balanced, and relaxed result runs are missing.",
            )
        ]

    return []


def _result_paths(runs_by_mode: Mapping[str, Mapping[str, Any]]) -> list[ModeBacktestResultPath]:
    paths: list[ModeBacktestResultPath] = []

    for mode_name in ["strict", "balanced", "relaxed"]:
        run = runs_by_mode.get(mode_name)
        if not run:
            continue

        output_dir = str(run.get("expected_output_directory") or "").strip()
        if not output_dir:
            continue

        for category, filename in RESULT_CATEGORIES.items():
            path = Path(output_dir) / filename
            paths.append(
                ModeBacktestResultPath(
                    mode_name=mode_name,
                    category=category,
                    path=str(path),
                    exists=path.exists(),
                    required=True,
                )
            )

    return paths


def _summaries(result_paths: Sequence[ModeBacktestResultPath]) -> list[ModeBacktestResultSummary]:
    summaries: list[ModeBacktestResultSummary] = []

    for mode_name in ["strict", "balanced", "relaxed"]:
        mode_paths = [path for path in result_paths if path.mode_name == mode_name]
        if not mode_paths:
            continue

        existing = sum(1 for path in mode_paths if path.exists)
        missing = sum(1 for path in mode_paths if not path.exists)
        summaries.append(
            ModeBacktestResultSummary(
                mode_name=mode_name,
                expected_output_count=len(mode_paths),
                existing_output_count=existing,
                missing_output_count=missing,
            )
        )

    return summaries


def build_strategy_mode_backtest_result_comparison_report(
    *,
    run_matrix_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
    require_mode_outputs_exist: bool = True,
) -> ModeBacktestResultComparisonReport:
    run_matrix, load_issues = _load_run_matrix_pack(run_matrix_pack_path)

    issues: list[ModeBacktestResultComparisonIssue] = []
    issues.extend(load_issues)
    issues.extend(_run_matrix_issues(run_matrix, allow_warnings=allow_warnings))

    runs_by_mode = _runs_by_mode(run_matrix)
    mode_names = sorted(runs_by_mode.keys())
    issues.extend(_mode_issues(mode_names))

    result_paths = _result_paths(runs_by_mode)
    missing_paths = [path for path in result_paths if path.required and not path.exists]

    if require_mode_outputs_exist and missing_paths:
        issues.append(
            _issue(
                "fail",
                "strategy_mode_backtest_result_outputs_missing_on_disk",
                len(missing_paths),
                "One or more strategy mode backtest result outputs are missing on disk.",
            )
        )

    summaries = _summaries(result_paths)
    status = _status(issues)

    return ModeBacktestResultComparisonReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        run_matrix_pack_path=str(run_matrix_pack_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_cost_adjusted_mode_comparison=status in {"pass", "warn"},
        selected_dataset_path=str((run_matrix or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        mode_count=len(mode_names),
        expected_result_path_count=len(result_paths),
        existing_result_path_count=sum(1 for path in result_paths if path.exists),
        missing_result_path_count=sum(1 for path in result_paths if not path.exists),
        issues=issues,
        result_paths=result_paths,
        mode_summaries=summaries,
        mode_names=mode_names,
    )


def write_strategy_mode_backtest_result_comparison_report(
    report: ModeBacktestResultComparisonReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    comparison_json = output_dir / "strategy_mode_backtest_result_comparison_pack.json"
    comparison_txt = output_dir / "strategy_mode_backtest_result_comparison_pack.txt"
    result_paths_csv = output_dir / "strategy_mode_backtest_result_paths.csv"
    mode_summary_csv = output_dir / "strategy_mode_backtest_result_summary.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["result_paths"] = [asdict(path) for path in report.result_paths]
    data["mode_summaries"] = [asdict(summary) for summary in report.mode_summaries]
    comparison_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with result_paths_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["mode_name", "category", "required", "exists", "path"])
        for path in report.result_paths:
            writer.writerow(
                [
                    path.mode_name,
                    path.category,
                    path.required,
                    path.exists,
                    path.path,
                ]
            )

    with mode_summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "mode_name",
                "expected_output_count",
                "existing_output_count",
                "missing_output_count",
            ]
        )
        for summary in report.mode_summaries:
            writer.writerow(
                [
                    summary.mode_name,
                    summary.expected_output_count,
                    summary.existing_output_count,
                    summary.missing_output_count,
                ]
            )

    lines = [
        "HQE Strategy Mode Backtest Result Comparison Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future cost-adjusted mode comparison: {report.ready_for_future_cost_adjusted_mode_comparison}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Modes: {report.mode_count}",
        f"Expected result paths: {report.expected_result_path_count}",
        f"Existing result paths: {report.existing_result_path_count}",
        f"Missing result paths: {report.missing_result_path_count}",
        "",
        "Mode summaries:",
    ]

    if not report.mode_summaries:
        lines.append("- No mode summaries were created.")
    else:
        for summary in report.mode_summaries:
            lines.append(
                (
                    f"- {summary.mode_name}: expected={summary.expected_output_count}, "
                    f"existing={summary.existing_output_count}, missing={summary.missing_output_count}"
                )
            )

    lines.extend(["", "Result paths:"])
    if not report.result_paths:
        lines.append("- No result paths were created.")
    else:
        for path in report.result_paths:
            lines.append(
                f"- {path.mode_name}/{path.category}: exists={path.exists}, path={path.path}"
            )

    lines.extend(
        [
            "",
            "Safety:",
            "- This pack does not run backtests.",
            "- This pack does not calculate profitability.",
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
        lines.append("- PASS: Strategy mode results are ready for future cost-adjusted comparison.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {comparison_json}",
            f"- {comparison_txt}",
            f"- {result_paths_csv}",
            f"- {mode_summary_csv}",
            f"- {manifest_json}",
        ]
    )
    comparison_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "strategy_mode_backtest_result_comparison_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_cost_adjusted_mode_comparison": report.ready_for_future_cost_adjusted_mode_comparison,
        "selected_dataset_path": report.selected_dataset_path,
        "mode_count": report.mode_count,
        "expected_result_path_count": report.expected_result_path_count,
        "existing_result_path_count": report.existing_result_path_count,
        "missing_result_path_count": report.missing_result_path_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "strategy_mode_backtest_result_comparison_pack_json": str(comparison_json),
            "strategy_mode_backtest_result_comparison_pack_txt": str(comparison_txt),
            "strategy_mode_backtest_result_paths_csv": str(result_paths_csv),
            "strategy_mode_backtest_result_summary_csv": str(mode_summary_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "strategy_mode_backtest_result_comparison_pack_json": comparison_json,
        "strategy_mode_backtest_result_comparison_pack_txt": comparison_txt,
        "strategy_mode_backtest_result_paths_csv": result_paths_csv,
        "strategy_mode_backtest_result_summary_csv": mode_summary_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_mode_backtest_result_comparison_report(
    *,
    run_matrix_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
    require_mode_outputs_exist: bool = True,
) -> tuple[ModeBacktestResultComparisonReport, dict[str, Path]]:
    report = build_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=run_matrix_pack_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
        require_mode_outputs_exist=require_mode_outputs_exist,
    )
    outputs = write_strategy_mode_backtest_result_comparison_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build strategy mode backtest result comparison pack."
    )
    parser.add_argument(
        "--run-matrix-pack",
        default=(
            "reports/paper_trading/"
            "strategy_mode_backtest_run_matrix_pack/"
            "strategy_mode_backtest_run_matrix_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/strategy_mode_backtest_result_comparison_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--skip-mode-output-existence-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=Path(args.run_matrix_pack),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
        require_mode_outputs_exist=not args.skip_mode_output_existence_check,
    )

    print("HQE strategy mode backtest result comparison pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future cost-adjusted mode comparison: {report.ready_for_future_cost_adjusted_mode_comparison}")
    print(f"Mode result paths: {report.expected_result_path_count}")
    print(f"Comparison pack: {outputs['strategy_mode_backtest_result_comparison_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
