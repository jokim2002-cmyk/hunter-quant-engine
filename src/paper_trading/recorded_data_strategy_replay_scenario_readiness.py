"""
Recorded data strategy replay scenario readiness gate.

One-command evidence-only readiness gate for future recorded-data paper strategy
replay scenarios:
1. Run recorded-data strategy replay preflight.
2. Build recorded-data strategy replay scenario manifest.
3. Run scenario acceptance gate.
4. Write final scenario readiness report.

This module never runs strategies, creates signals, creates trade plans,
connects to brokers, requests live market data, places orders, uses real money,
or proves profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from src.paper_trading.recorded_data_strategy_replay_preflight import (
    build_and_write_strategy_replay_preflight_report,
)
from src.paper_trading.recorded_data_strategy_replay_scenario import (
    build_and_write_strategy_replay_scenario_report,
)
from src.paper_trading.recorded_data_strategy_replay_scenario_acceptance import (
    build_and_write_scenario_acceptance_report,
)


@dataclass(frozen=True)
class StrategyReplayScenarioReadinessStageResult:
    """One stage result in the final scenario readiness gate."""

    stage: str
    status: str
    output_directory: str
    output_files: dict[str, str]
    accepted: bool
    summary: dict[str, int | str | bool | None]


@dataclass(frozen=True)
class StrategyReplayScenarioReadinessReport:
    """Final scenario readiness report."""

    generated_at_utc: str
    status: str
    ready_for_future_paper_strategy_replay: bool
    output_directory: str
    min_events_required: int
    min_bars_required: int
    min_scenarios_required: int
    min_bars_per_scenario: int
    allow_warnings: bool
    safety_notice: str
    stage_results: list[StrategyReplayScenarioReadinessStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data strategy replay "
        "scenario readiness gate does not run strategies, create signals, create "
        "trade plans, connect to brokers, request live market data, place real "
        "orders, use real money, or prove profitability."
    )


def _stringify_outputs(outputs: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in outputs.items()}


def _accepted_from_status(status: str, allow_warnings: bool) -> bool:
    if status == "pass":
        return True
    if status == "warn" and allow_warnings:
        return True
    return False


def _overall_status(
    preflight_status: str,
    preflight_ready: bool,
    scenario_status: str,
    scenario_accepted: bool,
    acceptance_status: str,
    acceptance_accepted: bool,
) -> str:
    if not preflight_ready or not scenario_accepted or not acceptance_accepted:
        return "fail"
    if "warn" in {preflight_status, scenario_status, acceptance_status}:
        return "warn"
    if {preflight_status, scenario_status, acceptance_status} == {"pass"}:
        return "pass"
    return "fail"


def build_strategy_replay_scenario_readiness_report(
    *,
    inventory_path: Path,
    recorded_roots: Sequence[Path],
    base_output_dir: Path,
    evidence_output_dir: Path,
    replay_acceptance_output_dir: Path,
    replay_readiness_output_dir: Path,
    contract_output_dir: Path,
    preflight_output_dir: Path,
    scenario_output_dir: Path,
    scenario_acceptance_output_dir: Path,
    scenario_readiness_output_dir: Path,
    min_events: int = 1,
    min_bars: int = 1,
    min_scenarios: int = 1,
    min_bars_per_scenario: int = 1,
    allow_warnings: bool = False,
    max_records: int | None = None,
    max_events: int | None = None,
    max_scenarios: int | None = None,
) -> StrategyReplayScenarioReadinessReport:
    """Run preflight, scenario manifest, and scenario acceptance."""

    preflight_report, preflight_outputs = build_and_write_strategy_replay_preflight_report(
        inventory_path=inventory_path,
        recorded_roots=recorded_roots,
        base_output_dir=base_output_dir,
        evidence_output_dir=evidence_output_dir,
        acceptance_output_dir=replay_acceptance_output_dir,
        readiness_output_dir=replay_readiness_output_dir,
        contract_output_dir=contract_output_dir,
        preflight_output_dir=preflight_output_dir,
        min_events=min_events,
        min_bars=min_bars,
        allow_warnings=allow_warnings,
        max_records=max_records,
        max_events=max_events,
    )

    preflight_stage = StrategyReplayScenarioReadinessStageResult(
        stage="recorded_data_strategy_replay_preflight",
        status=preflight_report.status,
        output_directory=str(preflight_output_dir),
        output_files=_stringify_outputs(preflight_outputs),
        accepted=preflight_report.ready_for_future_paper_strategy_replay,
        summary={
            "ready_for_future_paper_strategy_replay": (
                preflight_report.ready_for_future_paper_strategy_replay
            ),
            "min_events_required": preflight_report.min_events_required,
            "min_bars_required": preflight_report.min_bars_required,
            "allow_warnings": preflight_report.allow_warnings,
            "stage_count": len(preflight_report.stage_results),
            "message": "Recorded-data strategy replay preflight completed.",
        },
    )

    strategy_input_bars_path = contract_output_dir / "strategy_input_bars.jsonl"
    preflight_report_path = preflight_output_dir / "preflight_report.json"

    scenario_report, scenario_outputs = build_and_write_strategy_replay_scenario_report(
        strategy_input_bars_path=strategy_input_bars_path,
        preflight_report_path=preflight_report_path,
        output_dir=scenario_output_dir,
        min_bars_per_scenario=min_bars_per_scenario,
        max_scenarios=max_scenarios,
    )

    scenario_accepted = _accepted_from_status(scenario_report.status, allow_warnings)
    scenario_stage = StrategyReplayScenarioReadinessStageResult(
        stage="recorded_data_strategy_replay_scenario",
        status=scenario_report.status,
        output_directory=str(scenario_output_dir),
        output_files=_stringify_outputs(scenario_outputs),
        accepted=scenario_accepted,
        summary={
            "min_bars_per_scenario": scenario_report.min_bars_per_scenario,
            "input_bar_count": scenario_report.input_bar_count,
            "scenario_count": scenario_report.scenario_count,
            "issue_count": len(scenario_report.issues),
            "message": "Recorded-data strategy replay scenario manifest completed.",
        },
    )

    acceptance_report, acceptance_outputs = build_and_write_scenario_acceptance_report(
        scenario_manifest_path=scenario_outputs["scenario_manifest_json"],
        output_dir=scenario_acceptance_output_dir,
        min_scenarios=min_scenarios,
        min_bars_per_scenario=min_bars_per_scenario,
        allow_warnings=allow_warnings,
    )

    acceptance_stage = StrategyReplayScenarioReadinessStageResult(
        stage="recorded_data_strategy_replay_scenario_acceptance",
        status=acceptance_report.status,
        output_directory=str(scenario_acceptance_output_dir),
        output_files=_stringify_outputs(acceptance_outputs),
        accepted=acceptance_report.accepted,
        summary={
            "accepted": acceptance_report.accepted,
            "min_scenarios_required": acceptance_report.min_scenarios_required,
            "min_bars_per_scenario": acceptance_report.min_bars_per_scenario,
            "allow_warnings": acceptance_report.allow_warnings,
            "manifest_status": acceptance_report.manifest_status,
            "scenario_count": acceptance_report.scenario_count,
            "total_bar_count": acceptance_report.total_bar_count,
            "issue_count": len(acceptance_report.issues),
            "message": "Recorded-data strategy replay scenario acceptance completed.",
        },
    )

    status = _overall_status(
        preflight_report.status,
        preflight_report.ready_for_future_paper_strategy_replay,
        scenario_report.status,
        scenario_accepted,
        acceptance_report.status,
        acceptance_report.accepted,
    )

    return StrategyReplayScenarioReadinessReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        ready_for_future_paper_strategy_replay=status in {"pass", "warn"},
        output_directory=str(scenario_readiness_output_dir),
        min_events_required=max(min_events, 0),
        min_bars_required=max(min_bars, 0),
        min_scenarios_required=max(min_scenarios, 0),
        min_bars_per_scenario=max(min_bars_per_scenario, 0),
        allow_warnings=allow_warnings,
        safety_notice=safety_notice(),
        stage_results=[preflight_stage, scenario_stage, acceptance_stage],
    )


def write_strategy_replay_scenario_readiness_report(
    report: StrategyReplayScenarioReadinessReport,
    output_dir: Path,
) -> dict[str, Path]:
    """Write final scenario readiness report outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)

    readiness_json = output_dir / "scenario_readiness_report.json"
    readiness_txt = output_dir / "scenario_readiness_report.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["stage_results"] = [asdict(stage) for stage in report.stage_results]

    readiness_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Strategy Replay Scenario Readiness Gate",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        (
            "Ready for future paper strategy replay: "
            f"{report.ready_for_future_paper_strategy_replay}"
        ),
        f"Minimum replay events required: {report.min_events_required}",
        f"Minimum strategy input bars required: {report.min_bars_required}",
        f"Minimum scenarios required: {report.min_scenarios_required}",
        f"Minimum bars per scenario: {report.min_bars_per_scenario}",
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
            "This gate only checks structural scenario readiness for a future paper strategy replay.",
            "This report is not a profitability claim.",
        ]
    )
    readiness_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_strategy_replay_scenario_readiness",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_paper_strategy_replay": (
            report.ready_for_future_paper_strategy_replay
        ),
        "min_events_required": report.min_events_required,
        "min_bars_required": report.min_bars_required,
        "min_scenarios_required": report.min_scenarios_required,
        "min_bars_per_scenario": report.min_bars_per_scenario,
        "allow_warnings": report.allow_warnings,
        "safety_notice": report.safety_notice,
        "outputs": {
            "scenario_readiness_report_json": str(readiness_json),
            "scenario_readiness_report_txt": str(readiness_txt),
            "manifest_json": str(manifest_json),
        },
        "stages": [asdict(stage) for stage in report.stage_results],
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "scenario_readiness_report_json": readiness_json,
        "scenario_readiness_report_txt": readiness_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_replay_scenario_readiness_report(
    *,
    inventory_path: Path,
    recorded_roots: Sequence[Path],
    base_output_dir: Path,
    evidence_output_dir: Path,
    replay_acceptance_output_dir: Path,
    replay_readiness_output_dir: Path,
    contract_output_dir: Path,
    preflight_output_dir: Path,
    scenario_output_dir: Path,
    scenario_acceptance_output_dir: Path,
    scenario_readiness_output_dir: Path,
    min_events: int = 1,
    min_bars: int = 1,
    min_scenarios: int = 1,
    min_bars_per_scenario: int = 1,
    allow_warnings: bool = False,
    max_records: int | None = None,
    max_events: int | None = None,
    max_scenarios: int | None = None,
) -> tuple[StrategyReplayScenarioReadinessReport, dict[str, Path]]:
    report = build_strategy_replay_scenario_readiness_report(
        inventory_path=inventory_path,
        recorded_roots=recorded_roots,
        base_output_dir=base_output_dir,
        evidence_output_dir=evidence_output_dir,
        replay_acceptance_output_dir=replay_acceptance_output_dir,
        replay_readiness_output_dir=replay_readiness_output_dir,
        contract_output_dir=contract_output_dir,
        preflight_output_dir=preflight_output_dir,
        scenario_output_dir=scenario_output_dir,
        scenario_acceptance_output_dir=scenario_acceptance_output_dir,
        scenario_readiness_output_dir=scenario_readiness_output_dir,
        min_events=min_events,
        min_bars=min_bars,
        min_scenarios=min_scenarios,
        min_bars_per_scenario=min_bars_per_scenario,
        allow_warnings=allow_warnings,
        max_records=max_records,
        max_events=max_events,
        max_scenarios=max_scenarios,
    )
    outputs = write_strategy_replay_scenario_readiness_report(
        report,
        scenario_readiness_output_dir,
    )
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run paper-only recorded-data strategy replay scenario readiness gate."
    )
    parser.add_argument(
        "--inventory",
        default="reports/paper_trading/recorded_data_inventory/inventory.json",
        help="Path to recorded-data inventory JSON output.",
    )
    parser.add_argument(
        "--recorded-root",
        action="append",
        default=None,
        help="Recorded-data root to scan. Can be passed multiple times.",
    )
    parser.add_argument(
        "--base-output-dir",
        default="reports/paper_trading",
        help="Base directory where replay stage outputs are written.",
    )
    parser.add_argument(
        "--evidence-output-dir",
        default="reports/paper_trading/recorded_data_replay_evidence",
        help="Directory where evidence bundle reports are written.",
    )
    parser.add_argument(
        "--replay-acceptance-output-dir",
        default="reports/paper_trading/recorded_data_replay_acceptance",
        help="Directory where replay acceptance reports are written.",
    )
    parser.add_argument(
        "--replay-readiness-output-dir",
        default="reports/paper_trading/recorded_data_replay_readiness",
        help="Directory where replay readiness reports are written.",
    )
    parser.add_argument(
        "--contract-output-dir",
        default="reports/paper_trading/recorded_data_strategy_input_contract",
        help="Directory where strategy input contract reports are written.",
    )
    parser.add_argument(
        "--preflight-output-dir",
        default="reports/paper_trading/recorded_data_strategy_replay_preflight",
        help="Directory where strategy replay preflight reports are written.",
    )
    parser.add_argument(
        "--scenario-output-dir",
        default="reports/paper_trading/recorded_data_strategy_replay_scenario",
        help="Directory where scenario manifest reports are written.",
    )
    parser.add_argument(
        "--scenario-acceptance-output-dir",
        default="reports/paper_trading/recorded_data_strategy_replay_scenario_acceptance",
        help="Directory where scenario acceptance reports are written.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_strategy_replay_scenario_readiness",
        help="Directory where final scenario readiness reports are written.",
    )
    parser.add_argument(
        "--min-events",
        type=int,
        default=1,
        help="Minimum replay dry-run events required by preflight.",
    )
    parser.add_argument(
        "--min-bars",
        type=int,
        default=1,
        help="Minimum accepted strategy input bars required by preflight.",
    )
    parser.add_argument(
        "--min-scenarios",
        type=int,
        default=1,
        help="Minimum accepted scenarios required by scenario acceptance.",
    )
    parser.add_argument(
        "--min-bars-per-scenario",
        type=int,
        default=1,
        help="Minimum bars required in each accepted scenario.",
    )
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="Allow warn-status evidence to be considered ready with warning status.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Optional maximum replay records for the dry-run stage.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Optional maximum dry-run events for the strategy input contract.",
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=None,
        help="Optional maximum scenarios for the scenario manifest.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    recorded_roots = (
        [Path(value) for value in args.recorded_root]
        if args.recorded_root
        else [Path("data/recorded"), Path("data/live_recording")]
    )

    report, outputs = build_and_write_strategy_replay_scenario_readiness_report(
        inventory_path=Path(args.inventory),
        recorded_roots=recorded_roots,
        base_output_dir=Path(args.base_output_dir),
        evidence_output_dir=Path(args.evidence_output_dir),
        replay_acceptance_output_dir=Path(args.replay_acceptance_output_dir),
        replay_readiness_output_dir=Path(args.replay_readiness_output_dir),
        contract_output_dir=Path(args.contract_output_dir),
        preflight_output_dir=Path(args.preflight_output_dir),
        scenario_output_dir=Path(args.scenario_output_dir),
        scenario_acceptance_output_dir=Path(args.scenario_acceptance_output_dir),
        scenario_readiness_output_dir=Path(args.output_dir),
        min_events=args.min_events,
        min_bars=args.min_bars,
        min_scenarios=args.min_scenarios,
        min_bars_per_scenario=args.min_bars_per_scenario,
        allow_warnings=args.allow_warnings,
        max_records=args.max_records,
        max_events=args.max_events,
        max_scenarios=args.max_scenarios,
    )

    print("HQE recorded data strategy replay scenario readiness gate completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Ready for future paper strategy replay: "
        f"{report.ready_for_future_paper_strategy_replay}"
    )
    print(f"Scenario readiness report: {outputs['scenario_readiness_report_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
