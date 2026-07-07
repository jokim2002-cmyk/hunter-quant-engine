"""Tests for live-readiness preflight."""

from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.live_readiness_preflight import (
    build_live_readiness_preflight_report,
    format_live_readiness_preflight_report,
    live_readiness_preflight_report_to_dict,
    main,
    run_live_readiness_preflight,
)
from src.paper_trading.live_execution_firewall import LiveExecutionFirewallDecision
from src.paper_trading.live_readiness_gate import LiveReadinessReport
from src.paper_trading.live_safety_lock import LiveSafetyLockReport


_GENERATED_AT = datetime(2026, 7, 6, 9, 15)


def test_live_readiness_preflight_runs_full_safe_chain(tmp_path):
    result = run_live_readiness_preflight(
        output_root=tmp_path / "reports" / "paper_trading",
        generated_at=_GENERATED_AT,
    )

    assert result.preflight_report.preflight_passed is True
    assert result.preflight_report.live_trading_approved is False
    assert result.preflight_report.real_money_enabled is False
    assert result.preflight_report.broker_execution_enabled is False
    assert result.preflight_report.live_market_data_enabled is False
    assert result.preflight_report.real_orders_enabled is False
    assert result.preflight_report.not_a_profitability_claim is True
    assert result.preflight_report.live_execution_firewall_passed is True
    assert result.preflight_report.live_order_intent_allowed is False


def test_live_readiness_preflight_writes_stage_and_final_outputs(tmp_path):
    result = run_live_readiness_preflight(
        output_root=tmp_path / "reports" / "paper_trading",
        generated_at=_GENERATED_AT,
    )

    assert result.operator_demo_result.evidence_paths.evidence_json.exists()
    assert result.evidence_aggregate_paths.aggregate_json.exists()
    assert result.live_readiness_paths.readiness_json.exists()
    assert result.live_safety_lock_paths.safety_json.exists()
    assert result.live_execution_firewall_paths.firewall_json.exists()
    assert result.preflight_paths.preflight_json.exists()
    assert result.preflight_paths.preflight_text.exists()
    assert result.preflight_paths.manifest_json.exists()


def test_live_readiness_preflight_report_has_expected_stage_results(tmp_path):
    result = run_live_readiness_preflight(
        output_root=tmp_path / "reports" / "paper_trading",
        generated_at=_GENERATED_AT,
    )

    report = result.preflight_report

    assert report.operator_demo_passed is True
    assert report.evidence_aggregate_passed is True
    assert report.live_readiness_allowed is True
    assert report.live_safety_lock_passed is True
    assert report.live_execution_firewall_passed is True
    assert report.live_order_intent_allowed is False
    assert report.paper_closed_trades == 1
    assert report.aggregate_report_count == 1
    assert report.aggregate_total_closed_trades == 1
    assert report.blocking_reasons == ()


def test_live_readiness_preflight_report_dict_is_json_safe(tmp_path):
    result = run_live_readiness_preflight(
        output_root=tmp_path / "reports" / "paper_trading",
        generated_at=_GENERATED_AT,
    )

    payload = live_readiness_preflight_report_to_dict(result.preflight_report)

    assert payload["preflight_passed"] is True
    assert payload["live_trading_approved"] is False
    assert payload["real_money_enabled"] is False
    assert payload["live_execution_firewall_passed"] is True
    assert payload["live_order_intent_allowed"] is False
    assert payload["blocking_reasons"] == []


def test_live_readiness_preflight_format_is_trader_friendly(tmp_path):
    result = run_live_readiness_preflight(
        output_root=tmp_path / "reports" / "paper_trading",
        generated_at=_GENERATED_AT,
    )

    text = format_live_readiness_preflight_report(result.preflight_report)

    assert "Hunter Quant Engine - Live Readiness Preflight" in text
    assert "safe local preflight only" in text
    assert "this is not live trading" in text
    assert "real money disabled" in text
    assert "broker execution disabled" in text
    assert "live market data disabled" in text
    assert "real orders disabled" in text
    assert "not a profitability claim" in text
    assert "preflight passed: True" in text
    assert "live trading approved: False" in text
    assert "live execution firewall passed: True" in text
    assert "live order intent allowed: False" in text


def test_live_readiness_preflight_rejects_output_outside_reports(tmp_path):
    with pytest.raises(ValueError, match="reports/"):
        run_live_readiness_preflight(
            output_root=tmp_path / "paper_trading",
            generated_at=_GENERATED_AT,
        )


