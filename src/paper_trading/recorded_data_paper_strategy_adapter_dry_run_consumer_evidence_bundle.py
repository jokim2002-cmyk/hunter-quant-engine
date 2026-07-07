"""
Recorded data paper strategy adapter dry-run consumer evidence bundle.

One-command evidence-only bundle for the consumer layer:
1. Run adapter evidence readiness.
2. Run adapter dry-run consumer readiness.
3. Write final consumer evidence bundle.

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

from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run_consumer_readiness import (
    build_and_write_adapter_dry_run_consumer_readiness_report,
)
from src.paper_trading.recorded_data_paper_strategy_adapter_evidence_readiness import (
    build_and_write_adapter_evidence_readiness_report,
)


@dataclass(frozen=True)
class AdapterDryRunConsumerEvidenceBundleStageResult:
    stage: str
    status: str
    output_directory: str
    output_files: dict[str, str]
    accepted: bool
    summary: dict[str, int | str | bool | None]


@dataclass(frozen=True)
class AdapterDryRunConsumerEvidenceBundleReport:
    generated_at_utc: str
    status: str
    ready_for_future_consumer_evidence: bool
    output_directory: str
    min_requests_required: int
    min_total_planned_bars_required: int
    min_stages_required: int
    allow_warnings: bool
    safety_notice: str
    stage_results: list[AdapterDryRunConsumerEvidenceBundleStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter dry-run consumer evidence "
        "bundle does not execute strategy logic, create signals, create trade "
        "plans, connect to brokers, request live market data, place real orders, "
        "use real money, calculate PnL, or prove profitability."
    )


def _stringify_outputs(outputs: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in outputs.items()}


def _overall_status(
    *,
    adapter_status: str,
    adapter_ready: bool,
    consumer_status: str,
    consumer_ready: bool,
) -> str:
    if not adapter_ready or not consumer_ready:
        return "fail"
    if adapter_status == "warn" or consumer_status == "warn":
        return "warn"
    if adapter_status == "pass" and consumer_status == "pass":
        return "pass"
    return "fail"


def build_adapter_dry_run_consumer_evidence_bundle_report(
    *,
    plan_readiness_path: Path,
    replay_plan_path: Path,
    adapter_contract_output_dir: Path,
    adapter_contract_acceptance_output_dir: Path,
    adapter_readiness_output_dir: Path,
    adapter_dry_run_output_dir: Path,
    adapter_dry_run_acceptance_output_dir: Path,
    adapter_dry_run_readiness_output_dir: Path,
    adapter_evidence_bundle_output_dir: Path,
    adapter_evidence_bundle_acceptance_output_dir: Path,
    adapter_evidence_readiness_output_dir: Path,
    consumer_output_dir: Path,
    consumer_acceptance_output_dir: Path,
    consumer_readiness_output_dir: Path,
    evidence_output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    min_stages: int = 2,
    allow_warnings: bool = False,
    max_requests: int | None = None,
) -> AdapterDryRunConsumerEvidenceBundleReport:
    adapter_report, adapter_outputs = build_and_write_adapter_evidence_readiness_report(
        plan_readiness_path=plan_readiness_path,
        replay_plan_path=replay_plan_path,
        adapter_contract_output_dir=adapter_contract_output_dir,
        adapter_contract_acceptance_output_dir=adapter_contract_acceptance_output_dir,
        adapter_readiness_output_dir=adapter_readiness_output_dir,
        adapter_dry_run_output_dir=adapter_dry_run_output_dir,
        adapter_dry_run_acceptance_output_dir=adapter_dry_run_acceptance_output_dir,
        adapter_dry_run_readiness_output_dir=adapter_dry_run_readiness_output_dir,
        adapter_evidence_bundle_output_dir=adapter_evidence_bundle_output_dir,
        adapter_evidence_bundle_acceptance_output_dir=(
            adapter_evidence_bundle_acceptance_output_dir
        ),
        readiness_output_dir=adapter_evidence_readiness_output_dir,
        min_requests=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        min_stages=min_stages,
        allow_warnings=allow_warnings,
        max_requests=max_requests,
    )

    adapter_stage = AdapterDryRunConsumerEvidenceBundleStageResult(
        stage="recorded_data_paper_strategy_adapter_evidence_readiness",
        status=adapter_report.status,
        output_directory=str(adapter_evidence_readiness_output_dir),
        output_files=_stringify_outputs(adapter_outputs),
        accepted=adapter_report.ready_for_future_paper_strategy_adapter_evidence_release,
        summary={
            "ready_for_future_paper_strategy_adapter_evidence_release": (
                adapter_report.ready_for_future_paper_strategy_adapter_evidence_release
            ),
            "min_requests_required": adapter_report.min_requests_required,
            "min_total_planned_bars_required": (
                adapter_report.min_total_planned_bars_required
            ),
            "min_stages_required": adapter_report.min_stages_required,
            "stage_count": len(adapter_report.stage_results),
            "message": "Adapter evidence readiness completed.",
        },
    )

    adapter_evidence_readiness_path = adapter_outputs[
        "paper_strategy_adapter_evidence_readiness_json"
    ]
    adapter_dry_run_events_path = (
        adapter_dry_run_output_dir / "paper_strategy_adapter_dry_run_events.jsonl"
    )

    consumer_report, consumer_outputs = (
        build_and_write_adapter_dry_run_consumer_readiness_report(
            adapter_evidence_readiness_path=adapter_evidence_readiness_path,
            adapter_dry_run_events_path=adapter_dry_run_events_path,
            consumer_output_dir=consumer_output_dir,
            consumer_acceptance_output_dir=consumer_acceptance_output_dir,
            readiness_output_dir=consumer_readiness_output_dir,
            min_events=min_requests,
            min_total_planned_bars=min_total_planned_bars,
            allow_warnings=allow_warnings,
            max_events=max_requests,
        )
    )

    consumer_stage = AdapterDryRunConsumerEvidenceBundleStageResult(
        stage="recorded_data_paper_strategy_adapter_dry_run_consumer_readiness",
        status=consumer_report.status,
        output_directory=str(consumer_readiness_output_dir),
        output_files=_stringify_outputs(consumer_outputs),
        accepted=consumer_report.ready_for_future_consumer_evidence_release,
        summary={
            "ready_for_future_consumer_evidence_release": (
                consumer_report.ready_for_future_consumer_evidence_release
            ),
            "min_events_required": consumer_report.min_events_required,
            "min_total_planned_bars_required": (
                consumer_report.min_total_planned_bars_required
            ),
            "stage_count": len(consumer_report.stage_results),
            "message": "Adapter dry-run consumer readiness completed.",
        },
    )

    status = _overall_status(
        adapter_status=adapter_report.status,
        adapter_ready=(
            adapter_report.ready_for_future_paper_strategy_adapter_evidence_release
        ),
        consumer_status=consumer_report.status,
        consumer_ready=consumer_report.ready_for_future_consumer_evidence_release,
    )

    return AdapterDryRunConsumerEvidenceBundleReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        ready_for_future_consumer_evidence=status in {"pass", "warn"},
        output_directory=str(evidence_output_dir),
        min_requests_required=max(min_requests, 0),
        min_total_planned_bars_required=max(min_total_planned_bars, 0),
        min_stages_required=max(min_stages, 0),
        allow_warnings=allow_warnings,
        safety_notice=safety_notice(),
        stage_results=[adapter_stage, consumer_stage],
    )


def write_adapter_dry_run_consumer_evidence_bundle_report(
    report: AdapterDryRunConsumerEvidenceBundleReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    evidence_json = output_dir / "paper_strategy_adapter_dry_run_consumer_evidence_bundle.json"
    evidence_txt = output_dir / "paper_strategy_adapter_dry_run_consumer_evidence_bundle.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["stage_results"] = [asdict(stage) for stage in report.stage_results]

    evidence_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Dry-Run Consumer Evidence Bundle",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        f"Ready for future consumer evidence: {report.ready_for_future_consumer_evidence}",
        f"Minimum requests/events required: {report.min_requests_required}",
        f"Minimum total planned bars required: {report.min_total_planned_bars_required}",
        f"Minimum stages required: {report.min_stages_required}",
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
            f"- {evidence_json}",
            f"- {evidence_txt}",
            f"- {manifest_json}",
            "",
            "This bundle only packages audit-only consumer evidence.",
            "This report is not a profitability claim.",
        ]
    )
    evidence_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_consumer_evidence": report.ready_for_future_consumer_evidence,
        "min_requests_required": report.min_requests_required,
        "min_total_planned_bars_required": report.min_total_planned_bars_required,
        "min_stages_required": report.min_stages_required,
        "allow_warnings": report.allow_warnings,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_dry_run_consumer_evidence_bundle_json": str(
                evidence_json
            ),
            "paper_strategy_adapter_dry_run_consumer_evidence_bundle_txt": str(
                evidence_txt
            ),
            "manifest_json": str(manifest_json),
        },
        "stages": [asdict(stage) for stage in report.stage_results],
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_adapter_dry_run_consumer_evidence_bundle_json": evidence_json,
        "paper_strategy_adapter_dry_run_consumer_evidence_bundle_txt": evidence_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_dry_run_consumer_evidence_bundle_report(
    *,
    plan_readiness_path: Path,
    replay_plan_path: Path,
    adapter_contract_output_dir: Path,
    adapter_contract_acceptance_output_dir: Path,
    adapter_readiness_output_dir: Path,
    adapter_dry_run_output_dir: Path,
    adapter_dry_run_acceptance_output_dir: Path,
    adapter_dry_run_readiness_output_dir: Path,
    adapter_evidence_bundle_output_dir: Path,
    adapter_evidence_bundle_acceptance_output_dir: Path,
    adapter_evidence_readiness_output_dir: Path,
    consumer_output_dir: Path,
    consumer_acceptance_output_dir: Path,
    consumer_readiness_output_dir: Path,
    evidence_output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    min_stages: int = 2,
    allow_warnings: bool = False,
    max_requests: int | None = None,
) -> tuple[AdapterDryRunConsumerEvidenceBundleReport, dict[str, Path]]:
    report = build_adapter_dry_run_consumer_evidence_bundle_report(
        plan_readiness_path=plan_readiness_path,
        replay_plan_path=replay_plan_path,
        adapter_contract_output_dir=adapter_contract_output_dir,
        adapter_contract_acceptance_output_dir=adapter_contract_acceptance_output_dir,
        adapter_readiness_output_dir=adapter_readiness_output_dir,
        adapter_dry_run_output_dir=adapter_dry_run_output_dir,
        adapter_dry_run_acceptance_output_dir=adapter_dry_run_acceptance_output_dir,
        adapter_dry_run_readiness_output_dir=adapter_dry_run_readiness_output_dir,
        adapter_evidence_bundle_output_dir=adapter_evidence_bundle_output_dir,
        adapter_evidence_bundle_acceptance_output_dir=(
            adapter_evidence_bundle_acceptance_output_dir
        ),
        adapter_evidence_readiness_output_dir=adapter_evidence_readiness_output_dir,
        consumer_output_dir=consumer_output_dir,
        consumer_acceptance_output_dir=consumer_acceptance_output_dir,
        consumer_readiness_output_dir=consumer_readiness_output_dir,
        evidence_output_dir=evidence_output_dir,
        min_requests=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        min_stages=min_stages,
        allow_warnings=allow_warnings,
        max_requests=max_requests,
    )
    outputs = write_adapter_dry_run_consumer_evidence_bundle_report(
        report,
        evidence_output_dir,
    )
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build no-execution adapter dry-run consumer evidence bundle."
    )
    parser.add_argument(
        "--plan-readiness",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_replay_plan_readiness/"
            "paper_strategy_replay_plan_readiness.json"
        ),
    )
    parser.add_argument(
        "--replay-plan",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_replay_plan/"
            "paper_strategy_replay_plan.json"
        ),
    )
    parser.add_argument(
        "--adapter-contract-output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_contract",
    )
    parser.add_argument(
        "--adapter-contract-acceptance-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_contract_acceptance"
        ),
    )
    parser.add_argument(
        "--adapter-readiness-output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_readiness",
    )
    parser.add_argument(
        "--adapter-dry-run-output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_dry_run",
    )
    parser.add_argument(
        "--adapter-dry-run-acceptance-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_acceptance"
        ),
    )
    parser.add_argument(
        "--adapter-dry-run-readiness-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_readiness"
        ),
    )
    parser.add_argument(
        "--adapter-evidence-bundle-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_evidence_bundle"
        ),
    )
    parser.add_argument(
        "--adapter-evidence-bundle-acceptance-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_evidence_bundle_acceptance"
        ),
    )
    parser.add_argument(
        "--adapter-evidence-readiness-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_evidence_readiness"
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
        "--consumer-readiness-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_consumer_readiness"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle"
        ),
    )
    parser.add_argument("--min-requests", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--min-stages", type=int, default=2)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-requests", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_dry_run_consumer_evidence_bundle_report(
        plan_readiness_path=Path(args.plan_readiness),
        replay_plan_path=Path(args.replay_plan),
        adapter_contract_output_dir=Path(args.adapter_contract_output_dir),
        adapter_contract_acceptance_output_dir=Path(
            args.adapter_contract_acceptance_output_dir
        ),
        adapter_readiness_output_dir=Path(args.adapter_readiness_output_dir),
        adapter_dry_run_output_dir=Path(args.adapter_dry_run_output_dir),
        adapter_dry_run_acceptance_output_dir=Path(
            args.adapter_dry_run_acceptance_output_dir
        ),
        adapter_dry_run_readiness_output_dir=Path(
            args.adapter_dry_run_readiness_output_dir
        ),
        adapter_evidence_bundle_output_dir=Path(args.adapter_evidence_bundle_output_dir),
        adapter_evidence_bundle_acceptance_output_dir=Path(
            args.adapter_evidence_bundle_acceptance_output_dir
        ),
        adapter_evidence_readiness_output_dir=Path(
            args.adapter_evidence_readiness_output_dir
        ),
        consumer_output_dir=Path(args.consumer_output_dir),
        consumer_acceptance_output_dir=Path(args.consumer_acceptance_output_dir),
        consumer_readiness_output_dir=Path(args.consumer_readiness_output_dir),
        evidence_output_dir=Path(args.output_dir),
        min_requests=args.min_requests,
        min_total_planned_bars=args.min_total_planned_bars,
        min_stages=args.min_stages,
        allow_warnings=args.allow_warnings,
        max_requests=args.max_requests,
    )

    print("HQE recorded data paper strategy adapter dry-run consumer evidence bundle completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future consumer evidence: {report.ready_for_future_consumer_evidence}")
    print(
        "Consumer evidence bundle: "
        f"{outputs['paper_strategy_adapter_dry_run_consumer_evidence_bundle_txt']}"
    )
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
