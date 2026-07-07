"""
Recorded data paper strategy adapter evidence bundle.

One-command evidence-only bundle for the adapter layer:
1. Run adapter readiness.
2. Run adapter dry-run readiness.
3. Write final adapter evidence bundle.

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

from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run_readiness import (
    build_and_write_adapter_dry_run_readiness_report,
)
from src.paper_trading.recorded_data_paper_strategy_adapter_readiness import (
    build_and_write_adapter_readiness_report,
)


@dataclass(frozen=True)
class AdapterEvidenceBundleStageResult:
    stage: str
    status: str
    output_directory: str
    output_files: dict[str, str]
    accepted: bool
    summary: dict[str, int | str | bool | None]


@dataclass(frozen=True)
class AdapterEvidenceBundleReport:
    generated_at_utc: str
    status: str
    ready_for_future_adapter_evidence: bool
    output_directory: str
    min_requests_required: int
    min_total_planned_bars_required: int
    allow_warnings: bool
    safety_notice: str
    stage_results: list[AdapterEvidenceBundleStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter evidence bundle does not "
        "execute strategy logic, create signals, create trade plans, connect to "
        "brokers, request live market data, place real orders, use real money, "
        "calculate PnL, or prove profitability."
    )


def _stringify_outputs(outputs: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in outputs.items()}


def _overall_status(
    *,
    adapter_status: str,
    adapter_ready: bool,
    dry_run_status: str,
    dry_run_ready: bool,
) -> str:
    if not adapter_ready or not dry_run_ready:
        return "fail"
    if adapter_status == "warn" or dry_run_status == "warn":
        return "warn"
    if adapter_status == "pass" and dry_run_status == "pass":
        return "pass"
    return "fail"


def build_adapter_evidence_bundle_report(
    *,
    plan_readiness_path: Path,
    replay_plan_path: Path,
    adapter_contract_output_dir: Path,
    adapter_contract_acceptance_output_dir: Path,
    adapter_readiness_output_dir: Path,
    adapter_dry_run_output_dir: Path,
    adapter_dry_run_acceptance_output_dir: Path,
    adapter_dry_run_readiness_output_dir: Path,
    evidence_output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
    max_requests: int | None = None,
) -> AdapterEvidenceBundleReport:
    adapter_report, adapter_outputs = build_and_write_adapter_readiness_report(
        plan_readiness_path=plan_readiness_path,
        replay_plan_path=replay_plan_path,
        contract_output_dir=adapter_contract_output_dir,
        contract_acceptance_output_dir=adapter_contract_acceptance_output_dir,
        readiness_output_dir=adapter_readiness_output_dir,
        min_requests=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )

    adapter_stage = AdapterEvidenceBundleStageResult(
        stage="recorded_data_paper_strategy_adapter_readiness",
        status=adapter_report.status,
        output_directory=str(adapter_readiness_output_dir),
        output_files=_stringify_outputs(adapter_outputs),
        accepted=adapter_report.ready_for_future_adapter_dry_run,
        summary={
            "ready_for_future_adapter_dry_run": (
                adapter_report.ready_for_future_adapter_dry_run
            ),
            "min_requests_required": adapter_report.min_requests_required,
            "min_total_planned_bars_required": (
                adapter_report.min_total_planned_bars_required
            ),
            "stage_count": len(adapter_report.stage_results),
            "message": "No-execution adapter readiness completed.",
        },
    )

    adapter_readiness_path = adapter_outputs["paper_strategy_adapter_readiness_json"]
    adapter_requests_path = adapter_contract_output_dir / "paper_strategy_adapter_requests.jsonl"

    dry_run_report, dry_run_outputs = build_and_write_adapter_dry_run_readiness_report(
        adapter_readiness_path=adapter_readiness_path,
        adapter_requests_path=adapter_requests_path,
        dry_run_output_dir=adapter_dry_run_output_dir,
        dry_run_acceptance_output_dir=adapter_dry_run_acceptance_output_dir,
        readiness_output_dir=adapter_dry_run_readiness_output_dir,
        min_events=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
        max_requests=max_requests,
    )

    dry_run_stage = AdapterEvidenceBundleStageResult(
        stage="recorded_data_paper_strategy_adapter_dry_run_readiness",
        status=dry_run_report.status,
        output_directory=str(adapter_dry_run_readiness_output_dir),
        output_files=_stringify_outputs(dry_run_outputs),
        accepted=dry_run_report.ready_for_future_adapter_evidence,
        summary={
            "ready_for_future_adapter_evidence": (
                dry_run_report.ready_for_future_adapter_evidence
            ),
            "min_events_required": dry_run_report.min_events_required,
            "min_total_planned_bars_required": (
                dry_run_report.min_total_planned_bars_required
            ),
            "stage_count": len(dry_run_report.stage_results),
            "message": "No-execution adapter dry-run readiness completed.",
        },
    )

    status = _overall_status(
        adapter_status=adapter_report.status,
        adapter_ready=adapter_report.ready_for_future_adapter_dry_run,
        dry_run_status=dry_run_report.status,
        dry_run_ready=dry_run_report.ready_for_future_adapter_evidence,
    )

    return AdapterEvidenceBundleReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        ready_for_future_adapter_evidence=status in {"pass", "warn"},
        output_directory=str(evidence_output_dir),
        min_requests_required=max(min_requests, 0),
        min_total_planned_bars_required=max(min_total_planned_bars, 0),
        allow_warnings=allow_warnings,
        safety_notice=safety_notice(),
        stage_results=[adapter_stage, dry_run_stage],
    )


def write_adapter_evidence_bundle_report(
    report: AdapterEvidenceBundleReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle_json = output_dir / "paper_strategy_adapter_evidence_bundle.json"
    bundle_txt = output_dir / "paper_strategy_adapter_evidence_bundle.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["stage_results"] = [asdict(stage) for stage in report.stage_results]

    bundle_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Evidence Bundle",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        f"Ready for future adapter evidence: {report.ready_for_future_adapter_evidence}",
        f"Minimum requests/events required: {report.min_requests_required}",
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
            f"- {bundle_json}",
            f"- {bundle_txt}",
            f"- {manifest_json}",
            "",
            "This bundle only packages structural adapter evidence.",
            "This report is not a profitability claim.",
        ]
    )
    bundle_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_adapter_evidence_bundle",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_adapter_evidence": report.ready_for_future_adapter_evidence,
        "min_requests_required": report.min_requests_required,
        "min_total_planned_bars_required": report.min_total_planned_bars_required,
        "allow_warnings": report.allow_warnings,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_evidence_bundle_json": str(bundle_json),
            "paper_strategy_adapter_evidence_bundle_txt": str(bundle_txt),
            "manifest_json": str(manifest_json),
        },
        "stages": [asdict(stage) for stage in report.stage_results],
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_adapter_evidence_bundle_json": bundle_json,
        "paper_strategy_adapter_evidence_bundle_txt": bundle_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_evidence_bundle_report(
    *,
    plan_readiness_path: Path,
    replay_plan_path: Path,
    adapter_contract_output_dir: Path,
    adapter_contract_acceptance_output_dir: Path,
    adapter_readiness_output_dir: Path,
    adapter_dry_run_output_dir: Path,
    adapter_dry_run_acceptance_output_dir: Path,
    adapter_dry_run_readiness_output_dir: Path,
    evidence_output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
    max_requests: int | None = None,
) -> tuple[AdapterEvidenceBundleReport, dict[str, Path]]:
    report = build_adapter_evidence_bundle_report(
        plan_readiness_path=plan_readiness_path,
        replay_plan_path=replay_plan_path,
        adapter_contract_output_dir=adapter_contract_output_dir,
        adapter_contract_acceptance_output_dir=adapter_contract_acceptance_output_dir,
        adapter_readiness_output_dir=adapter_readiness_output_dir,
        adapter_dry_run_output_dir=adapter_dry_run_output_dir,
        adapter_dry_run_acceptance_output_dir=adapter_dry_run_acceptance_output_dir,
        adapter_dry_run_readiness_output_dir=adapter_dry_run_readiness_output_dir,
        evidence_output_dir=evidence_output_dir,
        min_requests=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
        max_requests=max_requests,
    )
    outputs = write_adapter_evidence_bundle_report(report, evidence_output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build no-execution paper strategy adapter evidence bundle."
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
        "--output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_evidence_bundle",
    )
    parser.add_argument("--min-requests", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-requests", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_evidence_bundle_report(
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
        evidence_output_dir=Path(args.output_dir),
        min_requests=args.min_requests,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
        max_requests=args.max_requests,
    )

    print("HQE recorded data paper strategy adapter evidence bundle completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future adapter evidence: {report.ready_for_future_adapter_evidence}")
    print(f"Adapter evidence bundle: {outputs['paper_strategy_adapter_evidence_bundle_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
