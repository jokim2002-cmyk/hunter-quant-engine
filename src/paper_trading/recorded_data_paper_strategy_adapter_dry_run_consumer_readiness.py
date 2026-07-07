"""
Recorded data paper strategy adapter dry-run consumer readiness gate.

One-command evidence-only readiness gate for the adapter dry-run consumer layer:
1. Consume adapter dry-run events in audit-only mode.
2. Run adapter dry-run consumer acceptance.
3. Write final consumer readiness report.

This module never executes strategy logic, creates signals, creates trade plans,
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

from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run_consumer import (
    build_and_write_adapter_dry_run_consumer_report,
)
from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance import (
    build_and_write_adapter_dry_run_consumer_acceptance_report,
)


@dataclass(frozen=True)
class AdapterDryRunConsumerReadinessStageResult:
    stage: str
    status: str
    output_directory: str
    output_files: dict[str, str]
    accepted: bool
    summary: dict[str, int | str | bool | None]


@dataclass(frozen=True)
class AdapterDryRunConsumerReadinessReport:
    generated_at_utc: str
    status: str
    ready_for_future_consumer_evidence_release: bool
    output_directory: str
    min_events_required: int
    min_total_planned_bars_required: int
    allow_warnings: bool
    safety_notice: str
    stage_results: list[AdapterDryRunConsumerReadinessStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter dry-run consumer readiness "
        "gate does not execute strategy logic, create signals, create trade "
        "plans, connect to brokers, request live market data, place real orders, "
        "use real money, calculate PnL, or prove profitability."
    )


def _stringify_outputs(outputs: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in outputs.items()}


def _overall_status(
    *,
    consumer_status: str,
    consumer_ready: bool,
    acceptance_status: str,
    acceptance_accepted: bool,
) -> str:
    if not consumer_ready or not acceptance_accepted:
        return "fail"
    if consumer_status == "warn" or acceptance_status == "warn":
        return "warn"
    if consumer_status == "pass" and acceptance_status == "pass":
        return "pass"
    return "fail"


def build_adapter_dry_run_consumer_readiness_report(
    *,
    adapter_evidence_readiness_path: Path,
    adapter_dry_run_events_path: Path,
    consumer_output_dir: Path,
    consumer_acceptance_output_dir: Path,
    readiness_output_dir: Path,
    min_events: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
    max_events: int | None = None,
) -> AdapterDryRunConsumerReadinessReport:
    consumer_report, consumer_outputs = build_and_write_adapter_dry_run_consumer_report(
        adapter_evidence_readiness_path=adapter_evidence_readiness_path,
        adapter_dry_run_events_path=adapter_dry_run_events_path,
        output_dir=consumer_output_dir,
        min_events=min_events,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
        max_events=max_events,
    )

    consumer_stage = AdapterDryRunConsumerReadinessStageResult(
        stage="recorded_data_paper_strategy_adapter_dry_run_consumer",
        status=consumer_report.status,
        output_directory=str(consumer_output_dir),
        output_files=_stringify_outputs(consumer_outputs),
        accepted=consumer_report.ready_for_future_consumer_evidence,
        summary={
            "ready_for_future_consumer_evidence": (
                consumer_report.ready_for_future_consumer_evidence
            ),
            "input_event_count": consumer_report.input_event_count,
            "consumed_event_count": consumer_report.consumed_event_count,
            "total_planned_bars": consumer_report.total_planned_bars,
            "issue_count": len(consumer_report.issues),
            "message": "Audit-only adapter dry-run consumer completed.",
        },
    )

    acceptance_report, acceptance_outputs = (
        build_and_write_adapter_dry_run_consumer_acceptance_report(
            consumer_report_path=consumer_outputs[
                "paper_strategy_adapter_dry_run_consumer_json"
            ],
            output_dir=consumer_acceptance_output_dir,
            min_consumed_events=min_events,
            min_total_planned_bars=min_total_planned_bars,
            allow_warnings=allow_warnings,
        )
    )

    acceptance_stage = AdapterDryRunConsumerReadinessStageResult(
        stage="recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance",
        status=acceptance_report.status,
        output_directory=str(consumer_acceptance_output_dir),
        output_files=_stringify_outputs(acceptance_outputs),
        accepted=acceptance_report.accepted,
        summary={
            "accepted": acceptance_report.accepted,
            "consumer_status": acceptance_report.consumer_status,
            "ready_for_future_consumer_evidence": (
                acceptance_report.ready_for_future_consumer_evidence
            ),
            "consumed_event_count": acceptance_report.consumed_event_count,
            "total_planned_bars": acceptance_report.total_planned_bars,
            "issue_count": len(acceptance_report.issues),
            "message": "Adapter dry-run consumer acceptance gate completed.",
        },
    )

    status = _overall_status(
        consumer_status=consumer_report.status,
        consumer_ready=consumer_report.ready_for_future_consumer_evidence,
        acceptance_status=acceptance_report.status,
        acceptance_accepted=acceptance_report.accepted,
    )

    return AdapterDryRunConsumerReadinessReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        ready_for_future_consumer_evidence_release=status in {"pass", "warn"},
        output_directory=str(readiness_output_dir),
        min_events_required=max(min_events, 0),
        min_total_planned_bars_required=max(min_total_planned_bars, 0),
        allow_warnings=allow_warnings,
        safety_notice=safety_notice(),
        stage_results=[consumer_stage, acceptance_stage],
    )


def write_adapter_dry_run_consumer_readiness_report(
    report: AdapterDryRunConsumerReadinessReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    readiness_json = output_dir / "paper_strategy_adapter_dry_run_consumer_readiness.json"
    readiness_txt = output_dir / "paper_strategy_adapter_dry_run_consumer_readiness.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["stage_results"] = [asdict(stage) for stage in report.stage_results]

    readiness_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Dry-Run Consumer Readiness Gate",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        (
            "Ready for future consumer evidence release: "
            f"{report.ready_for_future_consumer_evidence_release}"
        ),
        f"Minimum events required: {report.min_events_required}",
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
            "This gate only checks audit-only adapter dry-run consumer readiness.",
            "This report is not a profitability claim.",
        ]
    )
    readiness_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_adapter_dry_run_consumer_readiness",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_consumer_evidence_release": (
            report.ready_for_future_consumer_evidence_release
        ),
        "min_events_required": report.min_events_required,
        "min_total_planned_bars_required": report.min_total_planned_bars_required,
        "allow_warnings": report.allow_warnings,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_dry_run_consumer_readiness_json": str(
                readiness_json
            ),
            "paper_strategy_adapter_dry_run_consumer_readiness_txt": str(readiness_txt),
            "manifest_json": str(manifest_json),
        },
        "stages": [asdict(stage) for stage in report.stage_results],
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_adapter_dry_run_consumer_readiness_json": readiness_json,
        "paper_strategy_adapter_dry_run_consumer_readiness_txt": readiness_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_dry_run_consumer_readiness_report(
    *,
    adapter_evidence_readiness_path: Path,
    adapter_dry_run_events_path: Path,
    consumer_output_dir: Path,
    consumer_acceptance_output_dir: Path,
    readiness_output_dir: Path,
    min_events: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
    max_events: int | None = None,
) -> tuple[AdapterDryRunConsumerReadinessReport, dict[str, Path]]:
    report = build_adapter_dry_run_consumer_readiness_report(
        adapter_evidence_readiness_path=adapter_evidence_readiness_path,
        adapter_dry_run_events_path=adapter_dry_run_events_path,
        consumer_output_dir=consumer_output_dir,
        consumer_acceptance_output_dir=consumer_acceptance_output_dir,
        readiness_output_dir=readiness_output_dir,
        min_events=min_events,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
        max_events=max_events,
    )
    outputs = write_adapter_dry_run_consumer_readiness_report(
        report,
        readiness_output_dir,
    )
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run no-execution adapter dry-run consumer readiness gate."
    )
    parser.add_argument(
        "--adapter-evidence-readiness",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_evidence_readiness/"
            "paper_strategy_adapter_evidence_readiness.json"
        ),
    )
    parser.add_argument(
        "--adapter-dry-run-events",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run/"
            "paper_strategy_adapter_dry_run_events.jsonl"
        ),
    )
    parser.add_argument(
        "--consumer-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_consumer"
        ),
    )
    parser.add_argument(
        "--consumer-acceptance-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_consumer_readiness"
        ),
    )
    parser.add_argument("--min-events", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-events", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_dry_run_consumer_readiness_report(
        adapter_evidence_readiness_path=Path(args.adapter_evidence_readiness),
        adapter_dry_run_events_path=Path(args.adapter_dry_run_events),
        consumer_output_dir=Path(args.consumer_output_dir),
        consumer_acceptance_output_dir=Path(args.consumer_acceptance_output_dir),
        readiness_output_dir=Path(args.output_dir),
        min_events=args.min_events,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
        max_events=args.max_events,
    )

    print("HQE recorded data paper strategy adapter dry-run consumer readiness completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Ready for future consumer evidence release: "
        f"{report.ready_for_future_consumer_evidence_release}"
    )
    print(
        "Adapter dry-run consumer readiness report: "
        f"{outputs['paper_strategy_adapter_dry_run_consumer_readiness_txt']}"
    )
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
