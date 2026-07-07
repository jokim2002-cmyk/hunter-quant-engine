"""
Live Safety Lock

Disabled-by-default safety lock for future live-readiness engineering.

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
from typing import Any


DEFAULT_LIVE_SAFETY_LOCK_OUTPUT_DIR = (
    Path("reports") / "paper_trading" / "live_safety_lock"
)

REQUIRED_OPERATOR_ACKNOWLEDGEMENT = (
    "I understand this is live-readiness only and real money remains disabled."
)


@dataclass(frozen=True)
class LiveSafetyLockConfig:
    """
    Disabled-by-default live safety config.

    All dangerous flags must remain False unless a future, separately reviewed
    module explicitly changes the policy.
    """

    real_money_enabled: bool = False
    broker_execution_enabled: bool = False
    live_market_data_enabled: bool = False
    real_orders_enabled: bool = False
    manual_arming_required: bool = True
    operator_acknowledgement: str = ""
    allowed_underlyings: tuple[str, ...] = ("NIFTY",)
    max_single_order_quantity: int = 0
    max_daily_order_count: int = 0


@dataclass(frozen=True)
class LiveSafetyLockPaths:
    """
    Files written by the live safety lock.
    """

    output_dir: Path
    safety_json: Path
    safety_text: Path
    manifest_json: Path


@dataclass(frozen=True)
class LiveSafetyLockReport:
    """
    Live safety lock decision.

    safety_lock_passed means the system is safely locked down.
    It does not mean live trading is approved.
    """

    generated_at: str
    lock_version: int
    lock_source: str
    safety_lock_passed: bool
    live_trading_approved: bool
    real_money_enabled: bool
    broker_execution_enabled: bool
    live_market_data_enabled: bool
    real_orders_enabled: bool
    manual_arming_required: bool
    operator_acknowledgement_present: bool
    allowed_underlyings: tuple[str, ...]
    max_single_order_quantity: int
    max_daily_order_count: int
    not_a_profitability_claim: bool
    blocking_reasons: tuple[str, ...]


def run_live_safety_lock(
    config: LiveSafetyLockConfig = LiveSafetyLockConfig(),
    *,
    output_dir: str | Path = DEFAULT_LIVE_SAFETY_LOCK_OUTPUT_DIR,
    generated_at: datetime | None = None,
) -> tuple[LiveSafetyLockReport, LiveSafetyLockPaths]:
    """
    Evaluate and write the live safety lock report.
    """
    report = build_live_safety_lock_report(
        config,
        generated_at=generated_at,
    )
    paths = write_live_safety_lock_report(report, output_dir)
    return report, paths


def build_live_safety_lock_report(
    config: LiveSafetyLockConfig = LiveSafetyLockConfig(),
    *,
    generated_at: datetime | None = None,
) -> LiveSafetyLockReport:
    """
    Build a safety-lock report from config.
    """
    generated = generated_at or datetime.now(timezone.utc)
    blocking_reasons = _build_blocking_reasons(config)

    return LiveSafetyLockReport(
        generated_at=generated.isoformat(),
        lock_version=1,
        lock_source="disabled_by_default_live_safety_lock",
        safety_lock_passed=not blocking_reasons,
        live_trading_approved=False,
        real_money_enabled=config.real_money_enabled,
        broker_execution_enabled=config.broker_execution_enabled,
        live_market_data_enabled=config.live_market_data_enabled,
        real_orders_enabled=config.real_orders_enabled,
        manual_arming_required=config.manual_arming_required,
        operator_acknowledgement_present=(
            config.operator_acknowledgement == REQUIRED_OPERATOR_ACKNOWLEDGEMENT
        ),
        allowed_underlyings=config.allowed_underlyings,
        max_single_order_quantity=config.max_single_order_quantity,
        max_daily_order_count=config.max_daily_order_count,
        not_a_profitability_claim=True,
        blocking_reasons=tuple(blocking_reasons),
    )


def write_live_safety_lock_report(
    report: LiveSafetyLockReport,
    output_dir: str | Path = DEFAULT_LIVE_SAFETY_LOCK_OUTPUT_DIR,
) -> LiveSafetyLockPaths:
    """
    Write live safety lock output files under reports/.
    """
    safe_output_dir = _ensure_reports_output_dir(output_dir)
    safe_output_dir.mkdir(parents=True, exist_ok=True)

    paths = LiveSafetyLockPaths(
        output_dir=safe_output_dir,
        safety_json=safe_output_dir / "live_safety_lock.json",
        safety_text=safe_output_dir / "live_safety_lock.txt",
        manifest_json=safe_output_dir / "manifest.json",
    )

    _write_json(paths.safety_json, live_safety_lock_report_to_dict(report))
    paths.safety_text.write_text(format_live_safety_lock_report(report), encoding="utf-8")
    _write_json(paths.manifest_json, live_safety_lock_manifest_to_dict(paths))

    return paths


def live_safety_lock_report_to_dict(report: LiveSafetyLockReport) -> dict[str, Any]:
    """
    Convert live safety lock report to JSON-safe dict.
    """
    payload = asdict(report)
    payload["allowed_underlyings"] = list(report.allowed_underlyings)
    payload["blocking_reasons"] = list(report.blocking_reasons)
    return payload


def live_safety_lock_manifest_to_dict(paths: LiveSafetyLockPaths) -> dict[str, Any]:
    """
    Convert live safety lock output paths to manifest form.
    """
    return {
        "manifest_version": 1,
        "manifest_source": "live_safety_lock",
        "live_trading_approved": False,
        "real_money_enabled": False,
        "broker_execution_enabled": False,
        "output_dir": str(paths.output_dir),
        "files": {
            "safety_json": str(paths.safety_json),
            "safety_text": str(paths.safety_text),
            "manifest_json": str(paths.manifest_json),
        },
    }


def format_live_safety_lock_report(report: LiveSafetyLockReport) -> str:
    """
    Format live safety lock report for terminal/text display.
    """
    lines = [
        "Hunter Quant Engine - Live Safety Lock",
        "disabled-by-default live safety scaffold",
        "this is not live trading",
        "real money disabled",
        "broker execution disabled",
        "live market data disabled",
        "real orders disabled",
        "not a profitability claim",
        "",
        f"generated at: {report.generated_at}",
        f"safety lock passed: {report.safety_lock_passed}",
        f"live trading approved: {report.live_trading_approved}",
        "",
        "Danger Flags",
        f"real money enabled: {report.real_money_enabled}",
        f"broker execution enabled: {report.broker_execution_enabled}",
        f"live market data enabled: {report.live_market_data_enabled}",
        f"real orders enabled: {report.real_orders_enabled}",
        "",
        "Limits",
        f"allowed underlyings: {', '.join(report.allowed_underlyings)}",
        f"max single order quantity: {report.max_single_order_quantity}",
        f"max daily order count: {report.max_daily_order_count}",
        "",
        "Manual Arming",
        f"manual arming required: {report.manual_arming_required}",
        f"operator acknowledgement present: {report.operator_acknowledgement_present}",
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
    report, paths = run_live_safety_lock()
    print(format_live_safety_lock_report(report), end="")
    print(f"safety json: {paths.safety_json}")
    print(f"safety text: {paths.safety_text}")
    return 0 if report.safety_lock_passed else 1


def _build_blocking_reasons(config: LiveSafetyLockConfig) -> list[str]:
    reasons: list[str] = []

    if config.real_money_enabled:
        reasons.append("real money must remain disabled")

    if config.broker_execution_enabled:
        reasons.append("broker execution must remain disabled")

    if config.live_market_data_enabled:
        reasons.append("live market data must remain disabled")

    if config.real_orders_enabled:
        reasons.append("real orders must remain disabled")

    if not config.manual_arming_required:
        reasons.append("manual arming must remain required")

    if config.max_single_order_quantity != 0:
        reasons.append("max single order quantity must remain 0")

    if config.max_daily_order_count != 0:
        reasons.append("max daily order count must remain 0")

    if not config.allowed_underlyings:
        reasons.append("allowed underlyings cannot be empty")

    return reasons


def _ensure_reports_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    if "reports" not in path.parts:
        raise ValueError("live safety lock output must be under reports/")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
