"""
Recorded data paper strategy adapter readiness gate.

One-command evidence-only readiness gate for future paper/simulation adapter
dry-run:
1. Build the no-execution adapter contract.
2. Run the adapter contract acceptance gate.
3. Write final adapter readiness report.

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

from src.paper_trading.recorded_data_paper_strategy_adapter_contract import (
    build_and_write_adapter_contract_report,
)
from src.paper_trading.recorded_data_paper_strategy_adapter_contract_acceptance import (
    build_and_write_adapter_contract_acceptance_report,
)


@dataclass(frozen=True)
class AdapterReadinessStageResult:
    stage: str
    status: str
    output_directory: str
    output_files: dict[str, str]
    accepted: bool
    summary: dict[str, int | str | bool | None]


@dataclass(frozen=True)
class AdapterReadinessReport:
    generated_at_utc: str
    status: str
    ready_for_future_adapter_dry_run: bool
    output_directory: str
    min_requests_required: int
    min_total_planned_bars_required: int
    allow_warnings: bool
    safety_notice: str
    stage_results: list[AdapterReadinessStageResult]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter readiness gate does not "
        "execute strategy logic, create signals, create trade plans, connect to "
        "brokers, request live market data, place real orders, use real money, "
        "calculate PnL, or prove profitability."
    )


def _stringify_outputs(outputs: dict[str, Path]) -> dict[str, str]:
    return {name: str(path) for name, path in outputs.items()}


def _overall_status(
    *,
    contract_status: str,
    contract_ready: bool,
    acceptance_status: str,
    acceptance_accepted: bool,
) -> str:
    if not contract_ready or not acceptance_accepted:
        return "fail"
    if contract_status == "warn" or acceptance_status == "warn":
        return "warn"
    if contract_status == "pass" and acceptance_status == "pass":
        return "pass"
    return "fail"


def build_adapter_readiness_report(
    *,
    plan_readiness_path: Path,
    replay_plan_path: Path,
    contract_output_dir: Path,
    contract_acceptance_output_dir: Path,
    readiness_output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> AdapterReadinessReport:
    contract_report, contract_outputs = build_and_write_adapter_contract_report(
        plan_readiness_path=plan_readiness_path,
        replay_plan_path=replay_plan_path,
        output_dir=contract_output_dir,
        min_requests=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )

    contract_stage = AdapterReadinessStageResult(
        stage="recorded_data_paper_strategy_adapter_contract",
        status=contract_report.status,
        output_directory=str(contract_output_dir),
        output_files=_stringify_outputs(contract_outputs),
        accepted=contract_report.ready_for_future_adapter,
        summary={
            "ready_for_future_adapter": contract_report.ready_for_future_adapter,
            "request_count": contract_report.request_count,
            "total_planned_bars": contract_report.total_planned_bars,
            "min_requests_required": contract_report.min_requests_required,
            "min_total_planned_bars_required": (
                contract_report.min_total_planned_bars_required
            ),
            "issue_count": len(contract_report.issues),
            "message": "No-execution adapter contract completed.",
        },
    )

    acceptance_report, acceptance_outputs = build_and_write_adapter_contract_acceptance_report(
        adapter_contract_path=contract_outputs["paper_strategy_adapter_contract_json"],
        output_dir=contract_acceptance_output_dir,
        min_requests=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )

    acceptance_stage = AdapterReadinessStageResult(
        stage="recorded_data_paper_strategy_adapter_contract_acceptance",
        status=acceptance_report.status,
        output_directory=str(contract_acceptance_output_dir),
        output_files=_stringify_outputs(acceptance_outputs),
        accepted=acceptance_report.accepted,
        summary={
            "accepted": acceptance_report.accepted,
            "allow_warnings": acceptance_report.allow_warnings,
            "contract_status": acceptance_report.contract_status,
            "ready_for_future_adapter": acceptance_report.ready_for_future_adapter,
            "request_count": acceptance_report.request_count,
            "total_planned_bars": acceptance_report.total_planned_bars,
            "min_requests_required": acceptance_report.min_requests_required,
            "min_total_planned_bars_required": (
                acceptance_report.min_total_planned_bars_required
            ),
            "issue_count": len(acceptance_report.issues),
            "message": "Adapter contract acceptance gate completed.",
        },
    )

    status = _overall_status(
        contract_status=contract_report.status,
        contract_ready=contract_report.ready_for_future_adapter,
        acceptance_status=acceptance_report.status,
        acceptance_accepted=acceptance_report.accepted,
    )

    return AdapterReadinessReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        ready_for_future_adapter_dry_run=status in {"pass", "warn"},
        output_directory=str(readiness_output_dir),
        min_requests_required=max(min_requests, 0),
        min_total_planned_bars_required=max(min_total_planned_bars, 0),
        allow_warnings=allow_warnings,
        safety_notice=safety_notice(),
        stage_results=[contract_stage, acceptance_stage],
    )


def write_adapter_readiness_report(
    report: AdapterReadinessReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    readiness_json = output_dir / "paper_strategy_adapter_readiness.json"
    readiness_txt = output_dir / "paper_strategy_adapter_readiness.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["stage_results"] = [asdict(stage) for stage in report.stage_results]

    readiness_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Readiness Gate",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        f"Ready for future adapter dry-run: {report.ready_for_future_adapter_dry_run}",
        f"Minimum adapter requests required: {report.min_requests_required}",
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
            "This gate only checks structural adapter readiness.",
            "This report is not a profitability claim.",
        ]
    )
    readiness_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_adapter_readiness",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_adapter_dry_run": report.ready_for_future_adapter_dry_run,
        "min_requests_required": report.min_requests_required,
        "min_total_planned_bars_required": report.min_total_planned_bars_required,
        "allow_warnings": report.allow_warnings,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_readiness_json": str(readiness_json),
            "paper_strategy_adapter_readiness_txt": str(readiness_txt),
            "manifest_json": str(manifest_json),
        },
        "stages": [asdict(stage) for stage in report.stage_results],
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_adapter_readiness_json": readiness_json,
        "paper_strategy_adapter_readiness_txt": readiness_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_readiness_report(
    *,
    plan_readiness_path: Path,
    replay_plan_path: Path,
    contract_output_dir: Path,
    contract_acceptance_output_dir: Path,
    readiness_output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> tuple[AdapterReadinessReport, dict[str, Path]]:
    report = build_adapter_readiness_report(
        plan_readiness_path=plan_readiness_path,
        replay_plan_path=replay_plan_path,
        contract_output_dir=contract_output_dir,
        contract_acceptance_output_dir=contract_acceptance_output_dir,
        readiness_output_dir=readiness_output_dir,
        min_requests=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )
    outputs = write_adapter_readiness_report(report, readiness_output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run no-execution paper strategy adapter readiness gate."
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
        "--contract-output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_contract",
    )
    parser.add_argument(
        "--contract-acceptance-output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_contract_acceptance"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_readiness",
    )
    parser.add_argument("--min-requests", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_readiness_report(
        plan_readiness_path=Path(args.plan_readiness),
        replay_plan_path=Path(args.replay_plan),
        contract_output_dir=Path(args.contract_output_dir),
        contract_acceptance_output_dir=Path(args.contract_acceptance_output_dir),
        readiness_output_dir=Path(args.output_dir),
        min_requests=args.min_requests,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data paper strategy adapter readiness completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future adapter dry-run: {report.ready_for_future_adapter_dry_run}")
    print(f"Adapter readiness report: {outputs['paper_strategy_adapter_readiness_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
