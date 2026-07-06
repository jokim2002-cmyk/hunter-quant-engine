"""
Paper Backtest Evidence Runner

Builds a local evidence report from paper trading session output.

This module is paper/simulation only.
No broker code. No real orders. No live market data.
This is not a profitability claim.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.paper_trading.paper_trading_session import PaperTradingSession
from src.paper_trading.paper_trading_session_summary import (
    PaperTradingSessionSummary,
    build_paper_trading_session_summary,
)


DEFAULT_PAPER_BACKTEST_EVIDENCE_OUTPUT_DIR = (
    Path("reports") / "paper_trading" / "evidence"
)


@dataclass(frozen=True)
class PaperBacktestEvidenceThresholds:
    """
    Safety thresholds for deciding whether paper evidence is acceptable.
    """

    min_closed_trades: int = 1
    max_open_positions: int = 0
    max_unknown_trades: int = 0
    min_simulated_net_pnl: float | None = None


@dataclass(frozen=True)
class PaperBacktestEvidencePaths:
    """
    Files written by the paper evidence runner.
    """

    output_dir: Path
    evidence_json: Path
    evidence_text: Path
    manifest_json: Path


@dataclass(frozen=True)
class PaperBacktestEvidenceReport:
    """
    Paper evidence report with pass/fail gates.
    """

    generated_at: str
    evidence_version: int
    evidence_source: str
    paper_evidence_is_simulation_only: bool
    no_broker_orders: bool
    no_live_market_data: bool
    no_real_orders: bool
    not_a_profitability_claim: bool
    total_orders: int
    open_positions: int
    closed_trades: int
    exit_records: int
    simulated_gross_pnl: float | None
    estimated_costs: float | None
    simulated_net_pnl: float | None
    winning_trades: int | None
    losing_trades: int | None
    flat_trades: int | None
    unknown_trades: int | None
    thresholds: PaperBacktestEvidenceThresholds
    passed: bool
    blocking_reasons: tuple[str, ...]


def run_paper_backtest_evidence(
    session: PaperTradingSession,
    *,
    output_dir: str | Path = DEFAULT_PAPER_BACKTEST_EVIDENCE_OUTPUT_DIR,
    thresholds: PaperBacktestEvidenceThresholds = PaperBacktestEvidenceThresholds(),
    generated_at: datetime | None = None,
) -> tuple[PaperBacktestEvidenceReport, PaperBacktestEvidencePaths]:
    """
    Build and write a local paper evidence report from a paper trading session.
    """
    summary = build_paper_trading_session_summary(session)
    report = build_paper_backtest_evidence_report(
        summary,
        thresholds=thresholds,
        generated_at=generated_at,
    )
    paths = write_paper_backtest_evidence_report(report, output_dir)
    return report, paths


def build_paper_backtest_evidence_report(
    summary: PaperTradingSessionSummary,
    *,
    thresholds: PaperBacktestEvidenceThresholds = PaperBacktestEvidenceThresholds(),
    generated_at: datetime | None = None,
) -> PaperBacktestEvidenceReport:
    """
    Build a paper evidence report from a paper trading summary.
    """
    generated = generated_at or datetime.now(timezone.utc)

    total_orders = _int_metric(summary, "total_orders")
    open_positions = _int_metric(summary, "open_positions_count", "open_positions")
    closed_trades = _int_metric(summary, "closed_trades_count", "closed_trades")
    exit_records = _int_metric(summary, "exit_records_count", "exit_records")

    simulated_gross_pnl = _float_metric(
        summary,
        "total_simulated_gross_pnl",
        "simulated_gross_pnl",
    )
    estimated_costs = _float_metric(
        summary,
        "total_estimated_costs",
        "estimated_costs",
    )
    simulated_net_pnl = _float_metric(
        summary,
        "total_simulated_net_pnl",
        "simulated_net_pnl",
    )

    winning_trades = _optional_int_metric(
        summary,
        "net_winning_trades",
        "winning_trades",
    )
    losing_trades = _optional_int_metric(
        summary,
        "net_losing_trades",
        "losing_trades",
    )
    flat_trades = _optional_int_metric(
        summary,
        "net_flat_trades",
        "flat_trades",
    )
    unknown_trades = _optional_int_metric(
        summary,
        "net_unknown_trades",
        "unknown_trades",
    )

    blocking_reasons = _build_blocking_reasons(
        closed_trades=closed_trades,
        open_positions=open_positions,
        unknown_trades=unknown_trades,
        simulated_net_pnl=simulated_net_pnl,
        thresholds=thresholds,
    )

    return PaperBacktestEvidenceReport(
        generated_at=generated.isoformat(),
        evidence_version=1,
        evidence_source="paper_backtest",
        paper_evidence_is_simulation_only=True,
        no_broker_orders=True,
        no_live_market_data=True,
        no_real_orders=True,
        not_a_profitability_claim=True,
        total_orders=total_orders,
        open_positions=open_positions,
        closed_trades=closed_trades,
        exit_records=exit_records,
        simulated_gross_pnl=simulated_gross_pnl,
        estimated_costs=estimated_costs,
        simulated_net_pnl=simulated_net_pnl,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        flat_trades=flat_trades,
        unknown_trades=unknown_trades,
        thresholds=thresholds,
        passed=not blocking_reasons,
        blocking_reasons=tuple(blocking_reasons),
    )


def write_paper_backtest_evidence_report(
    report: PaperBacktestEvidenceReport,
    output_dir: str | Path = DEFAULT_PAPER_BACKTEST_EVIDENCE_OUTPUT_DIR,
) -> PaperBacktestEvidencePaths:
    """
    Write evidence JSON, text, and manifest files under reports/.
    """
    safe_output_dir = _ensure_reports_output_dir(output_dir)
    safe_output_dir.mkdir(parents=True, exist_ok=True)

    paths = PaperBacktestEvidencePaths(
        output_dir=safe_output_dir,
        evidence_json=safe_output_dir / "evidence.json",
        evidence_text=safe_output_dir / "evidence.txt",
        manifest_json=safe_output_dir / "manifest.json",
    )

    report_payload = paper_backtest_evidence_report_to_dict(report)
    _write_json(paths.evidence_json, report_payload)
    paths.evidence_text.write_text(
        format_paper_backtest_evidence_report(report),
        encoding="utf-8",
    )
    _write_json(paths.manifest_json, paper_backtest_evidence_manifest_to_dict(paths))

    return paths


def paper_backtest_evidence_report_to_dict(
    report: PaperBacktestEvidenceReport,
) -> dict[str, Any]:
    """
    Convert an evidence report to JSON-safe dict form.
    """
    payload = asdict(report)
    payload["blocking_reasons"] = list(report.blocking_reasons)
    return payload


def paper_backtest_evidence_manifest_to_dict(
    paths: PaperBacktestEvidencePaths,
) -> dict[str, Any]:
    """
    Convert evidence paths to manifest dict form.
    """
    return {
        "manifest_version": 1,
        "manifest_source": "paper_backtest_evidence",
        "paper_evidence_is_simulation_only": True,
        "output_dir": str(paths.output_dir),
        "files": {
            "evidence_json": str(paths.evidence_json),
            "evidence_text": str(paths.evidence_text),
            "manifest_json": str(paths.manifest_json),
        },
    }


def format_paper_backtest_evidence_report(
    report: PaperBacktestEvidenceReport,
) -> str:
    """
    Format an evidence report for terminal/text output.
    """
    lines = [
        "Hunter Quant Engine - Paper Backtest Evidence",
        "paper/simulation only",
        "no broker",
        "no live market data",
        "no real orders",
        "not a profitability claim",
        "",
        f"generated at: {report.generated_at}",
        f"passed gates: {report.passed}",
        "",
        "Activity",
        f"total orders: {report.total_orders}",
        f"open positions: {report.open_positions}",
        f"closed trades: {report.closed_trades}",
        f"exit records: {report.exit_records}",
        "",
        "Simulated PnL",
        f"gross pnl: {_format_optional(report.simulated_gross_pnl)}",
        f"estimated costs: {_format_optional(report.estimated_costs)}",
        f"net pnl: {_format_optional(report.simulated_net_pnl)}",
        "",
        "Result Counts",
        f"wins: {_format_optional(report.winning_trades)}",
        f"losses: {_format_optional(report.losing_trades)}",
        f"flat: {_format_optional(report.flat_trades)}",
        f"unknown: {_format_optional(report.unknown_trades)}",
        "",
        "Blocking Reasons",
    ]

    if report.blocking_reasons:
        lines.extend(f"- {reason}" for reason in report.blocking_reasons)
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def _build_blocking_reasons(
    *,
    closed_trades: int,
    open_positions: int,
    unknown_trades: int | None,
    simulated_net_pnl: float | None,
    thresholds: PaperBacktestEvidenceThresholds,
) -> list[str]:
    reasons: list[str] = []

    if closed_trades < thresholds.min_closed_trades:
        reasons.append(
            "closed trades below minimum: "
            f"{closed_trades} < {thresholds.min_closed_trades}"
        )

    if open_positions > thresholds.max_open_positions:
        reasons.append(
            "open positions above maximum: "
            f"{open_positions} > {thresholds.max_open_positions}"
        )

    if unknown_trades is not None and unknown_trades > thresholds.max_unknown_trades:
        reasons.append(
            "unknown trades above maximum: "
            f"{unknown_trades} > {thresholds.max_unknown_trades}"
        )

    if thresholds.min_simulated_net_pnl is not None:
        if simulated_net_pnl is None:
            reasons.append("simulated net pnl is unavailable")
        elif simulated_net_pnl < thresholds.min_simulated_net_pnl:
            reasons.append(
                "simulated net pnl below minimum: "
                f"{simulated_net_pnl} < {thresholds.min_simulated_net_pnl}"
            )

    return reasons


def _int_metric(summary: PaperTradingSessionSummary, *names: str) -> int:
    value = _first_metric(summary, names, 0)
    return int(value)


def _optional_int_metric(
    summary: PaperTradingSessionSummary,
    *names: str,
) -> int | None:
    value = _first_metric(summary, names, None)
    if value is None:
        return None
    return int(value)


def _float_metric(summary: PaperTradingSessionSummary, *names: str) -> float | None:
    value = _first_metric(summary, names, None)
    if value is None:
        return None
    return float(value)


def _first_metric(
    summary: PaperTradingSessionSummary,
    names: tuple[str, ...],
    default: Any,
) -> Any:
    for name in names:
        if hasattr(summary, name):
            return getattr(summary, name)
    return default


def _format_optional(value: Any) -> str:
    if value is None:
        return "unknown"
    return str(value)


def _ensure_reports_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    parts = path.parts

    if "reports" not in parts:
        raise ValueError("paper backtest evidence output must be under reports/")

    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
