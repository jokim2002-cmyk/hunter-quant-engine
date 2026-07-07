"""
Live Readiness Gate

Checks whether paper evidence is strong enough to start live-readiness
engineering.

This is not live trading.
This module does not enable real money.
This module does not use broker APIs.
This module does not use live market data.
This module does not send real orders.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


DEFAULT_EVIDENCE_AGGREGATE_JSON = (
    Path("reports") / "paper_trading" / "evidence_aggregate" / "aggregate.json"
)
DEFAULT_LIVE_READINESS_OUTPUT_DIR = (
    Path("reports") / "paper_trading" / "live_readiness"
)

REQUIRED_SAFETY_DOCS = (
    Path("docs/PAPER_MVP_V0_1_SCOPE.md"),
    Path("docs/PAPER_OPERATOR_GUIDE.md"),
    Path("docs/PAPER_MVP_V0_1_RELEASE_NOTES.md"),
)

REQUIRED_SAFETY_TEXT = (
    "It does not place broker orders.",
    "It does not use real money.",
    "It does not claim profitability.",
    "Live trading remains deferred",
)


@dataclass(frozen=True)
class LiveReadinessThresholds:
    """
    Thresholds required before live-readiness engineering can start.
    """

    min_evidence_reports: int = 1
    min_total_closed_trades: int = 1
    max_total_open_positions: int = 0
    max_total_unknown_trades: int = 0
    min_total_simulated_net_pnl: float | None = None
    require_aggregate_passed: bool = True


@dataclass(frozen=True)
class LiveReadinessPaths:
    """
    Files written by the live-readiness gate.
    """

    output_dir: Path
    readiness_json: Path
    readiness_text: Path
    manifest_json: Path


@dataclass(frozen=True)
class LiveReadinessReport:
    """
    Live-readiness gate result.

    live_readiness_allowed means engineering work on live-readiness may start.
    It does not mean real-money trading is allowed.
    """

    generated_at: str
    gate_version: int
    gate_source: str
    live_readiness_allowed: bool
    real_money_enabled: bool
    broker_execution_enabled: bool
    live_market_data_required: bool
    not_a_profitability_claim: bool
    evidence_aggregate_json: str
    evidence_report_count: int
    evidence_aggregate_passed: bool
    total_closed_trades: int
    total_open_positions: int
    total_unknown_trades: int
    total_simulated_net_pnl: float | None
    thresholds: LiveReadinessThresholds
    blocking_reasons: tuple[str, ...]


def run_live_readiness_gate(
    evidence_aggregate_json: str | Path = DEFAULT_EVIDENCE_AGGREGATE_JSON,
    *,
    output_dir: str | Path = DEFAULT_LIVE_READINESS_OUTPUT_DIR,
    thresholds: LiveReadinessThresholds = LiveReadinessThresholds(),
    generated_at: datetime | None = None,
) -> tuple[LiveReadinessReport, LiveReadinessPaths]:
    """
    Build and write a live-readiness gate report.
    """
    evidence_path = Path(evidence_aggregate_json)
    evidence_payload = _load_optional_json(evidence_path)
    report = build_live_readiness_report(
        evidence_payload,
        evidence_aggregate_json=evidence_path,
        thresholds=thresholds,
        generated_at=generated_at,
    )
    paths = write_live_readiness_report(report, output_dir)
    return report, paths


def build_live_readiness_report(
    evidence_payload: Mapping[str, Any] | None,
    *,
    evidence_aggregate_json: str | Path = DEFAULT_EVIDENCE_AGGREGATE_JSON,
    thresholds: LiveReadinessThresholds = LiveReadinessThresholds(),
    generated_at: datetime | None = None,
) -> LiveReadinessReport:
    """
    Build a live-readiness report from aggregate paper evidence.
    """
    generated = generated_at or datetime.now(timezone.utc)
    evidence_path = Path(evidence_aggregate_json)

    evidence_report_count = _int_value(evidence_payload, "report_count")
    evidence_aggregate_passed = bool(
        evidence_payload is not None and evidence_payload.get("passed") is True
    )
    total_closed_trades = _int_value(evidence_payload, "total_closed_trades")
    total_open_positions = _int_value(evidence_payload, "total_open_positions")
    total_unknown_trades = _int_value(evidence_payload, "total_unknown_trades")
    total_simulated_net_pnl = _optional_float_value(
        evidence_payload,
        "total_simulated_net_pnl",
    )

    blocking_reasons = _build_blocking_reasons(
        evidence_payload=evidence_payload,
        evidence_path=evidence_path,
        evidence_report_count=evidence_report_count,
        evidence_aggregate_passed=evidence_aggregate_passed,
        total_closed_trades=total_closed_trades,
        total_open_positions=total_open_positions,
        total_unknown_trades=total_unknown_trades,
        total_simulated_net_pnl=total_simulated_net_pnl,
        thresholds=thresholds,
    )

    return LiveReadinessReport(
        generated_at=generated.isoformat(),
        gate_version=1,
        gate_source="paper_live_readiness",
        live_readiness_allowed=not blocking_reasons,
        real_money_enabled=False,
        broker_execution_enabled=False,
        live_market_data_required=False,
        not_a_profitability_claim=True,
        evidence_aggregate_json=str(evidence_path),
        evidence_report_count=evidence_report_count,
        evidence_aggregate_passed=evidence_aggregate_passed,
        total_closed_trades=total_closed_trades,
        total_open_positions=total_open_positions,
        total_unknown_trades=total_unknown_trades,
        total_simulated_net_pnl=total_simulated_net_pnl,
        thresholds=thresholds,
        blocking_reasons=tuple(blocking_reasons),
    )


def write_live_readiness_report(
    report: LiveReadinessReport,
    output_dir: str | Path = DEFAULT_LIVE_READINESS_OUTPUT_DIR,
) -> LiveReadinessPaths:
    """
    Write live-readiness gate output files under reports/.
    """
    safe_output_dir = _ensure_reports_output_dir(output_dir)
    safe_output_dir.mkdir(parents=True, exist_ok=True)

    paths = LiveReadinessPaths(
        output_dir=safe_output_dir,
        readiness_json=safe_output_dir / "live_readiness.json",
        readiness_text=safe_output_dir / "live_readiness.txt",
        manifest_json=safe_output_dir / "manifest.json",
    )

    _write_json(paths.readiness_json, live_readiness_report_to_dict(report))
    paths.readiness_text.write_text(format_live_readiness_report(report), encoding="utf-8")
    _write_json(paths.manifest_json, live_readiness_manifest_to_dict(paths))

    return paths


def live_readiness_report_to_dict(report: LiveReadinessReport) -> dict[str, Any]:
    """
    Convert live-readiness report to JSON-safe dict.
    """
    payload = asdict(report)
    payload["blocking_reasons"] = list(report.blocking_reasons)
    return payload


def live_readiness_manifest_to_dict(paths: LiveReadinessPaths) -> dict[str, Any]:
    """
    Convert output paths to manifest form.
    """
    return {
        "manifest_version": 1,
        "manifest_source": "live_readiness_gate",
        "real_money_enabled": False,
        "broker_execution_enabled": False,
        "output_dir": str(paths.output_dir),
        "files": {
            "readiness_json": str(paths.readiness_json),
            "readiness_text": str(paths.readiness_text),
            "manifest_json": str(paths.manifest_json),
        },
    }


def format_live_readiness_report(report: LiveReadinessReport) -> str:
    """
    Format live-readiness gate output for terminal/text display.
    """
    lines = [
        "Hunter Quant Engine - Live Readiness Gate",
        "live-readiness engineering check only",
        "real money disabled",
        "broker execution disabled",
        "no live market data required",
        "not a profitability claim",
        "",
        f"generated at: {report.generated_at}",
        f"live-readiness allowed: {report.live_readiness_allowed}",
        f"real money enabled: {report.real_money_enabled}",
        f"broker execution enabled: {report.broker_execution_enabled}",
        "",
        "Evidence Aggregate",
        f"aggregate json: {report.evidence_aggregate_json}",
        f"report count: {report.evidence_report_count}",
        f"aggregate passed: {report.evidence_aggregate_passed}",
        f"closed trades: {report.total_closed_trades}",
        f"open positions: {report.total_open_positions}",
        f"unknown trades: {report.total_unknown_trades}",
        f"simulated net pnl: {_format_optional(report.total_simulated_net_pnl)}",
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
    report, paths = run_live_readiness_gate()
    print(format_live_readiness_report(report), end="")
    print(f"readiness json: {paths.readiness_json}")
    print(f"readiness text: {paths.readiness_text}")
    return 0 if report.live_readiness_allowed else 1


def _build_blocking_reasons(
    *,
    evidence_payload: Mapping[str, Any] | None,
    evidence_path: Path,
    evidence_report_count: int,
    evidence_aggregate_passed: bool,
    total_closed_trades: int,
    total_open_positions: int,
    total_unknown_trades: int,
    total_simulated_net_pnl: float | None,
    thresholds: LiveReadinessThresholds,
) -> list[str]:
    reasons: list[str] = []

    if evidence_payload is None:
        reasons.append(
            f"paper evidence aggregate missing: {evidence_path}. "
            "Run hqe_paper_mvp_operator_demo.bat and hqe_paper_evidence_aggregate.bat first."
        )
        return reasons

    if thresholds.require_aggregate_passed and not evidence_aggregate_passed:
        reasons.append("paper evidence aggregate failed its gates")

    if evidence_report_count < thresholds.min_evidence_reports:
        reasons.append(
            "evidence reports below minimum: "
            f"{evidence_report_count} < {thresholds.min_evidence_reports}"
        )

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
        if total_simulated_net_pnl is None:
            reasons.append("simulated net pnl unavailable")
        elif total_simulated_net_pnl < thresholds.min_total_simulated_net_pnl:
            reasons.append(
                "simulated net pnl below minimum: "
                f"{total_simulated_net_pnl} < {thresholds.min_total_simulated_net_pnl}"
            )

    reasons.extend(_safety_doc_blockers())

    return reasons


def _safety_doc_blockers() -> list[str]:
    blockers: list[str] = []

    for path in REQUIRED_SAFETY_DOCS:
        if not path.exists():
            blockers.append(f"safety doc missing: {path}")
            continue

        text = path.read_text(encoding="utf-8")
        for required_text in REQUIRED_SAFETY_TEXT:
            if required_text not in text:
                blockers.append(f"safety text missing in {path}: {required_text}")

    return blockers


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("live-readiness evidence aggregate must be a JSON object")
    return payload


def _int_value(payload: Mapping[str, Any] | None, key: str) -> int:
    if payload is None:
        return 0
    value = payload.get(key)
    if value is None:
        return 0
    return int(value)


def _optional_float_value(payload: Mapping[str, Any] | None, key: str) -> float | None:
    if payload is None:
        return None
    value = payload.get(key)
    if value is None:
        return None
    return float(value)


def _format_optional(value: Any) -> str:
    if value is None:
        return "unknown"
    return str(value)


def _ensure_reports_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    if "reports" not in path.parts:
        raise ValueError("live-readiness output must be under reports/")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
