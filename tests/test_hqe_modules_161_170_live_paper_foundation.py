
from pathlib import Path
import csv
import importlib.util
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import hqe_live_paper_foundation_common as common


def test_all_modules_payload_pass_and_safety(tmp_path):
    for module_number in range(161, 171):
        payload = common.build_module_payload(module_number, tmp_path, write=False)
        status_key = common.MODULES[module_number]["status_key"]
        assert payload[status_key] == "PASS"
        assert payload["safety_lock"]["paper_only"] is True
        assert payload["safety_lock"]["no_real_money"] is True
        assert payload["safety_lock"]["no_broker_execution"] is True
        assert payload["safety_lock"]["no_real_orders"] is True
        assert payload["safety_lock"]["no_auto_trading"] is True
        assert payload["safety_lock"]["no_fake_trades"] is True
        assert payload["external_api_calls_executed"] is False
        assert payload["order_api_invoked"] is False
        assert payload["broker_execution_invoked"] is False
        assert payload["auto_trading_started"] is False
        assert payload["real_money_automatic"] is False


def test_secret_preflight_redacts_values(tmp_path, monkeypatch):
    monkeypatch.setenv("FYERS_CLIENT_ID", "client-abc")
    monkeypatch.setenv("FYERS_ACCESS_TOKEN", "super-secret-access-token-value")
    payload = common.build_module_payload(161, tmp_path, write=True)
    assert payload["secrets"]["credentials_complete_for_future_data_transport"] is True
    assert payload["secrets"]["secret_values_redacted"] is True
    text = (tmp_path / "MODULE_161_FYERS_SECRET_PREFLIGHT_STATUS.json").read_text(encoding="utf-8")
    assert "super-secret-access-token-value" not in text
    assert "client-abc" not in text


def test_candle_builder_writes_local_sample_without_trade_signal(tmp_path):
    payload = common.build_module_payload(164, tmp_path, write=True)
    sample = tmp_path / "FYERS_5M_NORMALIZED_SAMPLE.csv"
    assert sample.exists()
    assert payload["normalized_candle_rows_written"] == 1
    assert payload["live_market_data_used"] is False
    assert payload["trade_signal_generated"] is False
    rows = list(csv.DictReader(sample.open("r", encoding="utf-8")))
    assert rows[0]["datetime"] == "2026-07-09T09:15:00"


def test_paper_signal_logger_never_creates_fake_trades(tmp_path):
    signal_file = tmp_path / "DAY_001_FORWARD_SIGNAL_FEED.csv"
    signal_file.write_text(
        "signal_id,paper_signal_decision,symbol,ltp\n"
        "S1,PAPER_SIGNAL_APPROVED,NSE:NIFTY50-INDEX,25000\n",
        encoding="utf-8",
    )
    payload = common.build_module_payload(166, tmp_path, day_number=1, write=True)
    assert payload["approved_signal_rows"] == 1
    assert payload["explicit_paper_execution_rows_logged"] == 0
    assert payload["fake_trades_created"] is False
    execution_log = tmp_path / "DAY_001_PAPER_EXECUTION_LOG.csv"
    rows = list(csv.DictReader(execution_log.open("r", encoding="utf-8")))
    assert rows == []


def test_guard_check_blocks_all_order_apis():
    payload = common.guard_check_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["order_api_invoked"] is False
    assert payload["broker_execution_invoked"] is False
    assert payload["real_money_automatic"] is False
    for api in common.BLOCKED_ORDER_APIS:
        assert payload["blocked_order_apis"][api] == "ORDER_API_BLOCKED:HARD_BLOCKED"
