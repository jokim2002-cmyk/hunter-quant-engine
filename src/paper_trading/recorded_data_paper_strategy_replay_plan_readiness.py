"""
Recorded data paper strategy replay plan readiness gate.

One-command evidence-only readiness gate for future paper/simulation strategy
replay planning:
1. Build the no-execution paper strategy replay plan.
2. Run the replay-plan acceptance gate.
3. Write a final plan readiness report.

This module never runs strategies, creates signals, creates trade plans,
connects to brokers, requests live market data, places orders, uses real money,
calculates PnL, or proves profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from src.paper_trading.recorded_data_paper_strategy_replay_plan import (
    build_and_write_paper_strategy_replay_plan_report,
)
from src.paper_trading.recorded_data_paper_strategy_replay_plan_acceptance import (
    build_and_write_replay_plan_acceptance_report,
)


@dataclass(frozen=True)
class PaperStrategyReplayPlanReadinessStageResult:
    stage: str
    status: str
    output_directory: str
    output_files: dict[str, str]
    accepted: bool
    summary: dict[str, int | str | bool | None]


@dataclass(frozen=True)
class PaperStrategyReplayPlanReadinessReport:
    generated_at_utc: str
    status: str
    ready_for_future_paper_strategy_replay_plan: bool
    output_directory: str
    min_scenarios_required: int
    min_bars_required: int
    min_scenario_plans_required: int
    min_total_planned_bars_required: int
    allow_warnings: bool
    safety_notice: str
    stage_results: list[PaperStrategyReplayPlanReadinessStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data paper strategy replay "
        "plan readiness gate does not run strategies, create signals, create "
        "trade plans, connect to brokers, request live market data, place real "
        "orders, use real money, calculate PnL, or prove profitability."
    )


def _stringify_outputs(outputs: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in outputs.items()}


def _overall_status(
    *,
    plan_status: str,
    plan_ready: bool,
    acceptance_status: str,
    acceptance_accepted: bool,
) -> str:
    if not plan_ready or not acceptance_accepted:
        return "fail"
    if plan_status == "warn" or acceptance_status == "warn":
        return "warn"
    if plan_status == "pass" and acceptance_status == "pass":
        return "pass"
    return "fail"


def build_paper_strategy_replay_plan_readiness_report(
    *,
    scenario_readiness_path: Path,
    scenario_manifest_path: Path,
    strategy_input_bars_path: Path,
    plan_output_dir: Path,
    plan_acceptance_output_dir: Path,
    plan_readiness_output_dir: Path,
    min_scenarios: int = 1,
    min_bars: int = 1,
    min_scenario_plans: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> PaperStrategyReplayPlanReadinessReport:
    """Run replay plan build plus acceptance and return final readiness."""

    plan_report, plan_outputs = build_and_write_paper_strategy_replay_plan_report(
        scenario_readiness_path=scenario_readiness_path,
        scenario_manifest_path=scenario_manifest_path,
        strategy_input_bars_path=strategy_input_bars_path,
        output_dir=plan_output_dir,
        min_scenarios=min_scenarios,
        min_bars=min_bars,
        allow_warnings=allow_warnings,
    )

    plan_stage = PaperStrategyReplayPlanReadinessStageResult(
        stage="recorded_data_paper_strategy_replay_plan",
        status=plan_report.status,
        output_directory=str(plan_output_dir),
        output_files=_stringify_outputs(plan_outputs),
        accepted=plan_report.ready_to_plan,
        summary={
            "ready_to_plan": plan_report.ready_to_plan,
            "min_scenarios_required": plan_report.min_scenarios_required,
            "min_bars_required": plan_report.min_bars_required,
            "scenario_count": plan_report.scenario_count,
            "total_planned_bars": plan_report.total_planned_bars,
            "issue_count": len(plan_report.issues),
            "message": "No-execution paper strategy replay plan completed.",
        },
    )

    acceptance_report, acceptance_outputs = build_and_write_replay_plan_acceptance_report(
        replay_plan_path=plan_outputs["paper_strategy_replay_plan_json"],
        output_dir=plan_acceptance_output_dir,
        min_scenario_plans=min_scenario_plans,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )

    acceptance_stage = PaperStrategyReplayPlanReadinessStageResult(
        stage="recorded_data_paper_strategy_replay_plan_acceptance",
        status=acceptance_report.status,
        output_directory=str(plan_acceptance_output_dir),
        output_files=_stringify_outputs(acceptance_outputs),
        accepted=acceptance_report.accepted,
        summary={
            "accepted": acceptance_report.accepted,
            "allow_warnings": acceptance_report.allow_warnings,
            "min_scenario_plans_required": (
                acceptance_report.min_scenario_plans_required
            ),
            "min_total_planned_bars_required": (
                acceptance_report.min_total_planned_bars_required
            ),
            "plan_status": acceptance_report.plan_status,
            "ready_to_plan": acceptance_report.ready_to_plan,
            "scenario_count": acceptance_report.scenario_count,
            "total_planned_bars": acceptance_report.total_planned_bars,
            "issue_count": len(acceptance_report.issues),
            "message": "Paper strategy replay plan acceptance gate completed.",
        },
    )

    status = _overall_status(
        plan_status=plan_report.status,
        plan_ready=plan_report.ready_to_plan,
        acceptance_status=acceptance_report.status,
        acceptance_accepted=acceptance_report.accepted,
    )

    return PaperStrategyReplayPlanReadinessReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        ready_for_future_paper_strategy_replay_plan=status in {"pass", "warn"},
        output_directory=str(plan_readiness_output_dir),
        min_scenarios_required=max(min_scenarios, 0),
        min_bars_required=max(min_bars, 0),
        min_scenario_plans_required=max(min_scenario_plans, 0),
        min_total_planned_bars_required=max(min_total_planned_bars, 0),
        allow_warnings=allow_warnings,
        safety_notice=safety_notice(),
        stage_results=[plan_stage, acceptance_stage],
    )


def write_paper_strategy_replay_plan_readiness_report(
    report: PaperStrategyReplayPlanReadinessReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    readiness_json = output_dir / "paper_strategy_replay_plan_readiness.json"
    readiness_txt = output_dir / "paper_strategy_replay_plan_readiness.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["stage_results"] = [asdict(stage) for stage in report.stage_results]

    readiness_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Replay Plan Readiness Gate",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        (
            "Ready for future paper strategy replay plan: "
            f"{report.ready_for_future_paper_strategy_replay_plan}"
        ),
        f"Minimum scenarios required: {report.min_scenarios_required}",
        f"Minimum bars required: {report.min_bars_required}",
        f"Minimum scenario plans required: {report.min_scenario_plans_required}",
        f"Minimum total planned bars required: {report.min_total_planned_bars_required}",
        f"Allow warnings: {report.allow_warnings}",
        "",
        "Stages:",
    ]

    for stage in report.stage_results:
        lines.append(
            f"- {stage.stage}: status={stage.status}, "
            f"accepted={stage.accepted}, output={stage.output_directory}"
        )
        for key, value in stage.summary.items():
            lines.append(f"  - {key}: {value}")

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {readiness_json}",
            f"- {readiness_txt}",
            f"- {manifest_json}",
            "",
            "This gate only checks structural replay-plan readiness.",
            "This report is not a profitability claim.",
        ]
    )
    readiness_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_replay_plan_readiness",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_paper_strategy_replay_plan": (
            report.ready_for_future_paper_strategy_replay_plan
        ),
        "min_scenarios_required": report.min_scenarios_required,
        "min_bars_required": report.min_bars_required,
        "min_scenario_plans_required": report.min_scenario_plans_required,
        "min_total_planned_bars_required": report.min_total_planned_bars_required,
        "allow_warnings": report.allow_warnings,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_replay_plan_readiness_json": str(readiness_json),
            "paper_strategy_replay_plan_readiness_txt": str(readiness_txt),
            "manifest_json": str(manifest_json),
        },
        "stages": [asdict(stage) for stage in report.stage_results],
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_replay_plan_readiness_json": readiness_json,
        "paper_strategy_replay_plan_readiness_txt": readiness_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_strategy_replay_plan_readiness_report(
    *,
    scenario_readiness_path: Path,
    scenario_manifest_path: Path,
    strategy_input_bars_path: Path,
    plan_output_dir: Path,
    plan_acceptance_output_dir: Path,
    plan_readiness_output_dir: Path,
    min_scenarios: int = 1,
    min_bars: int = 1,
    min_scenario_plans: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> tuple[PaperStrategyReplayPlanReadinessReport, dict[str, Path]]:
    report = build_paper_strategy_replay_plan_readiness_report(
        scenario_readiness_path=scenario_readiness_path,
        scenario_manifest_path=scenario_manifest_path,
        strategy_input_bars_path=strategy_input_bars_path,
        plan_output_dir=plan_output_dir,
        plan_acceptance_output_dir=plan_acceptance_output_dir,
        plan_readiness_output_dir=plan_readiness_output_dir,
        min_scenarios=min_scenarios,
        min_bars=min_bars,
        min_scenario_plans=min_scenario_plans,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_strategy_replay_plan_readiness_report(
        report,
        plan_readiness_output_dir,
    )
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run no-execution paper strategy replay plan readiness gate."
    )
    parser.add_argument(
        "--scenario-readiness",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_replay_scenario_readiness/"
            "scenario_readiness_report.json"
        ),
        help="Path to scenario readiness report JSON.",
    )
    parser.add_argument(
        "--scenario-manifest",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_replay_scenario/"
            "scenario_manifest.json"
        ),
        help="Path to scenario manifest JSON.",
    )
    parser.add_argument(
        "--strategy-input-bars",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_input_contract/"
            "strategy_input_bars.jsonl"
        ),
        help="Path to strategy input bars JSONL.",
    )
    parser.add_argument(
        "--plan-output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_replay_plan",
        help="Directory where replay plan reports are written.",
    )
    parser.add_argument(
        "--plan-acceptance-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_replay_plan_acceptance"
        ),
        help="Directory where replay plan acceptance reports are written.",
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_replay_plan_readiness"
        ),
        help="Directory where final plan readiness reports are written.",
    )
    parser.add_argument("--min-scenarios", type=int, default=1)
    parser.add_argument("--min-bars", type=int, default=1)
    parser.add_argument("--min-scenario-plans", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_paper_strategy_replay_plan_readiness_report(
        scenario_readiness_path=Path(args.scenario_readiness),
        scenario_manifest_path=Path(args.scenario_manifest),
        strategy_input_bars_path=Path(args.strategy_input_bars),
        plan_output_dir=Path(args.plan_output_dir),
        plan_acceptance_output_dir=Path(args.plan_acceptance_output_dir),
        plan_readiness_output_dir=Path(args.output_dir),
        min_scenarios=args.min_scenarios,
        min_bars=args.min_bars,
        min_scenario_plans=args.min_scenario_plans,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data paper strategy replay plan readiness completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Ready for future paper strategy replay plan: "
        f"{report.ready_for_future_paper_strategy_replay_plan}"
    )
    print(f"Plan readiness report: {outputs['paper_strategy_replay_plan_readiness_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
