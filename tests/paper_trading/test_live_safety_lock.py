"""Tests for the live safety lock."""

from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.live_safety_lock import (
    LiveSafetyLockConfig,
    REQUIRED_OPERATOR_ACKNOWLEDGEMENT,
    build_live_safety_lock_report,
    format_live_safety_lock_report,
    live_safety_lock_report_to_dict,
    main,
    run_live_safety_lock,
)


_GENERATED_AT = datetime(2026, 7, 6, 9, 15)


def test_live_safety_lock_passes_when_everything_is_disabled():
    report = build_live_safety_lock_report(generated_at=_GENERATED_AT)

    assert report.safety_lock_passed is True
    assert report.live_trading_approved is False
    assert report.real_money_enabled is False
    assert report.broker_execution_enabled is False
    assert report.live_market_data_enabled is False
    assert report.real_orders_enabled is False
    assert report.not_a_profitability_claim is True
    assert report.blocking_reasons == ()


def test_live_safety_lock_blocks_real_money():
    report = build_live_safety_lock_report(
        LiveSafetyLockConfig(real_money_enabled=True),
        generated_at=_GENERATED_AT,
    )

    assert report.safety_lock_passed is False
    assert "real money must remain disabled" in report.blocking_reasons


def test_live_safety_lock_blocks_broker_execution():
    report = build_live_safety_lock_report(
        LiveSafetyLockConfig(broker_execution_enabled=True),
        generated_at=_GENERATED_AT,
    )

    assert report.safety_lock_passed is False
    assert "broker execution must remain disabled" in report.blocking_reasons


def test_live_safety_lock_blocks_real_orders_and_live_data():
    report = build_live_safety_lock_report(
        LiveSafetyLockConfig(
            live_market_data_enabled=True,
            real_orders_enabled=True,
        ),
        generated_at=_GENERATED_AT,
    )

    assert report.safety_lock_passed is False
    assert "live market data must remain disabled" in report.blocking_reasons
    assert "real orders must remain disabled" in report.blocking_reasons


def test_live_safety_lock_blocks_quantity_limits_above_zero():
    report = build_live_safety_lock_report(
        LiveSafetyLockConfig(
            max_single_order_quantity=1,
            max_daily_order_count=1,
        ),
        generated_at=_GENERATED_AT,
    )

    assert report.safety_lock_passed is False
    assert "max single order quantity must remain 0" in report.blocking_reasons
    assert "max daily order count must remain 0" in report.blocking_reasons


def test_live_safety_lock_tracks_operator_acknowledgement_without_enabling_live():
    report = build_live_safety_lock_report(
        LiveSafetyLockConfig(
            operator_acknowledgement=REQUIRED_OPERATOR_ACKNOWLEDGEMENT,
        ),
        generated_at=_GENERATED_AT,
    )

    assert report.safety_lock_passed is True
    assert report.operator_acknowledgement_present is True
    assert report.live_trading_approved is False


def test_live_safety_lock_writes_outputs_under_reports(tmp_path):
    report, paths = run_live_safety_lock(
        output_dir=tmp_path / "reports" / "paper_trading" / "live_safety_lock",
        generated_at=_GENERATED_AT,
    )

    assert report.safety_lock_passed is True
    assert paths.safety_json.exists()
    assert paths.safety_text.exists()
    assert paths.manifest_json.exists()

    text = paths.safety_text.read_text(encoding="utf-8")
    assert "Hunter Quant Engine - Live Safety Lock" in text
    assert "real money disabled" in text
    assert "broker execution disabled" in text


def test_live_safety_lock_rejects_output_outside_reports(tmp_path):
    with pytest.raises(ValueError, match="reports/"):
        run_live_safety_lock(
            output_dir=tmp_path / "live_safety_lock",
            generated_at=_GENERATED_AT,
        )


def test_live_safety_lock_report_dict_is_json_safe():
    report = build_live_safety_lock_report(generated_at=_GENERATED_AT)

    payload = live_safety_lock_report_to_dict(report)

    assert payload["safety_lock_passed"] is True
    assert payload["live_trading_approved"] is False
    assert payload["allowed_underlyings"] == ["NIFTY"]
    assert payload["blocking_reasons"] == []


def test_live_safety_lock_format_is_trader_friendly():
    report = build_live_safety_lock_report(generated_at=_GENERATED_AT)

    text = format_live_safety_lock_report(report)

    assert "Hunter Quant Engine - Live Safety Lock" in text
    assert "disabled-by-default live safety scaffold" in text
    assert "this is not live trading" in text
    assert "real money disabled" in text
    assert "broker execution disabled" in text
    assert "real orders disabled" in text
    assert "safety lock passed: True" in text
    assert "live trading approved: False" in text


def test_live_safety_lock_main_prints_success(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert main() == 0

    out = capsys.readouterr().out

    assert "Live Safety Lock" in out
    assert "safety lock passed: True" in out
    assert "live trading approved: False" in out


def test_live_safety_lock_shortcut_points_to_safe_cli():
    text = Path("hqe_live_safety_lock_check.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "src.paper_trading.live_safety_lock" in text
    assert ".venv\\scripts\\python.exe" in text
    assert "this is not live trading" in text
    assert "real money remains disabled" in text
    assert "broker execution remains disabled" in text


def test_live_safety_lock_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/live_safety_lock.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def test_live_safety_lock_docs_define_disabled_boundary():
    text = Path("docs/LIVE_SAFETY_LOCK.md").read_text(encoding="utf-8")

    assert "It is not live trading." in text
    assert "It does not enable real money." in text
    assert "It does not enable broker execution." in text
    assert "It does not enable live market data." in text
    assert "It does not enable real orders." in text
    assert ".\\hqe_live_safety_lock_check.bat" in text
