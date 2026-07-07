"""
Recorded data replay readiness gate.

One-command evidence-only orchestrator for recorded-data replay readiness:
1. Run the recorded-data replay evidence bundle.
2. Run the recorded-data replay acceptance gate.
3. Write a final readiness report.

This module does not run strategies, create trade plans, connect to brokers,
request live market data, place real orders, use real money, or prove
profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from src.paper_trading.recorded_data_replay_acceptance import (
    build_and_write_acceptance_report,
)
from src.paper_trading.recorded_data_replay_evidence import (
    build_and_write_replay_evidence_bundle,
)


@dataclass(frozen=True)
class ReplayReadinessStageResult:
    """One stage result in the final readiness gate."""

    stage: str
    status: str
    output_directory: str
    output_files: dict[str, str]
    accepted: bool | None
    summary: dict[str, int | str | bool | None]


@dataclass(frozen=True)
class ReplayReadinessReport:
    """Final replay readiness report."""

    generated_at_utc: str
    status: str
    ready_for_future_paper_replay: bool
    output_directory: str
    min_events_required: int
    allow_warnings: bool
    safety_notice: str
    stage_results: list[ReplayReadinessStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data replay readiness "
        "gate does not run strategies, create trade plans, connect to brokers, "
        "request live market data, place real orders, use real money, or prove "
        "profitability."
    )


def _stringify_outputs(outputs: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in outputs.items()}


def _readiness_status(
    evidence_status: str,
    acceptance_status: str,
    accepted: bool,
) -> str:
    if not accepted:
        return "fail"
    if evidence_status == "warn" or acceptance_status == "warn":
        return "warn"
    if evidence_status == "pass" and acceptance_status == "pass":
        return "pass"
    return "fail"


def build_replay_readiness_report(
    *,
    inventory_path: Path,
    recorded_roots: Sequence[Path],
    base_output_dir: Path,
    evidence_output_dir: Path,
    acceptance_output_dir: Path,
    readiness_output_dir: Path,
    min_events: int = 1,
    allow_warnings: bool = False,
    max_records: int | None = None,
) -> ReplayReadinessReport:
    """Run evidence bundle plus acceptance gate and build final readiness report."""

    evidence_report, evidence_outputs = build_and_write_replay_evidence_bundle(
        inventory_path=inventory_path,
        recorded_roots=recorded_roots,
        base_output_dir=base_output_dir,
        bundle_output_dir=evidence_output_dir,
        max_records=max_records,
    )

    evidence_stage = ReplayReadinessStageResult(
        stage="recorded_data_replay_evidence",
        status=evidence_report.status,
        output_directory=str(evidence_output_dir),
        output_files=_stringify_outputs(evidence_outputs),
        accepted=None,
        summary={
            "stage_count": len(evidence_report.stage_results),
            "message": "Recorded-data replay evidence bundle completed.",
        },
    )

    acceptance_report, acceptance_outputs = build_and_write_acceptance_report(
        evidence_summary_path=evidence_outputs["evidence_summary_json"],
        output_dir=acceptance_output_dir,
        min_events=min_events,
        allow_warnings=allow_warnings,
    )

    acceptance_stage = ReplayReadinessStageResult(
        stage="recorded_data_replay_acceptance",
        status=acceptance_report.status,
        output_directory=str(acceptance_output_dir),
        output_files=_stringify_outputs(acceptance_outputs),
        accepted=acceptance_report.accepted,
        summary={
            "accepted": acceptance_report.accepted,
            "min_events_required": acceptance_report.min_events_required,
            "allow_warnings": acceptance_report.allow_warnings,
            "bundle_status": acceptance_report.bundle_status,
            "stage_count": acceptance_report.stage_count,
            "replayed_event_count": acceptance_report.replayed_event_count,
            "issue_count": len(acceptance_report.issues),
            "message": "Recorded-data replay acceptance gate completed.",
        },
    )

    status = _readiness_status(
        evidence_report.status,
        acceptance_report.status,
        acceptance_report.accepted,
    )

    return ReplayReadinessReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        ready_for_future_paper_replay=acceptance_report.accepted,
        output_directory=str(readiness_output_dir),
        min_events_required=max(min_events, 0),
        allow_warnings=allow_warnings,
        safety_notice=safety_notice(),
        stage_results=[evidence_stage, acceptance_stage],
    )


def write_replay_readiness_report(
    report: ReplayReadinessReport,
    output_dir: Path,
) -> dict[str, Path]:
    """Write final readiness report outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)

    readiness_json = output_dir / "readiness_report.json"
    readiness_txt = output_dir / "readiness_report.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["stage_results"] = [asdict(stage) for stage in report.stage_results]

    readiness_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Replay Readiness Gate",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        f"Ready for future paper replay: {report.ready_for_future_paper_replay}",
        f"Minimum events required: {report.min_events_required}",
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
            "This gate only checks structural replay readiness.",
            "This report is not a profitability claim.",
        ]
    )
    readiness_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_replay_readiness_gate",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_paper_replay": report.ready_for_future_paper_replay,
        "min_events_required": report.min_events_required,
        "allow_warnings": report.allow_warnings,
        "safety_notice": report.safety_notice,
        "outputs": {
            "readiness_report_json": str(readiness_json),
            "readiness_report_txt": str(readiness_txt),
            "manifest_json": str(manifest_json),
        },
        "stages": [asdict(stage) for stage in report.stage_results],
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "readiness_report_json": readiness_json,
        "readiness_report_txt": readiness_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_replay_readiness_report(
    *,
    inventory_path: Path,
    recorded_roots: Sequence[Path],
    base_output_dir: Path,
    evidence_output_dir: Path,
    acceptance_output_dir: Path,
    readiness_output_dir: Path,
    min_events: int = 1,
    allow_warnings: bool = False,
    max_records: int | None = None,
) -> tuple[ReplayReadinessReport, dict[str, Path]]:
    report = build_replay_readiness_report(
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
    outputs = write_replay_readiness_report(report, readiness_output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the paper-only recorded-data replay readiness gate."
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
        help="Directory where acceptance-gate reports are written.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_replay_readiness",
        help="Directory where final readiness reports are written.",
    )
    parser.add_argument(
        "--min-events",
        type=int,
        default=1,
        help="Minimum replay dry-run events required for acceptance.",
    )
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="Allow warn-status replay evidence to be considered ready with warning status.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Optional maximum replay records for the dry-run stage.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    recorded_roots = (
        [Path(value) for value in args.recorded_root]
        if args.recorded_root
        else [Path("data/recorded"), Path("data/live_recording")]
    )

    report, outputs = build_and_write_replay_readiness_report(
        inventory_path=Path(args.inventory),
        recorded_roots=recorded_roots,
        base_output_dir=Path(args.base_output_dir),
        evidence_output_dir=Path(args.evidence_output_dir),
        acceptance_output_dir=Path(args.acceptance_output_dir),
        readiness_output_dir=Path(args.output_dir),
        min_events=args.min_events,
        allow_warnings=args.allow_warnings,
        max_records=args.max_records,
    )

    print("HQE recorded data replay readiness gate completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future paper replay: {report.ready_for_future_paper_replay}")
    print(f"Readiness report: {outputs['readiness_report_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
