"""Tests for the live execution firewall."""

from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.live_execution_firewall import (
    LiveExecutionFirewallConfig,
    LiveOrderIntent,
    REQUIRED_OPERATOR_ACKNOWLEDGEMENT,
    build_live_execution_firewall_decision,
    format_live_execution_firewall_decision,
    live_execution_firewall_decision_to_dict,
    main,
    run_live_execution_firewall,
)


_GENERATED_AT = datetime(2026, 7, 6, 9, 15)


def test_live_execution_firewall_denies_default_intent_safely():
    decision = build_live_execution_firewall_decision(generated_at=_GENERATED_AT)

    assert decision.firewall_passed is True
    assert decision.intent_allowed is False
    assert decision.live_trading_approved is False
    assert decision.real_money_enabled is False
    assert decision.broker_submission_enabled is False
    assert decision.live_market_data_enabled is False
    assert decision.real_orders_enabled is False
    assert decision.not_a_profitability_claim is True
    assert "deny-only mode is active" in decision.denial_reasons
    assert decision.safety_violations == ()


def test_live_execution_firewall_flags_real_money_and_broker_submission_as_violations():
    decision = build_live_execution_firewall_decision(
        config=LiveExecutionFirewallConfig(
            real_money_enabled=True,
            broker_submission_enabled=True,
        ),
        generated_at=_GENERATED_AT,
    )

    assert decision.firewall_passed is False
    assert decision.intent_allowed is False
    assert "real money must remain disabled" in decision.safety_violations
    assert "broker submission must remain disabled" in decision.safety_violations


def test_live_execution_firewall_flags_live_data_and_real_orders_as_violations():
    decision = build_live_execution_firewall_decision(
        config=LiveExecutionFirewallConfig(
            live_market_data_enabled=True,
            real_orders_enabled=True,
        ),
        generated_at=_GENERATED_AT,
    )

    assert decision.firewall_passed is False
    assert "live market data must remain disabled" in decision.safety_violations
    assert "real orders must remain disabled" in decision.safety_violations


def test_live_execution_firewall_flags_quantity_limit_above_zero_as_violation():
    decision = build_live_execution_firewall_decision(
        config=LiveExecutionFirewallConfig(max_single_intent_quantity=1),
        generated_at=_GENERATED_AT,
    )

    assert decision.firewall_passed is False
    assert "max single intent quantity must remain 0" in decision.safety_violations


def test_live_execution_firewall_denies_unsupported_symbol():
    decision = build_live_execution_firewall_decision(
        intent=LiveOrderIntent(symbol="BANKNIFTY"),
        generated_at=_GENERATED_AT,
    )

    assert decision.intent_allowed is False
    assert "symbol is not allowed: BANKNIFTY" in decision.denial_reasons


def test_live_execution_firewall_tracks_acknowledgement_without_allowing_intent():
    decision = build_live_execution_firewall_decision(
        intent=LiveOrderIntent(
            operator_acknowledgement=REQUIRED_OPERATOR_ACKNOWLEDGEMENT,
        ),
        generated_at=_GENERATED_AT,
    )

    assert decision.operator_acknowledgement_present is True
    assert decision.intent_allowed is False
    assert decision.firewall_passed is True


def test_live_execution_firewall_writes_outputs_under_reports(tmp_path):
    decision, paths = run_live_execution_firewall(
        output_dir=tmp_path / "reports" / "paper_trading" / "live_execution_firewall",
        generated_at=_GENERATED_AT,
    )

    assert decision.firewall_passed is True
    assert paths.firewall_json.exists()
    assert paths.firewall_text.exists()
    assert paths.manifest_json.exists()

    text = paths.firewall_text.read_text(encoding="utf-8")
    assert "Hunter Quant Engine - Live Execution Firewall" in text
    assert "intent allowed: False" in text
    assert "real money disabled" in text


def test_live_execution_firewall_rejects_output_outside_reports(tmp_path):
    with pytest.raises(ValueError, match="reports/"):
        run_live_execution_firewall(
            output_dir=tmp_path / "live_execution_firewall",
            generated_at=_GENERATED_AT,
        )


def test_live_execution_firewall_decision_dict_is_json_safe():
    decision = build_live_execution_firewall_decision(generated_at=_GENERATED_AT)

    payload = live_execution_firewall_decision_to_dict(decision)

    assert payload["firewall_passed"] is True
    assert payload["intent_allowed"] is False
    assert payload["allowed_symbols"] == ["NIFTY"]
    assert "deny-only mode is active" in payload["denial_reasons"]
    assert payload["safety_violations"] == []


def test_live_execution_firewall_format_is_trader_friendly():
    decision = build_live_execution_firewall_decision(generated_at=_GENERATED_AT)

    text = format_live_execution_firewall_decision(decision)

    assert "Hunter Quant Engine - Live Execution Firewall" in text
    assert "deny-only live-readiness firewall" in text
    assert "this is not live trading" in text
    assert "real money disabled" in text
    assert "broker submission disabled" in text
    assert "live market data disabled" in text
    assert "real orders disabled" in text
    assert "firewall passed: True" in text
    assert "intent allowed: False" in text
    assert "live trading approved: False" in text


def test_live_execution_firewall_main_prints_success(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert main() == 0

    out = capsys.readouterr().out

    assert "Live Execution Firewall" in out
    assert "firewall passed: True" in out
    assert "intent allowed: False" in out


def test_live_execution_firewall_shortcut_points_to_safe_cli():
    text = Path("hqe_live_execution_firewall_check.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "src.paper_trading.live_execution_firewall" in text
    assert ".venv\\scripts\\python.exe" in text
    assert "this is not live trading" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text


def test_live_execution_firewall_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/live_execution_firewall.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def test_live_execution_firewall_docs_define_deny_only_boundary():
    text = Path("docs/LIVE_EXECUTION_FIREWALL.md").read_text(encoding="utf-8")

    assert "It is not live trading." in text
    assert "It does not enable real money." in text
    assert "It does not enable broker submission." in text
    assert "It does not enable live market data." in text
    assert "It does not enable real orders." in text
    assert "intent allowed is always false" in text
    assert ".\\hqe_live_execution_firewall_check.bat" in text
