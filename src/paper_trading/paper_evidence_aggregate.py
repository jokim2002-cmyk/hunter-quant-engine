"""
Paper Evidence Aggregate

Aggregates one or more paper evidence JSON reports into a single safety-gated
evidence summary.

Paper/simulation only.
No broker code. No real orders. No live market data.
This is not a profitability claim.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


DEFAULT_PAPER_EVIDENCE_INPUT_PATHS = (
    Path("reports") / "paper_trading" / "operator_demo" / "evidence" / "evidence.json",
)
DEFAULT_PAPER_EVIDENCE_AGGREGATE_OUTPUT_DIR = (
    Path("reports") / "paper_trading" / "evidence_aggregate"
)


@dataclass(frozen=True)
class PaperEvidenceAggregateThresholds:
    """
    Safety thresholds for aggregated paper evidence.
    """

    min_evidence_reports: int = 1
    min_total_closed_trades: int = 1
    max_total_open_positions: int = 0
    max_total_unknown_trades: int = 0
    min_total_simulated_net_pnl: float | None = None
    require_all_reports_passed: bool = True


@dataclass(frozen=True)
class PaperEvidenceAggregatePaths:
    """
    Files written by the paper evidence aggregate runner.
    """

    output_dir: Path
    aggregate_json: Path
    aggregate_text: Path
    manifest_json: Path


@dataclass(frozen=True)
class PaperEvidenceAggregateReport:
    """
    Aggregated paper evidence report.
    """

    generated_at: str
    aggregate_version: int
    aggregate_source: str
    paper_evidence_is_simulation_only: bool
    no_broker_orders: bool
    no_live_market_data: bool
    no_real_orders: bool
    not_a_profitability_claim: bool
    source_files: tuple[str, ...]
    report_count: int
    all_reports_passed: bool
    total_orders: int
    total_open_positions: int
    total_closed_trades: int
    total_exit_records: int
    total_unknown_trades: int
    total_simulated_gross_pnl: float
    total_estimated_costs: float
    total_simulated_net_pnl: float
    thresholds: PaperEvidenceAggregateThresholds
    passed: bool
    blocking_reasons: tuple[str, ...]


def run_paper_evidence_aggregate(
    evidence_json_paths: Iterable[str | Path] = DEFAULT_PAPER_EVIDENCE_INPUT_PATHS,
    *,
    output_dir: str | Path = DEFAULT_PAPER_EVIDENCE_AGGREGATE_OUTPUT_DIR,
    thresholds: PaperEvidenceAggregateThresholds = PaperEvidenceAggregateThresholds(),
    generated_at: datetime | None = None,
) -> tuple[PaperEvidenceAggregateReport, PaperEvidenceAggregatePaths]:
    """
    Load paper evidence files, aggregate them, and write aggregate outputs.
    """
    paths = tuple(Path(path) for path in evidence_json_paths)
    payloads = tuple(load_paper_evidence_json(path) for path in paths)
    report = build_paper_evidence_aggregate_report(
        payloads,
        source_paths=paths,
        thresholds=thresholds,
        generated_at=generated_at,
    )
    output_paths = write_paper_evidence_aggregate_report(report, output_dir)
    return report, output_paths


def load_paper_evidence_json(path: str | Path) -> dict[str, Any]:
    """
    Load one paper evidence JSON report.
    """
    evidence_path = Path(path)
    if not evidence_path.exists():
        raise FileNotFoundError(
            f"paper evidence JSON not found: {evidence_path}. "
            "Run hqe_paper_mvp_operator_demo.bat first."
        )

    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("paper evidence JSON must be a JSON object")

    return payload


def build_paper_evidence_aggregate_report(
    evidence_payloads: Iterable[Mapping[str, Any]],
    *,
    source_paths: Iterable[str | Path] = (),
    thresholds: PaperEvidenceAggregateThresholds = PaperEvidenceAggregateThresholds(),
    generated_at: datetime | None = None,
) -> PaperEvidenceAggregateReport:
    """
    Build an aggregate paper evidence report from loaded payloads.
    """
    payloads = tuple(evidence_payloads)
    sources = tuple(_format_path(path) for path in source_paths)
    generated = generated_at or datetime.now(timezone.utc)

    report_count = len(payloads)
    all_reports_passed = all(payload.get("passed") is True for payload in payloads)

    total_orders = _sum_int(payloads, "total_orders")
    total_open_positions = _sum_int(payloads, "open_positions")
    total_closed_trades = _sum_int(payloads, "closed_trades")
    total_exit_records = _sum_int(payloads, "exit_records")
    total_unknown_trades = _sum_int(payloads, "unknown_trades")
    total_simulated_gross_pnl = _sum_float(payloads, "simulated_gross_pnl")
    total_estimated_costs = _sum_float(payloads, "estimated_costs")
    total_simulated_net_pnl = _sum_float(payloads, "simulated_net_pnl")

    blocking_reasons = _build_blocking_reasons(
        report_count=report_count,
        all_reports_passed=all_reports_passed,
        total_open_positions=total_open_positions,
        total_closed_trades=total_closed_trades,
        total_unknown_trades=total_unknown_trades,
        total_simulated_net_pnl=total_simulated_net_pnl,
        thresholds=thresholds,
    )

    return PaperEvidenceAggregateReport(
        generated_at=generated.isoformat(),
        aggregate_version=1,
        aggregate_source="paper_evidence_aggregate",
        paper_evidence_is_simulation_only=True,
        no_broker_orders=True,
        no_live_market_data=True,
        no_real_orders=True,
        not_a_profitability_claim=True,
        source_files=sources,
        report_count=report_count,
        all_reports_passed=all_reports_passed,
        total_orders=total_orders,
        total_open_positions=total_open_positions,
        total_closed_trades=total_closed_trades,
        total_exit_records=total_exit_records,
        total_unknown_trades=total_unknown_trades,
        total_simulated_gross_pnl=total_simulated_gross_pnl,
        total_estimated_costs=total_estimated_costs,
        total_simulated_net_pnl=total_simulated_net_pnl,
        thresholds=thresholds,
        passed=not blocking_reasons,
        blocking_reasons=tuple(blocking_reasons),
    )


def write_paper_evidence_aggregate_report(
    report: PaperEvidenceAggregateReport,
    output_dir: str | Path = DEFAULT_PAPER_EVIDENCE_AGGREGATE_OUTPUT_DIR,
) -> PaperEvidenceAggregatePaths:
    """
    Write aggregate JSON, text, and manifest files under reports/.
    """
    safe_output_dir = _ensure_reports_output_dir(output_dir)
    safe_output_dir.mkdir(parents=True, exist_ok=True)

    paths = PaperEvidenceAggregatePaths(
        output_dir=safe_output_dir,
        aggregate_json=safe_output_dir / "aggregate.json",
        aggregate_text=safe_output_dir / "aggregate.txt",
        manifest_json=safe_output_dir / "manifest.json",
    )

    _write_json(paths.aggregate_json, paper_evidence_aggregate_report_to_dict(report))
    paths.aggregate_text.write_text(
        format_paper_evidence_aggregate_report(report),
        encoding="utf-8",
    )
    _write_json(paths.manifest_json, paper_evidence_aggregate_manifest_to_dict(paths))

    return paths


def paper_evidence_aggregate_report_to_dict(
    report: PaperEvidenceAggregateReport,
) -> dict[str, Any]:
    """
    Convert aggregate report to JSON-safe dict form.
    """
    payload = asdict(report)
    payload["source_files"] = list(report.source_files)
    payload["blocking_reasons"] = list(report.blocking_reasons)
    return payload


def paper_evidence_aggregate_manifest_to_dict(
    paths: PaperEvidenceAggregatePaths,
) -> dict[str, Any]:
    """
    Convert aggregate output paths to manifest form.
    """
    return {
        "manifest_version": 1,
        "manifest_source": "paper_evidence_aggregate",
        "paper_evidence_is_simulation_only": True,
        "output_dir": str(paths.output_dir),
        "files": {
            "aggregate_json": str(paths.aggregate_json),
            "aggregate_text": str(paths.aggregate_text),
            "manifest_json": str(paths.manifest_json),
        },
    }


def format_paper_evidence_aggregate_report(
    report: PaperEvidenceAggregateReport,
) -> str:
    """
    Format aggregate evidence for terminal/text output.
    """
    lines = [
        "Hunter Quant Engine - Paper Evidence Aggregate",
        "paper/simulation only",
        "no broker",
        "no live market data",
        "no real orders",
        "not a profitability claim",
        "",
        f"generated at: {report.generated_at}",
        f"passed gates: {report.passed}",
        f"report count: {report.report_count}",
        f"all reports passed: {report.all_reports_passed}",
        "",
        "Totals",
        f"total orders: {report.total_orders}",
        f"open positions: {report.total_open_positions}",
        f"closed trades: {report.total_closed_trades}",
        f"exit records: {report.total_exit_records}",
        f"unknown trades: {report.total_unknown_trades}",
        "",
        "Simulated PnL",
        f"gross pnl: {report.total_simulated_gross_pnl}",
        f"estimated costs: {report.total_estimated_costs}",
        f"net pnl: {report.total_simulated_net_pnl}",
        "",
        "Source Files",
    ]

    if report.source_files:
        lines.extend(f"- {source}" for source in report.source_files)
    else:
        lines.append("- none")

    lines.append("")
    lines.append("Blocking Reasons")

    if report.blocking_reasons:
        lines.extend(f"- {reason}" for reason in report.blocking_reasons)
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def main() -> int:
    """
    CLI entrypoint.
    """
    try:
        report, paths = run_paper_evidence_aggregate()
    except FileNotFoundError as error:
        print(f"ERROR: {error}")
        return 1

    print(format_paper_evidence_aggregate_report(report), end="")
    print(f"aggregate json: {paths.aggregate_json}")
    print(f"aggregate text: {paths.aggregate_text}")
    return 0 if report.passed else 1


def _build_blocking_reasons(
    *,
    report_count: int,
    all_reports_passed: bool,
    total_open_positions: int,
    total_closed_trades: int,
    total_unknown_trades: int,
    total_simulated_net_pnl: float,
    thresholds: PaperEvidenceAggregateThresholds,
) -> list[str]:
    reasons: list[str] = []

    if report_count < thresholds.min_evidence_reports:
        reasons.append(
            "evidence reports below minimum: "
            f"{report_count} < {thresholds.min_evidence_reports}"
        )

    if thresholds.require_all_reports_passed and not all_reports_passed:
        reasons.append("one or more evidence reports failed their gates")

    if total_closed_trades < thresholds.min_total_closed_trades:
        reasons.append(
            "closed trades below minimum: "
            f"{total_closed_trades} < {thresholds.min_total_closed_trades}"
        )

    if total_open_positions > thresholds.max_total_open_positions:
        reasons.append(
            "open positions above maximum: "
            f"{total_open_positions} > {thresholds.max_total_open_positions}"
        )

    if total_unknown_trades > thresholds.max_total_unknown_trades:
        reasons.append(
            "unknown trades above maximum: "
            f"{total_unknown_trades} > {thresholds.max_total_unknown_trades}"
        )

    if thresholds.min_total_simulated_net_pnl is not None:
        if total_simulated_net_pnl < thresholds.min_total_simulated_net_pnl:
            reasons.append(
                "simulated net pnl below minimum: "
                f"{total_simulated_net_pnl} < {thresholds.min_total_simulated_net_pnl}"
            )

    return reasons


def _sum_int(payloads: tuple[Mapping[str, Any], ...], key: str) -> int:
    total = 0
    for payload in payloads:
        value = payload.get(key)
        if value is None:
            continue
        total += int(value)
    return total


def _sum_float(payloads: tuple[Mapping[str, Any], ...], key: str) -> float:
    total = 0.0
    for payload in payloads:
        value = payload.get(key)
        if value is None:
            continue
        total += float(value)
    return total


def _format_path(path: str | Path) -> str:
    return Path(path).as_posix()


def _ensure_reports_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    if "reports" not in path.parts:
        raise ValueError("paper evidence aggregate output must be under reports/")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
