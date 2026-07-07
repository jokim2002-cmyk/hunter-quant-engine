"""
Recorded data paper strategy adapter dry-run readiness gate.

One-command evidence-only readiness gate for future adapter evidence:
1. Build adapter dry-run events.
2. Run adapter dry-run acceptance.
3. Write final adapter dry-run readiness report.

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

from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run import (
    build_and_write_adapter_dry_run_report,
)
from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run_acceptance import (
    build_and_write_adapter_dry_run_acceptance_report,
)


@dataclass(frozen=True)
class AdapterDryRunReadinessStageResult:
    stage: str
    status: str
    output_directory: str
    output_files: dict[str, str]
    accepted: bool
    summary: dict[str, int | str | bool | None]


@dataclass(frozen=True)
class AdapterDryRunReadinessReport:
    generated_at_utc: str
    status: str
    ready_for_future_adapter_evidence: bool
    output_directory: str
    min_events_required: int
    min_total_planned_bars_required: int
    allow_warnings: bool
    safety_notice: str
    stage_results: list[AdapterDryRunReadinessStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter dry-run readiness gate "
        "does not execute strategy logic, create signals, create trade plans, "
        "connect to brokers, request live market data, place real orders, use "
        "real money, calculate PnL, or prove profitability."
    )


def _stringify_outputs(outputs: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in outputs.items()}


def _overall_status(
    *,
    dry_run_status: str,
    dry_run_ready: bool,
    acceptance_status: str,
    acceptance_accepted: bool,
) -> str:
    if not dry_run_ready or not acceptance_accepted:
        return "fail"
    if dry_run_status == "warn" or acceptance_status == "warn":
        return "warn"
    if dry_run_status == "pass" and acceptance_status == "pass":
        return "pass"
    return "fail"


def build_adapter_dry_run_readiness_report(
    *,
    adapter_readiness_path: Path,
    adapter_requests_path: Path,
    dry_run_output_dir: Path,
    dry_run_acceptance_output_dir: Path,
    readiness_output_dir: Path,
    min_events: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
    max_requests: int | None = None,
) -> AdapterDryRunReadinessReport:
    dry_run_report, dry_run_outputs = build_and_write_adapter_dry_run_report(
        adapter_readiness_path=adapter_readiness_path,
        adapter_requests_path=adapter_requests_path,
        output_dir=dry_run_output_dir,
        min_requests=min_events,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
        max_requests=max_requests,
    )

    dry_run_stage = AdapterDryRunReadinessStageResult(
        stage="recorded_data_paper_strategy_adapter_dry_run",
        status=dry_run_report.status,
        output_directory=str(dry_run_output_dir),
        output_files=_stringify_outputs(dry_run_outputs),
        accepted=dry_run_report.ready_for_future_adapter_evidence,
        summary={
            "ready_for_future_adapter_evidence": (
                dry_run_report.ready_for_future_adapter_evidence
            ),
            "request_count": dry_run_report.request_count,
            "dry_run_event_count": dry_run_report.dry_run_event_count,
            "total_planned_bars": dry_run_report.total_planned_bars,
            "min_events_required": dry_run_report.min_requests_required,
            "min_total_planned_bars_required": (
                dry_run_report.min_total_planned_bars_required
            ),
            "issue_count": len(dry_run_report.issues),
            "message": "No-execution adapter dry-run completed.",
        },
    )

    acceptance_report, acceptance_outputs = build_and_write_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=dry_run_outputs["paper_strategy_adapter_dry_run_json"],
        output_dir=dry_run_acceptance_output_dir,
        min_events=min_events,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )

    acceptance_stage = AdapterDryRunReadinessStageResult(
        stage="recorded_data_paper_strategy_adapter_dry_run_acceptance",
        status=acceptance_report.status,
        output_directory=str(dry_run_acceptance_output_dir),
        output_files=_stringify_outputs(acceptance_outputs),
        accepted=acceptance_report.accepted,
        summary={
            "accepted": acceptance_report.accepted,
            "allow_warnings": acceptance_report.allow_warnings,
            "dry_run_status": acceptance_report.dry_run_status,
            "ready_for_future_adapter_evidence": (
                acceptance_report.ready_for_future_adapter_evidence
            ),
            "event_count": acceptance_report.event_count,
            "total_planned_bars": acceptance_report.total_planned_bars,
            "min_events_required": acceptance_report.min_events_required,
            "min_total_planned_bars_required": (
                acceptance_report.min_total_planned_bars_required
            ),
            "issue_count": len(acceptance_report.issues),
            "message": "Adapter dry-run acceptance gate completed.",
        },
    )

    status = _overall_status(
        dry_run_status=dry_run_report.status,
        dry_run_ready=dry_run_report.ready_for_future_adapter_evidence,
        acceptance_status=acceptance_report.status,
        acceptance_accepted=acceptance_report.accepted,
    )

    return AdapterDryRunReadinessReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        ready_for_future_adapter_evidence=status in {"pass", "warn"},
        output_directory=str(readiness_output_dir),
        min_events_required=max(min_events, 0),
        min_total_planned_bars_required=max(min_total_planned_bars, 0),
        allow_warnings=allow_warnings,
        safety_notice=safety_notice(),
        stage_results=[dry_run_stage, acceptance_stage],
    )


def write_adapter_dry_run_readiness_report(
    report: AdapterDryRunReadinessReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    readiness_json = output_dir / "paper_strategy_adapter_dry_run_readiness.json"
    readiness_txt = output_dir / "paper_strategy_adapter_dry_run_readiness.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["stage_results"] = [asdict(stage) for stage in report.stage_results]

    readiness_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Dry-Run Readiness Gate",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        f"Ready for future adapter evidence: {report.ready_for_future_adapter_evidence}",
        f"Minimum dry-run events required: {report.min_events_required}",
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
            "This gate only checks structural adapter dry-run readiness.",
            "This report is not a profitability claim.",
        ]
    )
    readiness_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_adapter_dry_run_readiness",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_adapter_evidence": report.ready_for_future_adapter_evidence,
        "min_events_required": report.min_events_required,
        "min_total_planned_bars_required": report.min_total_planned_bars_required,
        "allow_warnings": report.allow_warnings,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_dry_run_readiness_json": str(readiness_json),
            "paper_strategy_adapter_dry_run_readiness_txt": str(readiness_txt),
            "manifest_json": str(manifest_json),
        },
        "stages": [asdict(stage) for stage in report.stage_results],
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_adapter_dry_run_readiness_json": readiness_json,
        "paper_strategy_adapter_dry_run_readiness_txt": readiness_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_dry_run_readiness_report(
    *,
    adapter_readiness_path: Path,
    adapter_requests_path: Path,
    dry_run_output_dir: Path,
    dry_run_acceptance_output_dir: Path,
    readiness_output_dir: Path,
    min_events: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
    max_requests: int | None = None,
) -> tuple[AdapterDryRunReadinessReport, dict[str, Path]]:
    report = build_adapter_dry_run_readiness_report(
        adapter_readiness_path=adapter_readiness_path,
        adapter_requests_path=adapter_requests_path,
        dry_run_output_dir=dry_run_output_dir,
        dry_run_acceptance_output_dir=dry_run_acceptance_output_dir,
        readiness_output_dir=readiness_output_dir,
        min_events=min_events,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
        max_requests=max_requests,
    )
    outputs = write_adapter_dry_run_readiness_report(report, readiness_output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run no-execution paper strategy adapter dry-run readiness gate."
    )
    parser.add_argument(
        "--adapter-readiness",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_readiness/"
            "paper_strategy_adapter_readiness.json"
        ),
    )
    parser.add_argument(
        "--adapter-requests",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_contract/"
            "paper_strategy_adapter_requests.jsonl"
        ),
    )
    parser.add_argument(
        "--dry-run-output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_dry_run",
    )
    parser.add_argument(
        "--dry-run-acceptance-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_acceptance"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_readiness"
        ),
    )
    parser.add_argument("--min-events", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-requests", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_dry_run_readiness_report(
        adapter_readiness_path=Path(args.adapter_readiness),
        adapter_requests_path=Path(args.adapter_requests),
        dry_run_output_dir=Path(args.dry_run_output_dir),
        dry_run_acceptance_output_dir=Path(args.dry_run_acceptance_output_dir),
        readiness_output_dir=Path(args.output_dir),
        min_events=args.min_events,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
        max_requests=args.max_requests,
    )

    print("HQE recorded data paper strategy adapter dry-run readiness completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future adapter evidence: {report.ready_for_future_adapter_evidence}")
    print(
        "Adapter dry-run readiness report: "
        f"{outputs['paper_strategy_adapter_dry_run_readiness_txt']}"
    )
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
