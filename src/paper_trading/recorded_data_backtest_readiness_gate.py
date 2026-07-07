"""
Recorded data backtest readiness gate.

Module EEE in the fast-track v1.0 Testing Edition path.

This module orchestrates the one-command paper backtest runner and the backtest
acceptance gate into a final backtest readiness report.

It does not connect to brokers, request live market data, place real orders,
use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from src.paper_trading.recorded_data_backtest_acceptance_gate import (
    build_and_write_backtest_acceptance_report,
)
from src.paper_trading.recorded_data_one_command_backtest_runner import (
    build_and_write_one_command_backtest_runner_report,
)


@dataclass(frozen=True)
class BacktestReadinessStageResult:
    stage_name: str
    status: str
    ready: bool
    primary_output: str
    detail: str


@dataclass(frozen=True)
class BacktestReadinessIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class BacktestReadinessReport:
    generated_at_utc: str
    consumer_evidence_readiness_path: str
    strategy_input_bars_path: str
    output_directory: str
    status: str
    ready_for_future_v1_testing_release_gate: bool
    min_trades_required: int
    safety_notice: str
    one_command_runner_report_path: str
    backtest_acceptance_report_path: str
    final_backtest_report_path: str
    final_metrics_path: str
    final_trade_ledger_path: str
    stage_count: int
    passed_stage_count: int
    warning_stage_count: int
    failed_stage_count: int
    issues: list[BacktestReadinessIssue]
    stages: list[BacktestReadinessStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation backtest readiness gate only. This gate runs recorded "
        "replay paper backtest evidence and validates acceptance readiness. It "
        "does not connect to brokers, request live market data, place real "
        "orders, use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> BacktestReadinessIssue:
    return BacktestReadinessIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status_from_stages(
    stages: Sequence[BacktestReadinessStageResult],
    issues: Sequence[BacktestReadinessIssue],
) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(stage.status == "fail" for stage in stages):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    if any(stage.status == "warn" for stage in stages):
        return "warn"
    return "pass"


def _stage(
    *,
    stage_name: str,
    status: str,
    ready: bool,
    primary_output: Path | str,
    detail: str,
) -> BacktestReadinessStageResult:
    return BacktestReadinessStageResult(
        stage_name=stage_name,
        status=status,
        ready=ready,
        primary_output=str(primary_output),
        detail=detail,
    )


def _write_report(
    report: BacktestReadinessReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    readiness_json = output_dir / "backtest_readiness_gate.json"
    readiness_txt = output_dir / "backtest_readiness_gate.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["stages"] = [asdict(stage) for stage in report.stages]

    readiness_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Backtest Readiness Gate",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future v1.0 testing release gate: {report.ready_for_future_v1_testing_release_gate}",
        "",
        "Primary outputs:",
        f"- One-command runner report: {report.one_command_runner_report_path}",
        f"- Backtest acceptance report: {report.backtest_acceptance_report_path}",
        f"- Final backtest report: {report.final_backtest_report_path}",
        f"- Final metrics: {report.final_metrics_path}",
        f"- Final trade ledger: {report.final_trade_ledger_path}",
        "",
        "Stage summary:",
        f"- Stage count: {report.stage_count}",
        f"- Passed stages: {report.passed_stage_count}",
        f"- Warning stages: {report.warning_stage_count}",
        f"- Failed stages: {report.failed_stage_count}",
        "",
        "Stages:",
    ]

    for stage in report.stages:
        lines.append(
            f"- {stage.stage_name}: status={stage.status}, ready={stage.ready}, output={stage.primary_output}"
        )

    lines.extend(
        [
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
    )

    if not report.issues:
        lines.append("- PASS: Backtest readiness is accepted for future v1.0 testing release gate.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {readiness_json}",
            f"- {readiness_txt}",
            f"- {manifest_json}",
        ]
    )
    readiness_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_backtest_readiness_gate",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_v1_testing_release_gate": report.ready_for_future_v1_testing_release_gate,
        "stage_count": report.stage_count,
        "passed_stage_count": report.passed_stage_count,
        "warning_stage_count": report.warning_stage_count,
        "failed_stage_count": report.failed_stage_count,
        "one_command_runner_report_path": report.one_command_runner_report_path,
        "backtest_acceptance_report_path": report.backtest_acceptance_report_path,
        "final_backtest_report_path": report.final_backtest_report_path,
        "final_metrics_path": report.final_metrics_path,
        "final_trade_ledger_path": report.final_trade_ledger_path,
        "safety_notice": report.safety_notice,
        "outputs": {
            "backtest_readiness_gate_json": str(readiness_json),
            "backtest_readiness_gate_txt": str(readiness_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "backtest_readiness_gate_json": readiness_json,
        "backtest_readiness_gate_txt": readiness_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_backtest_readiness_report(
    *,
    consumer_evidence_readiness_path: Path,
    strategy_input_bars_path: Path,
    output_dir: Path,
    runner_output_dir: Path,
    acceptance_output_dir: Path,
    sandbox_output_dir: Path,
    decision_audit_output_dir: Path,
    decision_acceptance_output_dir: Path,
    trade_plan_output_dir: Path,
    fill_exit_output_dir: Path,
    trade_ledger_output_dir: Path,
    metrics_output_dir: Path,
    report_writer_output_dir: Path,
    min_bars: int = 1,
    min_decisions: int = 1,
    min_non_neutral_decisions: int = 0,
    min_plans: int = 1,
    min_lifecycles: int = 1,
    min_trades: int = 1,
    min_stage_count: int = 8,
    min_passed_stage_count: int = 8,
    threshold_points: float = 0.0,
    starting_equity_reference: float = 100000.0,
    allow_warnings: bool = False,
    max_bars: int | None = None,
    require_final_outputs_exist: bool = True,
) -> tuple[BacktestReadinessReport, dict[str, Path]]:
    issues: list[BacktestReadinessIssue] = []
    stages: list[BacktestReadinessStageResult] = []

    final_backtest_report_path = ""
    final_metrics_path = ""
    final_trade_ledger_path = ""
    runner_report_path = ""
    acceptance_report_path = ""

    try:
        runner_report, runner_outputs = build_and_write_one_command_backtest_runner_report(
            consumer_evidence_readiness_path=consumer_evidence_readiness_path,
            strategy_input_bars_path=strategy_input_bars_path,
            output_dir=runner_output_dir,
            sandbox_output_dir=sandbox_output_dir,
            decision_audit_output_dir=decision_audit_output_dir,
            decision_acceptance_output_dir=decision_acceptance_output_dir,
            trade_plan_output_dir=trade_plan_output_dir,
            fill_exit_output_dir=fill_exit_output_dir,
            trade_ledger_output_dir=trade_ledger_output_dir,
            metrics_output_dir=metrics_output_dir,
            report_writer_output_dir=report_writer_output_dir,
            min_bars=min_bars,
            min_decisions=min_decisions,
            min_non_neutral_decisions=min_non_neutral_decisions,
            min_plans=min_plans,
            min_lifecycles=min_lifecycles,
            min_trades=min_trades,
            threshold_points=threshold_points,
            starting_equity_reference=starting_equity_reference,
            allow_warnings=allow_warnings,
            max_bars=max_bars,
        )
        runner_report_path = str(runner_outputs["one_command_backtest_runner_json"])
        final_backtest_report_path = runner_report.final_backtest_report_path
        final_metrics_path = runner_report.final_metrics_path
        final_trade_ledger_path = runner_report.final_trade_ledger_path

        stages.append(
            _stage(
                stage_name="one_command_backtest_runner",
                status=runner_report.status,
                ready=runner_report.ready_for_future_backtest_acceptance_gate,
                primary_output=runner_outputs["one_command_backtest_runner_json"],
                detail="One-command paper backtest runner completed.",
            )
        )

        acceptance_report, acceptance_outputs = build_and_write_backtest_acceptance_report(
            runner_report_path=runner_outputs["one_command_backtest_runner_json"],
            output_dir=acceptance_output_dir,
            min_stage_count=min_stage_count,
            min_passed_stage_count=min_passed_stage_count,
            allow_warnings=allow_warnings,
            require_final_outputs_exist=require_final_outputs_exist,
        )
        acceptance_report_path = str(acceptance_outputs["backtest_acceptance_gate_json"])

        stages.append(
            _stage(
                stage_name="backtest_acceptance_gate",
                status=acceptance_report.status,
                ready=acceptance_report.accepted_for_future_v1_testing_release_gate,
                primary_output=acceptance_outputs["backtest_acceptance_gate_json"],
                detail="Backtest acceptance gate completed.",
            )
        )

    except Exception as exc:  # pragma: no cover - behavior-level safety catch
        issues.append(
            _issue(
                "fail",
                "backtest_readiness_exception",
                1,
                f"Backtest readiness gate failed: {exc}",
            )
        )

    status = _status_from_stages(stages, issues)
    passed_stage_count = sum(1 for stage in stages if stage.status == "pass")
    warning_stage_count = sum(1 for stage in stages if stage.status == "warn")
    failed_stage_count = sum(1 for stage in stages if stage.status == "fail")

    report = BacktestReadinessReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        consumer_evidence_readiness_path=str(consumer_evidence_readiness_path),
        strategy_input_bars_path=str(strategy_input_bars_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_v1_testing_release_gate=status in {"pass", "warn"} and len(stages) == 2,
        min_trades_required=max(min_trades, 0),
        safety_notice=safety_notice(),
        one_command_runner_report_path=runner_report_path,
        backtest_acceptance_report_path=acceptance_report_path,
        final_backtest_report_path=final_backtest_report_path,
        final_metrics_path=final_metrics_path,
        final_trade_ledger_path=final_trade_ledger_path,
        stage_count=len(stages),
        passed_stage_count=passed_stage_count,
        warning_stage_count=warning_stage_count,
        failed_stage_count=failed_stage_count,
        issues=issues,
        stages=stages,
    )

    outputs = _write_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run and validate recorded-data paper backtest readiness."
    )
    parser.add_argument(
        "--consumer-evidence-readiness",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness/"
            "paper_strategy_adapter_dry_run_consumer_evidence_readiness.json"
        ),
    )
    parser.add_argument(
        "--strategy-input-bars",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_input_contract/"
            "strategy_input_bars.jsonl"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_backtest_readiness_gate",
    )
    parser.add_argument("--base-stage-output-dir", default="reports/paper_trading")
    parser.add_argument("--min-bars", type=int, default=1)
    parser.add_argument("--min-decisions", type=int, default=1)
    parser.add_argument("--min-non-neutral-decisions", type=int, default=0)
    parser.add_argument("--min-plans", type=int, default=1)
    parser.add_argument("--min-lifecycles", type=int, default=1)
    parser.add_argument("--min-trades", type=int, default=1)
    parser.add_argument("--min-stage-count", type=int, default=8)
    parser.add_argument("--min-passed-stage-count", type=int, default=8)
    parser.add_argument("--threshold-points", type=float, default=0.0)
    parser.add_argument("--starting-equity-reference", type=float, default=100000.0)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-bars", type=int, default=None)
    parser.add_argument("--skip-final-output-existence-check", action="store_true")
    return parser.parse_args(argv)


def _stage_dir(base: Path, name: str) -> Path:
    return base / name


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    base = Path(args.base_stage_output_dir)

    report, outputs = build_and_write_backtest_readiness_report(
        consumer_evidence_readiness_path=Path(args.consumer_evidence_readiness),
        strategy_input_bars_path=Path(args.strategy_input_bars),
        output_dir=Path(args.output_dir),
        runner_output_dir=_stage_dir(base, "recorded_data_one_command_backtest_runner"),
        acceptance_output_dir=_stage_dir(base, "recorded_data_backtest_acceptance_gate"),
        sandbox_output_dir=_stage_dir(base, "recorded_data_strategy_replay_sandbox"),
        decision_audit_output_dir=_stage_dir(base, "recorded_data_strategy_decision_audit"),
        decision_acceptance_output_dir=_stage_dir(base, "recorded_data_strategy_decision_acceptance"),
        trade_plan_output_dir=_stage_dir(base, "recorded_data_paper_option_trade_plan_simulator"),
        fill_exit_output_dir=_stage_dir(base, "recorded_data_paper_fill_exit_simulator"),
        trade_ledger_output_dir=_stage_dir(base, "recorded_data_backtest_trade_ledger"),
        metrics_output_dir=_stage_dir(base, "recorded_data_backtest_metrics_engine"),
        report_writer_output_dir=_stage_dir(base, "recorded_data_backtest_report_writer"),
        min_bars=args.min_bars,
        min_decisions=args.min_decisions,
        min_non_neutral_decisions=args.min_non_neutral_decisions,
        min_plans=args.min_plans,
        min_lifecycles=args.min_lifecycles,
        min_trades=args.min_trades,
        min_stage_count=args.min_stage_count,
        min_passed_stage_count=args.min_passed_stage_count,
        threshold_points=args.threshold_points,
        starting_equity_reference=args.starting_equity_reference,
        allow_warnings=args.allow_warnings,
        max_bars=args.max_bars,
        require_final_outputs_exist=not args.skip_final_output_existence_check,
    )

    print("HQE recorded data backtest readiness gate completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future v1.0 testing release gate: {report.ready_for_future_v1_testing_release_gate}")
    print(f"Backtest readiness report: {outputs['backtest_readiness_gate_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
