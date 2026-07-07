"""
Live Readiness Preflight

Runs the safe local live-readiness preflight chain:

paper MVP operator demo -> evidence aggregate -> live-readiness gate
-> live safety lock -> final preflight report

This is not live trading.
No broker code. No live market data. No real orders.
Real money remains disabled.
This is not a profitability claim.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.paper_trading.live_readiness_gate import (
    LiveReadinessPaths,
    LiveReadinessReport,
    run_live_readiness_gate,
)
from src.paper_trading.live_safety_lock import (
    LiveSafetyLockPaths,
    LiveSafetyLockReport,
    run_live_safety_lock,
)
from src.paper_trading.paper_evidence_aggregate import (
    PaperEvidenceAggregatePaths,
    PaperEvidenceAggregateReport,
    run_paper_evidence_aggregate,
)
from src.paper_trading.paper_mvp_operator_demo_cli import (
    PaperMvpOperatorDemoResult,
    run_paper_mvp_operator_demo,
)


DEFAULT_LIVE_READINESS_PREFLIGHT_OUTPUT_ROOT = (
    Path("reports") / "paper_trading"
)
DEFAULT_LIVE_READINESS_PREFLIGHT_OUTPUT_DIR = (
    DEFAULT_LIVE_READINESS_PREFLIGHT_OUTPUT_ROOT / "live_readiness_preflight"
)


@dataclass(frozen=True)
class LiveReadinessPreflightPaths:
    """
    Files written by the live-readiness preflight.
    """

    output_dir: Path
    preflight_json: Path
    preflight_text: Path
    manifest_json: Path
    operator_demo_output_dir: Path
    evidence_aggregate_output_dir: Path
    live_readiness_output_dir: Path
    live_safety_lock_output_dir: Path


@dataclass(frozen=True)
class LiveReadinessPreflightReport:
    """
    Final safe local preflight report.

    preflight_passed means the local safe gates passed.
    It does not mean live trading is approved.
    """

    generated_at: str
    preflight_version: int
    preflight_source: str
    preflight_passed: bool
    live_trading_approved: bool
    real_money_enabled: bool
    broker_execution_enabled: bool
    live_market_data_enabled: bool
    real_orders_enabled: bool
    not_a_profitability_claim: bool
    operator_demo_passed: bool
    evidence_aggregate_passed: bool
    live_readiness_allowed: bool
    live_safety_lock_passed: bool
    paper_closed_trades: int
    aggregate_report_count: int
    aggregate_total_closed_trades: int
    aggregate_total_simulated_net_pnl: float
    blocking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class LiveReadinessPreflightResult:
    """
    Full result bundle for the live-readiness preflight.
    """

    operator_demo_result: PaperMvpOperatorDemoResult
    evidence_aggregate_report: PaperEvidenceAggregateReport
    evidence_aggregate_paths: PaperEvidenceAggregatePaths
    live_readiness_report: LiveReadinessReport
    live_readiness_paths: LiveReadinessPaths
    live_safety_lock_report: LiveSafetyLockReport
    live_safety_lock_paths: LiveSafetyLockPaths
    preflight_report: LiveReadinessPreflightReport
    preflight_paths: LiveReadinessPreflightPaths


def run_live_readiness_preflight(
    *,
    output_root: str | Path = DEFAULT_LIVE_READINESS_PREFLIGHT_OUTPUT_ROOT,
    generated_at: datetime | None = None,
) -> LiveReadinessPreflightResult:
    """
    Run the complete safe local live-readiness preflight.
    """
    safe_output_root = _ensure_reports_output_dir(output_root)
    generated = generated_at or datetime.now(timezone.utc)

    operator_demo_dir = safe_output_root / "operator_demo"
    evidence_aggregate_dir = safe_output_root / "evidence_aggregate"
    live_readiness_dir = safe_output_root / "live_readiness"
    live_safety_lock_dir = safe_output_root / "live_safety_lock"
    preflight_dir = safe_output_root / "live_readiness_preflight"

    operator_demo_result = run_paper_mvp_operator_demo(
        output_dir=operator_demo_dir,
        generated_at=generated,
    )

    aggregate_report, aggregate_paths = run_paper_evidence_aggregate(
        [operator_demo_result.evidence_paths.evidence_json],
        output_dir=evidence_aggregate_dir,
        generated_at=generated,
    )

    readiness_report, readiness_paths = run_live_readiness_gate(
        aggregate_paths.aggregate_json,
        output_dir=live_readiness_dir,
        generated_at=generated,
    )

    safety_report, safety_paths = run_live_safety_lock(
        output_dir=live_safety_lock_dir,
        generated_at=generated,
    )

    preflight_report = build_live_readiness_preflight_report(
        operator_demo_result=operator_demo_result,
        evidence_aggregate_report=aggregate_report,
        live_readiness_report=readiness_report,
        live_safety_lock_report=safety_report,
        generated_at=generated,
    )

    preflight_paths = write_live_readiness_preflight_report(
        preflight_report,
        output_dir=preflight_dir,
        operator_demo_output_dir=operator_demo_dir,
        evidence_aggregate_output_dir=evidence_aggregate_dir,
        live_readiness_output_dir=live_readiness_dir,
        live_safety_lock_output_dir=live_safety_lock_dir,
    )

    return LiveReadinessPreflightResult(
        operator_demo_result=operator_demo_result,
        evidence_aggregate_report=aggregate_report,
        evidence_aggregate_paths=aggregate_paths,
        live_readiness_report=readiness_report,
        live_readiness_paths=readiness_paths,
        live_safety_lock_report=safety_report,
        live_safety_lock_paths=safety_paths,
        preflight_report=preflight_report,
        preflight_paths=preflight_paths,
    )


def build_live_readiness_preflight_report(
    *,
    operator_demo_result: PaperMvpOperatorDemoResult,
    evidence_aggregate_report: PaperEvidenceAggregateReport,
    live_readiness_report: LiveReadinessReport,
    live_safety_lock_report: LiveSafetyLockReport,
    generated_at: datetime | None = None,
) -> LiveReadinessPreflightReport:
    """
    Build the final preflight report from stage results.
    """
    generated = generated_at or datetime.now(timezone.utc)

    operator_demo_passed = (
        operator_demo_result.evidence_report.passed
        and operator_demo_result.bridge_result.summary.closed_trades_count >= 1
        and operator_demo_result.bridge_result.summary.open_positions_count == 0
    )
    evidence_aggregate_passed = evidence_aggregate_report.passed
    live_readiness_allowed = live_readiness_report.live_readiness_allowed
    live_safety_lock_passed = live_safety_lock_report.safety_lock_passed

    blocking_reasons = _build_blocking_reasons(
        operator_demo_passed=operator_demo_passed,
        evidence_aggregate_passed=evidence_aggregate_passed,
        live_readiness_allowed=live_readiness_allowed,
        live_safety_lock_passed=live_safety_lock_passed,
        live_readiness_report=live_readiness_report,
        live_safety_lock_report=live_safety_lock_report,
    )

    return LiveReadinessPreflightReport(
        generated_at=generated.isoformat(),
        preflight_version=1,
        preflight_source="live_readiness_preflight",
        preflight_passed=not blocking_reasons,
        live_trading_approved=False,
        real_money_enabled=False,
        broker_execution_enabled=False,
        live_market_data_enabled=False,
        real_orders_enabled=False,
        not_a_profitability_claim=True,
        operator_demo_passed=operator_demo_passed,
        evidence_aggregate_passed=evidence_aggregate_passed,
        live_readiness_allowed=live_readiness_allowed,
        live_safety_lock_passed=live_safety_lock_passed,
        paper_closed_trades=operator_demo_result.bridge_result.summary.closed_trades_count,
        aggregate_report_count=evidence_aggregate_report.report_count,
        aggregate_total_closed_trades=evidence_aggregate_report.total_closed_trades,
        aggregate_total_simulated_net_pnl=(
            evidence_aggregate_report.total_simulated_net_pnl
        ),
        blocking_reasons=tuple(blocking_reasons),
    )


def write_live_readiness_preflight_report(
    report: LiveReadinessPreflightReport,
    *,
    output_dir: str | Path = DEFAULT_LIVE_READINESS_PREFLIGHT_OUTPUT_DIR,
    operator_demo_output_dir: str | Path,
    evidence_aggregate_output_dir: str | Path,
    live_readiness_output_dir: str | Path,
    live_safety_lock_output_dir: str | Path,
) -> LiveReadinessPreflightPaths:
    """
    Write final preflight output files under reports/.
    """
    safe_output_dir = _ensure_reports_output_dir(output_dir)
    safe_output_dir.mkdir(parents=True, exist_ok=True)

    paths = LiveReadinessPreflightPaths(
        output_dir=safe_output_dir,
        preflight_json=safe_output_dir / "preflight.json",
        preflight_text=safe_output_dir / "preflight.txt",
        manifest_json=safe_output_dir / "manifest.json",
        operator_demo_output_dir=Path(operator_demo_output_dir),
        evidence_aggregate_output_dir=Path(evidence_aggregate_output_dir),
        live_readiness_output_dir=Path(live_readiness_output_dir),
        live_safety_lock_output_dir=Path(live_safety_lock_output_dir),
    )

    _write_json(paths.preflight_json, live_readiness_preflight_report_to_dict(report))
    paths.preflight_text.write_text(
        format_live_readiness_preflight_report(report),
        encoding="utf-8",
    )
    _write_json(paths.manifest_json, live_readiness_preflight_manifest_to_dict(paths))

    return paths


def live_readiness_preflight_report_to_dict(
    report: LiveReadinessPreflightReport,
) -> dict[str, Any]:
    """
    Convert preflight report to JSON-safe dict.
    """
    payload = asdict(report)
    payload["blocking_reasons"] = list(report.blocking_reasons)
    return payload


def live_readiness_preflight_manifest_to_dict(
    paths: LiveReadinessPreflightPaths,
) -> dict[str, Any]:
    """
    Convert preflight output paths to manifest form.
    """
    return {
        "manifest_version": 1,
        "manifest_source": "live_readiness_preflight",
        "live_trading_approved": False,
        "real_money_enabled": False,
        "broker_execution_enabled": False,
        "files": {
            "preflight_json": str(paths.preflight_json),
            "preflight_text": str(paths.preflight_text),
            "manifest_json": str(paths.manifest_json),
        },
        "stage_output_dirs": {
            "operator_demo": str(paths.operator_demo_output_dir),
            "evidence_aggregate": str(paths.evidence_aggregate_output_dir),
            "live_readiness": str(paths.live_readiness_output_dir),
            "live_safety_lock": str(paths.live_safety_lock_output_dir),
        },
    }


def format_live_readiness_preflight_report(
    report: LiveReadinessPreflightReport,
) -> str:
    """
    Format final preflight output for terminal/text display.
    """
    lines = [
        "Hunter Quant Engine - Live Readiness Preflight",
        "safe local preflight only",
        "this is not live trading",
        "real money disabled",
        "broker execution disabled",
        "live market data disabled",
        "real orders disabled",
        "not a profitability claim",
        "",
        f"generated at: {report.generated_at}",
        f"preflight passed: {report.preflight_passed}",
        f"live trading approved: {report.live_trading_approved}",
        "",
        "Stage Results",
        f"operator demo passed: {report.operator_demo_passed}",
        f"evidence aggregate passed: {report.evidence_aggregate_passed}",
        f"live-readiness allowed: {report.live_readiness_allowed}",
        f"live safety lock passed: {report.live_safety_lock_passed}",
        "",
        "Evidence Summary",
        f"paper closed trades: {report.paper_closed_trades}",
        f"aggregate report count: {report.aggregate_report_count}",
        f"aggregate closed trades: {report.aggregate_total_closed_trades}",
        f"aggregate simulated net pnl: {report.aggregate_total_simulated_net_pnl}",
        "",
        "Danger Flags",
        f"real money enabled: {report.real_money_enabled}",
        f"broker execution enabled: {report.broker_execution_enabled}",
        f"live market data enabled: {report.live_market_data_enabled}",
        f"real orders enabled: {report.real_orders_enabled}",
        "",
        "Blocking Reasons",
    ]

    if report.blocking_reasons:
        lines.extend(f"- {reason}" for reason in report.blocking_reasons)
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def main() -> int:
    """
    CLI entrypoint.
    """
    result = run_live_readiness_preflight()
    print(format_live_readiness_preflight_report(result.preflight_report), end="")
    print(f"preflight json: {result.preflight_paths.preflight_json}")
    print(f"preflight text: {result.preflight_paths.preflight_text}")
    return 0 if result.preflight_report.preflight_passed else 1


def _build_blocking_reasons(
    *,
    operator_demo_passed: bool,
    evidence_aggregate_passed: bool,
    live_readiness_allowed: bool,
    live_safety_lock_passed: bool,
    live_readiness_report: LiveReadinessReport,
    live_safety_lock_report: LiveSafetyLockReport,
) -> list[str]:
    reasons: list[str] = []

    if not operator_demo_passed:
        reasons.append("paper MVP operator demo did not pass")

    if not evidence_aggregate_passed:
        reasons.append("paper evidence aggregate did not pass")

    if not live_readiness_allowed:
        reasons.append("live-readiness gate did not allow engineering")
        reasons.extend(live_readiness_report.blocking_reasons)

    if not live_safety_lock_passed:
        reasons.append("live safety lock did not pass")
        reasons.extend(live_safety_lock_report.blocking_reasons)

    return reasons


def _ensure_reports_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    if "reports" not in path.parts:
        raise ValueError("live-readiness preflight output must be under reports/")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
