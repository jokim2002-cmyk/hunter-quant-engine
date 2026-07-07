"""
Recorded data strategy replay preflight.

One-command evidence-only preflight for a future paper/simulation strategy replay:
1. Run recorded-data replay readiness.
2. Build the recorded-data strategy input contract.
3. Write a final preflight report.

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

from src.paper_trading.recorded_data_replay_readiness import (
    build_and_write_replay_readiness_report,
)
from src.paper_trading.recorded_data_strategy_input_contract import (
    build_and_write_strategy_input_contract_report,
)


@dataclass(frozen=True)
class StrategyReplayPreflightStageResult:
    """One stage result in the strategy replay preflight."""

    stage: str
    status: str
    output_directory: str
    output_files: dict[str, str]
    accepted: bool
    summary: dict[str, int | str | bool | None]


@dataclass(frozen=True)
class StrategyReplayPreflightReport:
    """Final strategy replay preflight report."""

    generated_at_utc: str
    status: str
    ready_for_future_paper_strategy_replay: bool
    output_directory: str
    min_events_required: int
    min_bars_required: int
    allow_warnings: bool
    safety_notice: str
    stage_results: list[StrategyReplayPreflightStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data strategy replay "
        "preflight does not run strategies, create signals, create trade plans, "
        "connect to brokers, request live market data, place real orders, use "
        "real money, or prove profitability."
    )


def _stringify_outputs(outputs: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in outputs.items()}


def _stage_is_accepted(status: str, allow_warnings: bool) -> bool:
    if status == "pass":
        return True
    if status == "warn" and allow_warnings:
        return True
    return False


def _preflight_status(
    readiness_status: str,
    readiness_ready: bool,
    contract_status: str,
    contract_ready: bool,
) -> str:
    if not readiness_ready or not contract_ready:
        return "fail"
    if readiness_status == "warn" or contract_status == "warn":
        return "warn"
    if readiness_status == "pass" and contract_status == "pass":
        return "pass"
    return "fail"


def build_strategy_replay_preflight_report(
    *,
    inventory_path: Path,
    recorded_roots: Sequence[Path],
    base_output_dir: Path,
    evidence_output_dir: Path,
    acceptance_output_dir: Path,
    readiness_output_dir: Path,
    contract_output_dir: Path,
    preflight_output_dir: Path,
    min_events: int = 1,
    min_bars: int = 1,
    allow_warnings: bool = False,
    max_records: int | None = None,
    max_events: int | None = None,
) -> StrategyReplayPreflightReport:
    """Run replay readiness and strategy input contract checks."""

    readiness_report, readiness_outputs = build_and_write_replay_readiness_report(
        inventory_path=inventory_path,
        recorded_roots=recorded_roots,
        base_output_dir=base_output_dir,
        evidence_output_dir=evidence_output_dir,
        acceptance_output_dir=acceptance_output_dir,
        readiness_output_dir=readiness_output_dir,
        min_events=min_events,
        allow_warnings=allow_warnings,
        max_records=max_records,
    )

    readiness_stage = StrategyReplayPreflightStageResult(
        stage="recorded_data_replay_readiness",
        status=readiness_report.status,
        output_directory=str(readiness_output_dir),
        output_files=_stringify_outputs(readiness_outputs),
        accepted=readiness_report.ready_for_future_paper_replay,
        summary={
            "ready_for_future_paper_replay": readiness_report.ready_for_future_paper_replay,
            "min_events_required": readiness_report.min_events_required,
            "allow_warnings": readiness_report.allow_warnings,
            "stage_count": len(readiness_report.stage_results),
            "message": "Recorded-data replay readiness gate completed.",
        },
    )

    dry_run_events_path = (
        base_output_dir / "recorded_data_replay_dry_run" / "dry_run_events.jsonl"
    )
    contract_report, contract_outputs = build_and_write_strategy_input_contract_report(
        dry_run_events_path=dry_run_events_path,
        output_dir=contract_output_dir,
        min_bars=min_bars,
        max_events=max_events,
    )

    contract_ready = _stage_is_accepted(contract_report.status, allow_warnings)
    contract_stage = StrategyReplayPreflightStageResult(
        stage="recorded_data_strategy_input_contract",
        status=contract_report.status,
        output_directory=str(contract_output_dir),
        output_files=_stringify_outputs(contract_outputs),
        accepted=contract_ready,
        summary={
            "min_bars_required": contract_report.min_bars_required,
            "input_event_count": contract_report.input_event_count,
            "accepted_bar_count": contract_report.accepted_bar_count,
            "issue_count": len(contract_report.issues),
            "first_timestamp": contract_report.first_timestamp,
            "last_timestamp": contract_report.last_timestamp,
            "message": "Recorded-data strategy input contract completed.",
        },
    )

    status = _preflight_status(
        readiness_report.status,
        readiness_report.ready_for_future_paper_replay,
        contract_report.status,
        contract_ready,
    )

    return StrategyReplayPreflightReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        ready_for_future_paper_strategy_replay=status in {"pass", "warn"},
        output_directory=str(preflight_output_dir),
        min_events_required=max(min_events, 0),
        min_bars_required=max(min_bars, 0),
        allow_warnings=allow_warnings,
        safety_notice=safety_notice(),
        stage_results=[readiness_stage, contract_stage],
    )


def write_strategy_replay_preflight_report(
    report: StrategyReplayPreflightReport,
    output_dir: Path,
) -> dict[str, Path]:
    """Write final strategy replay preflight outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)

    preflight_json = output_dir / "preflight_report.json"
    preflight_txt = output_dir / "preflight_report.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["stage_results"] = [asdict(stage) for stage in report.stage_results]

    preflight_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Strategy Replay Preflight",
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
            f"- {preflight_json}",
            f"- {preflight_txt}",
            f"- {manifest_json}",
            "",
            "This preflight only checks structural readiness for a future paper strategy replay.",
            "This report is not a profitability claim.",
        ]
    )
    preflight_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_strategy_replay_preflight",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        (
            "ready_for_future_paper_strategy_replay"
        ): report.ready_for_future_paper_strategy_replay,
        "min_events_required": report.min_events_required,
        "min_bars_required": report.min_bars_required,
        "allow_warnings": report.allow_warnings,
        "safety_notice": report.safety_notice,
        "outputs": {
            "preflight_report_json": str(preflight_json),
            "preflight_report_txt": str(preflight_txt),
            "manifest_json": str(manifest_json),
        },
        "stages": [asdict(stage) for stage in report.stage_results],
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "preflight_report_json": preflight_json,
        "preflight_report_txt": preflight_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_replay_preflight_report(
    *,
    inventory_path: Path,
    recorded_roots: Sequence[Path],
    base_output_dir: Path,
    evidence_output_dir: Path,
    acceptance_output_dir: Path,
    readiness_output_dir: Path,
    contract_output_dir: Path,
    preflight_output_dir: Path,
    min_events: int = 1,
    min_bars: int = 1,
    allow_warnings: bool = False,
    max_records: int | None = None,
    max_events: int | None = None,
) -> tuple[StrategyReplayPreflightReport, dict[str, Path]]:
    report = build_strategy_replay_preflight_report(
        inventory_path=inventory_path,
        recorded_roots=recorded_roots,
        base_output_dir=base_output_dir,
        evidence_output_dir=evidence_output_dir,
        acceptance_output_dir=acceptance_output_dir,
        readiness_output_dir=readiness_output_dir,
        contract_output_dir=contract_output_dir,
        preflight_output_dir=preflight_output_dir,
        min_events=min_events,
        min_bars=min_bars,
        allow_warnings=allow_warnings,
        max_records=max_records,
        max_events=max_events,
    )
    outputs = write_strategy_replay_preflight_report(report, preflight_output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run paper-only recorded-data strategy replay preflight."
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
        "--acceptance-output-dir",
        default="reports/paper_trading/recorded_data_replay_acceptance",
        help="Directory where replay acceptance reports are written.",
    )
    parser.add_argument(
        "--readiness-output-dir",
        default="reports/paper_trading/recorded_data_replay_readiness",
        help="Directory where replay readiness reports are written.",
    )
    parser.add_argument(
        "--contract-output-dir",
        default="reports/paper_trading/recorded_data_strategy_input_contract",
        help="Directory where strategy input contract reports are written.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_strategy_replay_preflight",
        help="Directory where final preflight reports are written.",
    )
    parser.add_argument(
        "--min-events",
        type=int,
        default=1,
        help="Minimum replay dry-run events required by readiness.",
    )
    parser.add_argument(
        "--min-bars",
        type=int,
        default=1,
        help="Minimum accepted strategy input bars required by the contract.",
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    recorded_roots = (
        [Path(value) for value in args.recorded_root]
        if args.recorded_root
        else [Path("data/recorded"), Path("data/live_recording")]
    )

    report, outputs = build_and_write_strategy_replay_preflight_report(
        inventory_path=Path(args.inventory),
        recorded_roots=recorded_roots,
        base_output_dir=Path(args.base_output_dir),
        evidence_output_dir=Path(args.evidence_output_dir),
        acceptance_output_dir=Path(args.acceptance_output_dir),
        readiness_output_dir=Path(args.readiness_output_dir),
        contract_output_dir=Path(args.contract_output_dir),
        preflight_output_dir=Path(args.output_dir),
        min_events=args.min_events,
        min_bars=args.min_bars,
        allow_warnings=args.allow_warnings,
        max_records=args.max_records,
        max_events=args.max_events,
    )

    print("HQE recorded data strategy replay preflight completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Ready for future paper strategy replay: "
        f"{report.ready_for_future_paper_strategy_replay}"
    )
    print(f"Preflight report: {outputs['preflight_report_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
