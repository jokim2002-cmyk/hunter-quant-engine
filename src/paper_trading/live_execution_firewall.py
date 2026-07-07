"""
Live Execution Firewall

Deny-only firewall for future live-readiness order intents.

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


DEFAULT_LIVE_EXECUTION_FIREWALL_OUTPUT_DIR = (
    Path("reports") / "paper_trading" / "live_execution_firewall"
)

REQUIRED_OPERATOR_ACKNOWLEDGEMENT = (
    "I understand the live execution firewall is deny-only and real money remains disabled."
)


@dataclass(frozen=True)
class LiveOrderIntent:
    """
    Future live-readiness order intent.

    This model is only evaluated by the firewall.
    It is not submitted anywhere.
    """

    symbol: str = "NIFTY"
    side: str = "BUY"
    quantity: int = 1
    order_kind: str = "MARKET"
    product_kind: str = "INTRADAY"
    dry_run: bool = True
    requested_by: str = "operator"
    operator_acknowledgement: str = ""


@dataclass(frozen=True)
class LiveExecutionFirewallConfig:
    """
    Deny-only live execution firewall config.
    """

    deny_only_mode: bool = True
    real_money_enabled: bool = False
    broker_submission_enabled: bool = False
    live_market_data_enabled: bool = False
    real_orders_enabled: bool = False
    manual_review_required: bool = True
    allowed_symbols: tuple[str, ...] = ("NIFTY",)
    max_single_intent_quantity: int = 0


@dataclass(frozen=True)
class LiveExecutionFirewallPaths:
    """
    Files written by the live execution firewall.
    """

    output_dir: Path
    firewall_json: Path
    firewall_text: Path
    manifest_json: Path


@dataclass(frozen=True)
class LiveExecutionFirewallDecision:
    """
    Live execution firewall decision.

    firewall_passed means the firewall stayed safely closed.
    intent_allowed is intentionally False in this scaffold.
    """

    generated_at: str
    firewall_version: int
    firewall_source: str
    firewall_passed: bool
    intent_allowed: bool
    live_trading_approved: bool
    real_money_enabled: bool
    broker_submission_enabled: bool
    live_market_data_enabled: bool
    real_orders_enabled: bool
    manual_review_required: bool
    deny_only_mode: bool
    not_a_profitability_claim: bool
    intent_symbol: str
    intent_side: str
    intent_quantity: int
    intent_order_kind: str
    intent_product_kind: str
    intent_dry_run: bool
    allowed_symbols: tuple[str, ...]
    max_single_intent_quantity: int
    operator_acknowledgement_present: bool
    denial_reasons: tuple[str, ...]
    safety_violations: tuple[str, ...]


def run_live_execution_firewall(
    intent: LiveOrderIntent = LiveOrderIntent(),
    config: LiveExecutionFirewallConfig = LiveExecutionFirewallConfig(),
    *,
    output_dir: str | Path = DEFAULT_LIVE_EXECUTION_FIREWALL_OUTPUT_DIR,
    generated_at: datetime | None = None,
) -> tuple[LiveExecutionFirewallDecision, LiveExecutionFirewallPaths]:
    """
    Evaluate a future live-readiness intent and write firewall outputs.
    """
    decision = build_live_execution_firewall_decision(
        intent,
        config,
        generated_at=generated_at,
    )
    paths = write_live_execution_firewall_decision(decision, output_dir)
    return decision, paths


def build_live_execution_firewall_decision(
    intent: LiveOrderIntent = LiveOrderIntent(),
    config: LiveExecutionFirewallConfig = LiveExecutionFirewallConfig(),
    *,
    generated_at: datetime | None = None,
) -> LiveExecutionFirewallDecision:
    """
    Build deny-only firewall decision.
    """
    generated = generated_at or datetime.now(timezone.utc)
    safety_violations = tuple(_build_safety_violations(config))
    denial_reasons = tuple(_build_denial_reasons(intent, config))

    intent_allowed = False
    firewall_passed = not safety_violations and not intent_allowed

    return LiveExecutionFirewallDecision(
        generated_at=generated.isoformat(),
        firewall_version=1,
        firewall_source="deny_only_live_execution_firewall",
        firewall_passed=firewall_passed,
        intent_allowed=intent_allowed,
        live_trading_approved=False,
        real_money_enabled=config.real_money_enabled,
        broker_submission_enabled=config.broker_submission_enabled,
        live_market_data_enabled=config.live_market_data_enabled,
        real_orders_enabled=config.real_orders_enabled,
        manual_review_required=config.manual_review_required,
        deny_only_mode=config.deny_only_mode,
        not_a_profitability_claim=True,
        intent_symbol=intent.symbol,
        intent_side=intent.side,
        intent_quantity=intent.quantity,
        intent_order_kind=intent.order_kind,
        intent_product_kind=intent.product_kind,
        intent_dry_run=intent.dry_run,
        allowed_symbols=config.allowed_symbols,
        max_single_intent_quantity=config.max_single_intent_quantity,
        operator_acknowledgement_present=(
            intent.operator_acknowledgement == REQUIRED_OPERATOR_ACKNOWLEDGEMENT
        ),
        denial_reasons=denial_reasons,
        safety_violations=safety_violations,
    )


def write_live_execution_firewall_decision(
    decision: LiveExecutionFirewallDecision,
    output_dir: str | Path = DEFAULT_LIVE_EXECUTION_FIREWALL_OUTPUT_DIR,
) -> LiveExecutionFirewallPaths:
    """
    Write live execution firewall output files under reports/.
    """
    safe_output_dir = _ensure_reports_output_dir(output_dir)
    safe_output_dir.mkdir(parents=True, exist_ok=True)

    paths = LiveExecutionFirewallPaths(
        output_dir=safe_output_dir,
        firewall_json=safe_output_dir / "live_execution_firewall.json",
        firewall_text=safe_output_dir / "live_execution_firewall.txt",
        manifest_json=safe_output_dir / "manifest.json",
    )

    _write_json(paths.firewall_json, live_execution_firewall_decision_to_dict(decision))
    paths.firewall_text.write_text(
        format_live_execution_firewall_decision(decision),
        encoding="utf-8",
    )
    _write_json(paths.manifest_json, live_execution_firewall_manifest_to_dict(paths))

    return paths


def live_execution_firewall_decision_to_dict(
    decision: LiveExecutionFirewallDecision,
) -> dict[str, Any]:
    """
    Convert firewall decision to JSON-safe dict.
    """
    payload = asdict(decision)
    payload["allowed_symbols"] = list(decision.allowed_symbols)
    payload["denial_reasons"] = list(decision.denial_reasons)
    payload["safety_violations"] = list(decision.safety_violations)
    return payload


def live_execution_firewall_manifest_to_dict(
    paths: LiveExecutionFirewallPaths,
) -> dict[str, Any]:
    """
    Convert firewall output paths to manifest form.
    """
    return {
        "manifest_version": 1,
        "manifest_source": "live_execution_firewall",
        "live_trading_approved": False,
        "real_money_enabled": False,
        "broker_submission_enabled": False,
        "output_dir": str(paths.output_dir),
        "files": {
            "firewall_json": str(paths.firewall_json),
            "firewall_text": str(paths.firewall_text),
            "manifest_json": str(paths.manifest_json),
        },
    }


def format_live_execution_firewall_decision(
    decision: LiveExecutionFirewallDecision,
) -> str:
    """
    Format firewall decision for terminal/text display.
    """
    lines = [
        "Hunter Quant Engine - Live Execution Firewall",
        "deny-only live-readiness firewall",
        "this is not live trading",
        "real money disabled",
        "broker submission disabled",
        "live market data disabled",
        "real orders disabled",
        "not a profitability claim",
        "",
        f"generated at: {decision.generated_at}",
        f"firewall passed: {decision.firewall_passed}",
        f"intent allowed: {decision.intent_allowed}",
        f"live trading approved: {decision.live_trading_approved}",
        "",
        "Intent",
        f"symbol: {decision.intent_symbol}",
        f"side: {decision.intent_side}",
        f"quantity: {decision.intent_quantity}",
        f"order kind: {decision.intent_order_kind}",
        f"product kind: {decision.intent_product_kind}",
        f"dry run: {decision.intent_dry_run}",
        "",
        "Danger Flags",
        f"real money enabled: {decision.real_money_enabled}",
        f"broker submission enabled: {decision.broker_submission_enabled}",
        f"live market data enabled: {decision.live_market_data_enabled}",
        f"real orders enabled: {decision.real_orders_enabled}",
        "",
        "Deny Policy",
        f"deny-only mode: {decision.deny_only_mode}",
        f"manual review required: {decision.manual_review_required}",
        f"allowed symbols: {', '.join(decision.allowed_symbols)}",
        f"max single intent quantity: {decision.max_single_intent_quantity}",
        f"operator acknowledgement present: {decision.operator_acknowledgement_present}",
        "",
        "Denial Reasons",
    ]

    if decision.denial_reasons:
        lines.extend(f"- {reason}" for reason in decision.denial_reasons)
    else:
        lines.append("- none")

    lines.append("")
    lines.append("Safety Violations")

    if decision.safety_violations:
        lines.extend(f"- {reason}" for reason in decision.safety_violations)
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def main() -> int:
    """
    CLI entrypoint.
    """
    decision, paths = run_live_execution_firewall()
    print(format_live_execution_firewall_decision(decision), end="")
    print(f"firewall json: {paths.firewall_json}")
    print(f"firewall text: {paths.firewall_text}")
    return 0 if decision.firewall_passed else 1


def _build_denial_reasons(
    intent: LiveOrderIntent,
    config: LiveExecutionFirewallConfig,
) -> list[str]:
    reasons: list[str] = []

    if config.deny_only_mode:
        reasons.append("deny-only mode is active")

    if not config.real_money_enabled:
        reasons.append("real money is disabled")

    if not config.broker_submission_enabled:
        reasons.append("broker submission is disabled")

    if not config.live_market_data_enabled:
        reasons.append("live market data is disabled")

    if not config.real_orders_enabled:
        reasons.append("real orders are disabled")

    if intent.symbol not in config.allowed_symbols:
        reasons.append(f"symbol is not allowed: {intent.symbol}")

    if intent.quantity > config.max_single_intent_quantity:
        reasons.append(
            "intent quantity above maximum: "
            f"{intent.quantity} > {config.max_single_intent_quantity}"
        )

    if config.manual_review_required:
        reasons.append("manual review is required")

    if intent.operator_acknowledgement != REQUIRED_OPERATOR_ACKNOWLEDGEMENT:
        reasons.append("operator acknowledgement missing")

    return reasons


def _build_safety_violations(config: LiveExecutionFirewallConfig) -> list[str]:
    violations: list[str] = []

    if not config.deny_only_mode:
        violations.append("deny-only mode must remain enabled")

    if config.real_money_enabled:
        violations.append("real money must remain disabled")

    if config.broker_submission_enabled:
        violations.append("broker submission must remain disabled")

    if config.live_market_data_enabled:
        violations.append("live market data must remain disabled")

    if config.real_orders_enabled:
        violations.append("real orders must remain disabled")

    if not config.manual_review_required:
        violations.append("manual review must remain required")

    if config.max_single_intent_quantity != 0:
        violations.append("max single intent quantity must remain 0")

    if not config.allowed_symbols:
        violations.append("allowed symbols cannot be empty")

    return violations


def _ensure_reports_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    if "reports" not in path.parts:
        raise ValueError("live execution firewall output must be under reports/")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