def test_live_readiness_preflight_blocks_failed_live_readiness(tmp_path):
    result = run_live_readiness_preflight(
        output_root=tmp_path / "reports" / "paper_trading",
        generated_at=_GENERATED_AT,
    )

    failed_readiness = LiveReadinessReport(
        **{
            **result.live_readiness_report.__dict__,
            "live_readiness_allowed": False,
            "blocking_reasons": ("test readiness blocker",),
        }
    )

    report = build_live_readiness_preflight_report(
        operator_demo_result=result.operator_demo_result,
        evidence_aggregate_report=result.evidence_aggregate_report,
        live_readiness_report=failed_readiness,
        live_safety_lock_report=result.live_safety_lock_report,
        live_execution_firewall_decision=result.live_execution_firewall_decision,
        generated_at=_GENERATED_AT,
    )

    assert report.preflight_passed is False
    assert "live-readiness gate did not allow engineering" in report.blocking_reasons
    assert "test readiness blocker" in report.blocking_reasons


def test_live_readiness_preflight_blocks_failed_safety_lock(tmp_path):
    result = run_live_readiness_preflight(
        output_root=tmp_path / "reports" / "paper_trading",
        generated_at=_GENERATED_AT,
    )

    failed_safety = LiveSafetyLockReport(
        **{
            **result.live_safety_lock_report.__dict__,
            "safety_lock_passed": False,
            "blocking_reasons": ("test safety blocker",),
        }
    )

    report = build_live_readiness_preflight_report(
        operator_demo_result=result.operator_demo_result,
        evidence_aggregate_report=result.evidence_aggregate_report,
        live_readiness_report=result.live_readiness_report,
        live_safety_lock_report=failed_safety,
        live_execution_firewall_decision=result.live_execution_firewall_decision,
        generated_at=_GENERATED_AT,
    )

    assert report.preflight_passed is False
    assert "live safety lock did not pass" in report.blocking_reasons
    assert "test safety blocker" in report.blocking_reasons


def test_live_readiness_preflight_blocks_failed_execution_firewall(tmp_path):
    result = run_live_readiness_preflight(
        output_root=tmp_path / "reports" / "paper_trading",
        generated_at=_GENERATED_AT,
    )

    failed_firewall = LiveExecutionFirewallDecision(
        **{
            **result.live_execution_firewall_decision.__dict__,
            "firewall_passed": False,
            "safety_violations": ("test firewall blocker",),
        }
    )

    report = build_live_readiness_preflight_report(
        operator_demo_result=result.operator_demo_result,
        evidence_aggregate_report=result.evidence_aggregate_report,
        live_readiness_report=result.live_readiness_report,
        live_safety_lock_report=result.live_safety_lock_report,
        live_execution_firewall_decision=failed_firewall,
        generated_at=_GENERATED_AT,
    )

    assert report.preflight_passed is False
    assert "live execution firewall did not pass" in report.blocking_reasons
    assert "test firewall blocker" in report.blocking_reasons


def test_live_readiness_preflight_main_prints_success(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _write_required_safety_docs(tmp_path)

    assert main() == 0

    out = capsys.readouterr().out

    assert "Live Readiness Preflight" in out
    assert "preflight passed: True" in out
    assert "live trading approved: False" in out
    assert "live execution firewall passed: True" in out
    assert "live order intent allowed: False" in out


def test_live_readiness_preflight_shortcut_points_to_safe_cli():
    text = Path("hqe_live_readiness_preflight.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "src.paper_trading.live_readiness_preflight" in text
    assert ".venv\\scripts\\python.exe" in text
    assert "this is not live trading" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text


def test_live_readiness_preflight_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/live_readiness_preflight.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def test_live_readiness_preflight_docs_define_boundary():
    text = Path("docs/LIVE_READINESS_PREFLIGHT.md").read_text(encoding="utf-8")

    assert "It is not live trading." in text
    assert "It does not enable real money." in text
    assert "It does not enable broker execution." in text
    assert "It does not enable live market data." in text
    assert "It does not enable real orders." in text
    assert ".\\hqe_live_readiness_preflight.bat" in text


def _write_required_safety_docs(root: Path):
    docs = root / "docs"
    docs.mkdir(parents=True)
    safety_text = "\n".join(
        [
            "It does not place broker orders.",
            "It does not use real money.",
            "It does not claim profitability.",
            "Live trading remains deferred",
        ]
    )

    for name in (
        "PAPER_MVP_V0_1_SCOPE.md",
        "PAPER_OPERATOR_GUIDE.md",
        "PAPER_MVP_V0_1_RELEASE_NOTES.md",
    ):
        (docs / name).write_text(safety_text, encoding="utf-8")
