"""
Recorded data replay evidence bundle.

Evidence-only orchestrator for the recorded-data replay pipeline:
inventory/discovery normalizer -> replay quality gate -> replay dry-run player.

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

from src.paper_trading.recorded_data_replay_dataset import (
    build_and_write_replay_dataset,
)
from src.paper_trading.recorded_data_replay_dry_run import (
    build_and_write_replay_dry_run_report,
)
from src.paper_trading.recorded_data_replay_quality_gate import (
    build_and_write_quality_gate_report,
)


@dataclass(frozen=True)
class ReplayEvidenceStageResult:
    """One stage result in the replay evidence bundle."""

    stage: str
    status: str
    output_directory: str
    output_files: dict[str, str]
    summary: dict[str, int | str | None]


@dataclass(frozen=True)
class ReplayEvidenceBundleReport:
    """Combined replay evidence bundle report."""

    generated_at_utc: str
    status: str
    output_directory: str
    safety_notice: str
    stage_results: list[ReplayEvidenceStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data replay evidence "
        "bundle does not run strategies, create trade plans, connect to brokers, "
        "request live market data, place real orders, use real money, or prove "
        "profitability."
    )


def _stringify_outputs(outputs: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in outputs.items()}


def _overall_status(stage_results: Sequence[ReplayEvidenceStageResult]) -> str:
    if any(stage.status == "fail" for stage in stage_results):
        return "fail"
    if any(stage.status == "warn" for stage in stage_results):
        return "warn"
    return "pass"


def build_replay_evidence_bundle(
    *,
    inventory_path: Path,
    recorded_roots: Sequence[Path],
    base_output_dir: Path,
    bundle_output_dir: Path,
    max_records: int | None = None,
) -> ReplayEvidenceBundleReport:
    """Run the complete recorded-data replay evidence pipeline."""

    dataset_output_dir = base_output_dir / "recorded_data_replay_dataset"
    quality_output_dir = base_output_dir / "recorded_data_replay_quality_gate"
    dry_run_output_dir = base_output_dir / "recorded_data_replay_dry_run"

    dataset_report, dataset_outputs = build_and_write_replay_dataset(
        inventory_path=inventory_path,
        recorded_roots=recorded_roots,
        output_dir=dataset_output_dir,
    )

    dataset_status = (
        "pass"
        if dataset_report.normalized_record_count > 0
        else "warn"
    )
    dataset_stage = ReplayEvidenceStageResult(
        stage="recorded_data_replay_dataset",
        status=dataset_status,
        output_directory=str(dataset_output_dir),
        output_files=_stringify_outputs(dataset_outputs),
        summary={
            "source_count": dataset_report.source_count,
            "normalized_record_count": dataset_report.normalized_record_count,
            "message": "Normalized replay dataset generated.",
        },
    )

    quality_report, quality_outputs = build_and_write_quality_gate_report(
        dataset_path=dataset_outputs["dataset_json"],
        output_dir=quality_output_dir,
    )
    quality_stage = ReplayEvidenceStageResult(
        stage="recorded_data_replay_quality_gate",
        status=quality_report.status,
        output_directory=str(quality_output_dir),
        output_files=_stringify_outputs(quality_outputs),
        summary={
            "source_count": quality_report.source_count,
            "record_count": quality_report.record_count,
            "issue_count": len(quality_report.issues),
            "message": "Replay dataset quality gate completed.",
        },
    )

    dry_run_report, dry_run_outputs = build_and_write_replay_dry_run_report(
        dataset_path=dataset_outputs["dataset_json"],
        quality_gate_path=quality_outputs["quality_gate_json"],
        output_dir=dry_run_output_dir,
        max_records=max_records,
    )
    dry_run_stage = ReplayEvidenceStageResult(
        stage="recorded_data_replay_dry_run",
        status=dry_run_report.status,
        output_directory=str(dry_run_output_dir),
        output_files=_stringify_outputs(dry_run_outputs),
        summary={
            "input_record_count": dry_run_report.input_record_count,
            "replayed_event_count": dry_run_report.replayed_event_count,
            "issue_count": len(dry_run_report.issues),
            "first_timestamp": dry_run_report.first_timestamp,
            "last_timestamp": dry_run_report.last_timestamp,
            "message": "Replay dry-run event stream completed.",
        },
    )

    stages = [dataset_stage, quality_stage, dry_run_stage]
    return ReplayEvidenceBundleReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=_overall_status(stages),
        output_directory=str(bundle_output_dir),
        safety_notice=safety_notice(),
        stage_results=stages,
    )


def write_replay_evidence_bundle(
    report: ReplayEvidenceBundleReport,
    output_dir: Path,
) -> dict[str, Path]:
    """Write combined replay evidence bundle reports."""

    output_dir.mkdir(parents=True, exist_ok=True)

    summary_json = output_dir / "evidence_summary.json"
    summary_txt = output_dir / "evidence_summary.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["stage_results"] = [
        asdict(stage) for stage in report.stage_results
    ]

    summary_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Replay Evidence Bundle",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        "",
        "Stages:",
    ]

    for stage in report.stage_results:
        lines.append(
            f"- {stage.stage}: status={stage.status}, "
            f"output={stage.output_directory}"
        )
        for key, value in stage.summary.items():
            lines.append(f"  - {key}: {value}")

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {summary_json}",
            f"- {summary_txt}",
            f"- {manifest_json}",
            "",
            "This bundle does not run strategies or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    summary_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_replay_evidence_bundle",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "stage_count": len(report.stage_results),
        "safety_notice": report.safety_notice,
        "outputs": {
            "evidence_summary_json": str(summary_json),
            "evidence_summary_txt": str(summary_txt),
            "manifest_json": str(manifest_json),
        },
        "stages": [asdict(stage) for stage in report.stage_results],
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "evidence_summary_json": summary_json,
        "evidence_summary_txt": summary_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_replay_evidence_bundle(
    *,
    inventory_path: Path,
    recorded_roots: Sequence[Path],
    base_output_dir: Path,
    bundle_output_dir: Path,
    max_records: int | None = None,
) -> tuple[ReplayEvidenceBundleReport, dict[str, Path]]:
    report = build_replay_evidence_bundle(
        inventory_path=inventory_path,
        recorded_roots=recorded_roots,
        base_output_dir=base_output_dir,
        bundle_output_dir=bundle_output_dir,
        max_records=max_records,
    )
    outputs = write_replay_evidence_bundle(report, bundle_output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the paper-only recorded-data replay evidence bundle."
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
        "--output-dir",
        default="reports/paper_trading/recorded_data_replay_evidence",
        help="Directory where combined evidence bundle reports are written.",
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

    report, outputs = build_and_write_replay_evidence_bundle(
        inventory_path=Path(args.inventory),
        recorded_roots=recorded_roots,
        base_output_dir=Path(args.base_output_dir),
        bundle_output_dir=Path(args.output_dir),
        max_records=args.max_records,
    )

    print("HQE recorded data replay evidence bundle completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Stage count: {len(report.stage_results)}")
    print(f"Evidence summary: {outputs['evidence_summary_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
