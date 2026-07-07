"""
Recorded data one-command backtest runner.

Module CCC in the fast-track v1.0 Testing Edition path.

This module orchestrates the paper-only backtest chain:
sandbox -> decision audit -> decision acceptance -> CE/PE paper plans ->
fill/exit simulator -> trade ledger -> metrics engine -> report writer.

This module does not connect to brokers, request live market data, place real
orders, use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from src.paper_trading.recorded_data_backtest_metrics_engine import (
    build_and_write_backtest_metrics_report,
)
from src.paper_trading.recorded_data_backtest_report_writer import (
    build_and_write_backtest_report_writer_report,
)
from src.paper_trading.recorded_data_backtest_trade_ledger import (
    build_and_write_backtest_trade_ledger_report,
)
from src.paper_trading.recorded_data_paper_fill_exit_simulator import (
    build_and_write_paper_fill_exit_report,
)
from src.paper_trading.recorded_data_paper_option_trade_plan_simulator import (
    build_and_write_paper_option_trade_plan_report,
)
from src.paper_trading.recorded_data_strategy_decision_acceptance import (
    build_and_write_strategy_decision_acceptance_report,
)
from src.paper_trading.recorded_data_strategy_decision_audit import (
    build_and_write_strategy_decision_audit_report,
)
from src.paper_trading.recorded_data_strategy_replay_sandbox import (
    build_and_write_strategy_replay_sandbox_report,
)


@dataclass(frozen=True)
class OneCommandBacktestStageResult:
    stage_name: str
    status: str
    ready: bool
    output_directory: str
    primary_output: str
    detail: str


@dataclass(frozen=True)
class OneCommandBacktestIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class OneCommandBacktestRunnerReport:
    generated_at_utc: str
    consumer_evidence_readiness_path: str
    strategy_input_bars_path: str
    output_directory: str
    status: str
    ready_for_future_backtest_acceptance_gate: bool
    min_trades_required: int
    safety_notice: str
    stage_count: int
    passed_stage_count: int
    warning_stage_count: int
    failed_stage_count: int
    final_backtest_report_path: str
    final_metrics_path: str
    final_trade_ledger_path: str
    issues: list[OneCommandBacktestIssue]
    stages: list[OneCommandBacktestStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation one-command backtest runner only. The chain uses "
        "recorded replay data and paper-only CE/PE option-buy simulation. It "
        "does not connect to brokers, request live market data, place real "
        "orders, use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> OneCommandBacktestIssue:
    return OneCommandBacktestIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _stage_result(
    *,
    stage_name: str,
    report: Any,
    output_dir: Path,
    primary_output: Path,
    ready_attr: str,
) -> OneCommandBacktestStageResult:
    status = str(getattr(report, "status", "unknown"))
    ready = bool(getattr(report, ready_attr, False))
    return OneCommandBacktestStageResult(
        stage_name=stage_name,
        status=status,
        ready=ready,
        output_directory=str(output_dir),
        primary_output=str(primary_output),
        detail=f"{stage_name} status={status}, ready={ready}",
    )


def _status_from_stages(
    stages: Sequence[OneCommandBacktestStageResult],
    issues: Sequence[OneCommandBacktestIssue],
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


def _write_report(
    report: OneCommandBacktestRunnerReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    runner_json = output_dir / "one_command_backtest_runner.json"
    runner_txt = output_dir / "one_command_backtest_runner.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["stages"] = [asdict(stage) for stage in report.stages]

    runner_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data One-Command Backtest Runner",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future backtest acceptance gate: {report.ready_for_future_backtest_acceptance_gate}",
        f"Stages: {report.stage_count}",
        f"Passed stages: {report.passed_stage_count}",
        f"Warning stages: {report.warning_stage_count}",
        f"Failed stages: {report.failed_stage_count}",
        "",
        "Final outputs:",
        f"- Backtest report: {report.final_backtest_report_path}",
        f"- Metrics: {report.final_metrics_path}",
        f"- Trade ledger: {report.final_trade_ledger_path}",
        "",
        "Stage results:",
    ]

    for stage in report.stages:
        lines.append(
            f"- {stage.stage_name}: status={stage.status}, ready={stage.ready}, output={stage.primary_output}"
        )

    lines.extend(
        [
            "",
            "Issues:",
        ]
    )

    if not report.issues:
        lines.append("- PASS: One-command backtest runner completed the paper-only chain.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
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
            "- No real money.",
            "- This report is not a profitability claim.",
            "",
            "Outputs:",
            f"- {runner_json}",
            f"- {runner_txt}",
            f"- {manifest_json}",
        ]
    )
    runner_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_one_command_backtest_runner",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_backtest_acceptance_gate": report.ready_for_future_backtest_acceptance_gate,
        "stage_count": report.stage_count,
        "passed_stage_count": report.passed_stage_count,
        "warning_stage_count": report.warning_stage_count,
        "failed_stage_count": report.failed_stage_count,
        "final_backtest_report_path": report.final_backtest_report_path,
        "final_metrics_path": report.final_metrics_path,
        "final_trade_ledger_path": report.final_trade_ledger_path,
        "safety_notice": report.safety_notice,
        "outputs": {
            "one_command_backtest_runner_json": str(runner_json),
            "one_command_backtest_runner_txt": str(runner_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "one_command_backtest_runner_json": runner_json,
        "one_command_backtest_runner_txt": runner_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_one_command_backtest_runner_report(
    *,
    consumer_evidence_readiness_path: Path,
    strategy_input_bars_path: Path,
    output_dir: Path,
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
    threshold_points: float = 0.0,
    starting_equity_reference: float = 100000.0,
    allow_warnings: bool = False,
    max_bars: int | None = None,
) -> tuple[OneCommandBacktestRunnerReport, dict[str, Path]]:
    issues: list[OneCommandBacktestIssue] = []
    stages: list[OneCommandBacktestStageResult] = []

    try:
        sandbox_report, sandbox_outputs = build_and_write_strategy_replay_sandbox_report(
            consumer_evidence_readiness_path=consumer_evidence_readiness_path,
            strategy_input_bars_path=strategy_input_bars_path,
            output_dir=sandbox_output_dir,
            min_bars=min_bars,
            allow_warnings=allow_warnings,
            max_bars=max_bars,
        )
        stages.append(
            _stage_result(
                stage_name="strategy_replay_sandbox",
                report=sandbox_report,
                output_dir=sandbox_output_dir,
                primary_output=sandbox_outputs["strategy_replay_sandbox_json"],
                ready_attr="ready_for_future_strategy_decision_audit",
            )
        )

        decision_report, decision_outputs = build_and_write_strategy_decision_audit_report(
            sandbox_report_path=sandbox_outputs["strategy_replay_sandbox_json"],
            output_dir=decision_audit_output_dir,
            min_decisions=min_decisions,
            threshold_points=threshold_points,
            allow_warnings=allow_warnings,
            max_events=max_bars,
        )
        stages.append(
            _stage_result(
                stage_name="strategy_decision_audit",
                report=decision_report,
                output_dir=decision_audit_output_dir,
                primary_output=decision_outputs["strategy_decision_audit_json"],
                ready_attr="ready_for_future_paper_trade_plan_simulator",
            )
        )

        acceptance_report, acceptance_outputs = build_and_write_strategy_decision_acceptance_report(
            decision_audit_path=decision_outputs["strategy_decision_audit_json"],
            output_dir=decision_acceptance_output_dir,
            min_decisions=min_decisions,
            min_non_neutral_decisions=min_non_neutral_decisions,
            allow_warnings=allow_warnings,
        )
        stages.append(
            _stage_result(
                stage_name="strategy_decision_acceptance",
                report=acceptance_report,
                output_dir=decision_acceptance_output_dir,
                primary_output=acceptance_outputs["strategy_decision_acceptance_json"],
                ready_attr="accepted_for_future_paper_trade_plan_simulator",
            )
        )

        trade_plan_report, trade_plan_outputs = build_and_write_paper_option_trade_plan_report(
            decision_acceptance_path=acceptance_outputs["strategy_decision_acceptance_json"],
            decision_audit_path=decision_outputs["strategy_decision_audit_json"],
            output_dir=trade_plan_output_dir,
            min_plans=min_plans,
            allow_warnings=allow_warnings,
        )
        stages.append(
            _stage_result(
                stage_name="paper_option_trade_plan_simulator",
                report=trade_plan_report,
                output_dir=trade_plan_output_dir,
                primary_output=trade_plan_outputs["paper_option_trade_plan_simulator_json"],
                ready_attr="ready_for_future_paper_fill_simulator",
            )
        )

        fill_exit_report, fill_exit_outputs = build_and_write_paper_fill_exit_report(
            trade_plan_report_path=trade_plan_outputs["paper_option_trade_plan_simulator_json"],
            decision_audit_path=decision_outputs["strategy_decision_audit_json"],
            output_dir=fill_exit_output_dir,
            min_lifecycles=min_lifecycles,
            allow_warnings=allow_warnings,
        )
        stages.append(
            _stage_result(
                stage_name="paper_fill_exit_simulator",
                report=fill_exit_report,
                output_dir=fill_exit_output_dir,
                primary_output=fill_exit_outputs["paper_fill_exit_simulator_json"],
                ready_attr="ready_for_future_backtest_ledger",
            )
        )

        trade_ledger_report, trade_ledger_outputs = build_and_write_backtest_trade_ledger_report(
            fill_exit_report_path=fill_exit_outputs["paper_fill_exit_simulator_json"],
            output_dir=trade_ledger_output_dir,
            min_trades=min_trades,
            allow_warnings=allow_warnings,
        )
        stages.append(
            _stage_result(
                stage_name="backtest_trade_ledger",
                report=trade_ledger_report,
                output_dir=trade_ledger_output_dir,
                primary_output=trade_ledger_outputs["backtest_trade_ledger_json"],
                ready_attr="ready_for_future_backtest_metrics_engine",
            )
        )

        metrics_report, metrics_outputs = build_and_write_backtest_metrics_report(
            trade_ledger_path=trade_ledger_outputs["backtest_trade_ledger_json"],
            output_dir=metrics_output_dir,
            min_trades=min_trades,
            starting_equity_reference=starting_equity_reference,
            allow_warnings=allow_warnings,
        )
        stages.append(
            _stage_result(
                stage_name="backtest_metrics_engine",
                report=metrics_report,
                output_dir=metrics_output_dir,
                primary_output=metrics_outputs["backtest_metrics_json"],
                ready_attr="ready_for_future_backtest_report_writer",
            )
        )

        report_writer_report, report_writer_outputs = build_and_write_backtest_report_writer_report(
            metrics_path=metrics_outputs["backtest_metrics_json"],
            trade_ledger_path=trade_ledger_outputs["backtest_trade_ledger_json"],
            output_dir=report_writer_output_dir,
            min_trades=min_trades,
            allow_warnings=allow_warnings,
        )
        stages.append(
            _stage_result(
                stage_name="backtest_report_writer",
                report=report_writer_report,
                output_dir=report_writer_output_dir,
                primary_output=report_writer_outputs["backtest_report_json"],
                ready_attr="ready_for_future_one_command_backtest_runner",
            )
        )

        final_backtest_report_path = str(report_writer_outputs["backtest_report_txt"])
        final_metrics_path = str(metrics_outputs["backtest_metrics_json"])
        final_trade_ledger_path = str(trade_ledger_outputs["backtest_trade_ledger_json"])

    except Exception as exc:  # pragma: no cover - covered by behavior-level tests
        issues.append(
            _issue(
                "fail",
                "one_command_backtest_runner_exception",
                1,
                f"One-command backtest runner failed: {exc}",
            )
        )
        final_backtest_report_path = ""
        final_metrics_path = ""
        final_trade_ledger_path = ""

    status = _status_from_stages(stages, issues)

    passed_stage_count = sum(1 for stage in stages if stage.status == "pass")
    warning_stage_count = sum(1 for stage in stages if stage.status == "warn")
    failed_stage_count = sum(1 for stage in stages if stage.status == "fail")

    report = OneCommandBacktestRunnerReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        consumer_evidence_readiness_path=str(consumer_evidence_readiness_path),
        strategy_input_bars_path=str(strategy_input_bars_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_backtest_acceptance_gate=status in {"pass", "warn"} and len(stages) == 8,
        min_trades_required=max(min_trades, 0),
        safety_notice=safety_notice(),
        stage_count=len(stages),
        passed_stage_count=passed_stage_count,
        warning_stage_count=warning_stage_count,
        failed_stage_count=failed_stage_count,
        final_backtest_report_path=final_backtest_report_path,
        final_metrics_path=final_metrics_path,
        final_trade_ledger_path=final_trade_ledger_path,
        issues=issues,
        stages=stages,
    )
    outputs = _write_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the recorded-data paper backtest chain with one command."
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
        default="reports/paper_trading/recorded_data_one_command_backtest_runner",
    )
    parser.add_argument(
        "--base-stage-output-dir",
        default="reports/paper_trading",
    )
    parser.add_argument("--min-bars", type=int, default=1)
    parser.add_argument("--min-decisions", type=int, default=1)
    parser.add_argument("--min-non-neutral-decisions", type=int, default=0)
    parser.add_argument("--min-plans", type=int, default=1)
    parser.add_argument("--min-lifecycles", type=int, default=1)
    parser.add_argument("--min-trades", type=int, default=1)
    parser.add_argument("--threshold-points", type=float, default=0.0)
    parser.add_argument("--starting-equity-reference", type=float, default=100000.0)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-bars", type=int, default=None)
    return parser.parse_args(argv)


def _stage_dir(base: Path, name: str) -> Path:
    return base / name


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    base_stage_dir = Path(args.base_stage_output_dir)

    report, outputs = build_and_write_one_command_backtest_runner_report(
        consumer_evidence_readiness_path=Path(args.consumer_evidence_readiness),
        strategy_input_bars_path=Path(args.strategy_input_bars),
        output_dir=Path(args.output_dir),
        sandbox_output_dir=_stage_dir(base_stage_dir, "recorded_data_strategy_replay_sandbox"),
        decision_audit_output_dir=_stage_dir(base_stage_dir, "recorded_data_strategy_decision_audit"),
        decision_acceptance_output_dir=_stage_dir(base_stage_dir, "recorded_data_strategy_decision_acceptance"),
        trade_plan_output_dir=_stage_dir(base_stage_dir, "recorded_data_paper_option_trade_plan_simulator"),
        fill_exit_output_dir=_stage_dir(base_stage_dir, "recorded_data_paper_fill_exit_simulator"),
        trade_ledger_output_dir=_stage_dir(base_stage_dir, "recorded_data_backtest_trade_ledger"),
        metrics_output_dir=_stage_dir(base_stage_dir, "recorded_data_backtest_metrics_engine"),
        report_writer_output_dir=_stage_dir(base_stage_dir, "recorded_data_backtest_report_writer"),
        min_bars=args.min_bars,
        min_decisions=args.min_decisions,
        min_non_neutral_decisions=args.min_non_neutral_decisions,
        min_plans=args.min_plans,
        min_lifecycles=args.min_lifecycles,
        min_trades=args.min_trades,
        threshold_points=args.threshold_points,
        starting_equity_reference=args.starting_equity_reference,
        allow_warnings=args.allow_warnings,
        max_bars=args.max_bars,
    )

    print("HQE recorded data one-command backtest runner completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Stages: {report.passed_stage_count}/{report.stage_count} passed")
    print(f"Final backtest report: {report.final_backtest_report_path}")
    print(f"Runner report: {outputs['one_command_backtest_runner_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
