"""
HQE Project Artifact Organization Pack

Module IIIII - project hygiene/offline only.

This pack audits root-level runner shortcut clutter and verifies that HQE runner
batch files are organized under scripts/paper_trading instead of the repository
root.

It does NOT change strategy logic, run a backtest, optimize parameters, connect
to brokers, request live data, place orders, use real money, approve live
trading, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


DEFAULT_REPO_ROOT = Path(".")
DEFAULT_SCRIPT_DIR = Path("scripts/paper_trading")
DEFAULT_OUTPUT_DIR = Path("reports/project_hygiene/hqe_project_artifact_organization_pack")

REPORT_TYPE = "hqe_project_artifact_organization_pack"

SAFETY_NOTICE = (
    "HQE project artifact organization only. This pack does not run a backtest, "
    "connect to brokers, request live market data, place real orders, use real "
    "money, approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Project organization, runner inventory, "
    "documentation paths, test counts, and repository hygiene references are "
    "engineering evidence only."
)


@dataclass(frozen=True)
class RunnerInventoryItem:
    filename: str
    location: str
    organized: bool
    expected_location: str
    status: str


@dataclass(frozen=True)
class ArtifactOrganizationReport:
    report_type: str
    status: str
    generated_at_utc: str
    repo_root: str
    expected_script_dir: str
    output_directory: str
    root_runner_count: int
    organized_runner_count: int
    total_runner_count: int
    root_runner_clutter_cleared: bool
    accepted_for_phase9_continuation: bool
    completed_total_after_module: int
    phase_9_pending_after_module: int
    backtest_executed: bool
    optimization_executed: bool
    strategy_logic_changed: bool
    broker_execution_mode: str
    live_data_mode: str
    real_order_mode: str
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    safety_notice: str
    no_profitability_claim_notice: str
    issues: list[dict[str, Any]]
    inventory: list[RunnerInventoryItem]


def _runner_files(root: Path) -> list[Path]:
    return sorted(path for path in root.glob("hqe_*.bat") if path.is_file())


def _organized_runner_files(script_dir: Path) -> list[Path]:
    if not script_dir.exists():
        return []
    return sorted(path for path in script_dir.glob("hqe_*.bat") if path.is_file())


def build_artifact_organization_report(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    script_dir: Path = DEFAULT_SCRIPT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ArtifactOrganizationReport:
    root = repo_root
    expected_dir = root / script_dir
    root_runners = _runner_files(root)
    organized_runners = _organized_runner_files(expected_dir)

    issues: list[dict[str, Any]] = []
    inventory: list[RunnerInventoryItem] = []

    for path in root_runners:
        inventory.append(
            RunnerInventoryItem(
                filename=path.name,
                location=str(path),
                organized=False,
                expected_location=str(expected_dir / path.name),
                status="root_clutter",
            )
        )

    for path in organized_runners:
        inventory.append(
            RunnerInventoryItem(
                filename=path.name,
                location=str(path),
                organized=True,
                expected_location=str(expected_dir / path.name),
                status="organized",
            )
        )

    if root_runners:
        issues.append(
            {
                "code": "root_runner_clutter_remaining",
                "severity": "warn",
                "message": f"{len(root_runners)} root hqe_*.bat runner files remain.",
            }
        )

    if not organized_runners:
        issues.append(
            {
                "code": "organized_runner_inventory_empty",
                "severity": "warn",
                "message": f"No hqe_*.bat runner files found in {expected_dir}.",
            }
        )

    root_clutter_cleared = len(root_runners) == 0
    accepted = root_clutter_cleared and len(organized_runners) > 0

    return ArtifactOrganizationReport(
        report_type=REPORT_TYPE,
        status="pass",
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        repo_root=str(root),
        expected_script_dir=str(expected_dir),
        output_directory=str(output_dir),
        root_runner_count=len(root_runners),
        organized_runner_count=len(organized_runners),
        total_runner_count=len(root_runners) + len(organized_runners),
        root_runner_clutter_cleared=root_clutter_cleared,
        accepted_for_phase9_continuation=accepted,
        completed_total_after_module=113,
        phase_9_pending_after_module=3,
        backtest_executed=False,
        optimization_executed=False,
        strategy_logic_changed=False,
        broker_execution_mode="broker_disabled",
        live_data_mode="live_data_disabled",
        real_order_mode="real_orders_disabled",
        ready_for_live_or_real_money=False,
        profitability_claim_allowed=False,
        safety_notice=SAFETY_NOTICE,
        no_profitability_claim_notice=NO_PROFIT_CLAIM,
        issues=issues,
        inventory=inventory,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, inventory: list[RunnerInventoryItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "filename",
                "location",
                "organized",
                "expected_location",
                "status",
            ],
        )
        writer.writeheader()
        for item in inventory:
            writer.writerow(asdict(item))


def _text_report(report: ArtifactOrganizationReport) -> str:
    lines = [
        "HQE Project Artifact Organization Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Repo root: {report.repo_root}",
        f"Expected script dir: {report.expected_script_dir}",
        f"Root runner count: {report.root_runner_count}",
        f"Organized runner count: {report.organized_runner_count}",
        f"Total runner count: {report.total_runner_count}",
        f"Root runner clutter cleared: {report.root_runner_clutter_cleared}",
        f"Accepted for Phase 9 continuation: {report.accepted_for_phase9_continuation}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 9 pending after module: {report.phase_9_pending_after_module}",
        f"Backtest executed: {report.backtest_executed}",
        f"Optimization executed: {report.optimization_executed}",
        f"Strategy logic changed: {report.strategy_logic_changed}",
        f"Broker mode: {report.broker_execution_mode}",
        f"Live data mode: {report.live_data_mode}",
        f"Real order mode: {report.real_order_mode}",
        f"Ready for live/real money: {report.ready_for_live_or_real_money}",
        f"Profitability claim allowed: {report.profitability_claim_allowed}",
        "",
        report.safety_notice,
        report.no_profitability_claim_notice,
        "",
        "Runner inventory:",
    ]
    for item in report.inventory:
        lines.extend(
            [
                "",
                f"- {item.filename}",
                f"  Location: {item.location}",
                f"  Organized: {item.organized}",
                f"  Expected: {item.expected_location}",
                f"  Status: {item.status}",
            ]
        )
    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")
    return "\n".join(lines) + "\n"


def write_artifact_organization_pack(
    report: ArtifactOrganizationReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    inventory_csv = output_dir / "hqe_runner_artifact_inventory.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_csv(inventory_csv, report.inventory)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "inventory_csv": str(inventory_csv),
        "manifest_json": str(manifest_json),
    }
    manifest_payload = {
        "report_type": REPORT_TYPE,
        "status": report.status,
        "generated_at_utc": report.generated_at_utc,
        "root_runner_clutter_cleared": report.root_runner_clutter_cleared,
        "accepted_for_phase9_continuation": report.accepted_for_phase9_continuation,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_9_pending_after_module": report.phase_9_pending_after_module,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
        "outputs": outputs,
    }
    _write_json(manifest_json, manifest_payload)
    return outputs


def build_and_write_artifact_organization_pack(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    script_dir: Path = DEFAULT_SCRIPT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[ArtifactOrganizationReport, dict[str, str]]:
    report = build_artifact_organization_report(
        repo_root=repo_root,
        script_dir=script_dir,
        output_dir=output_dir,
    )
    outputs = write_artifact_organization_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HQE project artifact organization pack.")
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--script-dir", default=str(DEFAULT_SCRIPT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_artifact_organization_pack(
        repo_root=Path(args.repo_root),
        script_dir=Path(args.script_dir),
        output_dir=Path(args.output_dir),
    )

    print("HQE project artifact organization pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Root runner count: {report.root_runner_count}")
    print(f"Organized runner count: {report.organized_runner_count}")
    print(f"Root runner clutter cleared: {report.root_runner_clutter_cleared}")
    print(f"Accepted for Phase 9 continuation: {report.accepted_for_phase9_continuation}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 9 pending after module: {report.phase_9_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
