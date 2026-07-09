from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hqe_fyers_data_only_connector import (  # noqa: E402
    BLOCKED_ORDER_APIS,
    BrokerExecutionBlockedError,
    FyersDataOnlyConfig,
    FyersDataOnlyConnector,
    guard_check_payload,
    write_local_config,
    write_workspace_evidence,
)


def test_order_api_methods_are_hard_blocked() -> None:
    connector = FyersDataOnlyConnector()
    for method_name in ["place_order", "modify_order", "cancel_order", "exit_positions", "orderbook", "positions", "funds"]:
        method = getattr(connector, method_name)
        with pytest.raises(BrokerExecutionBlockedError):
            method({"symbol": "NSE:NIFTY50-INDEX"})


def test_unsafe_config_flags_raise_blocked_error() -> None:
    with pytest.raises(BrokerExecutionBlockedError):
        FyersDataOnlyConfig(allow_order_api=True).validate()
    with pytest.raises(BrokerExecutionBlockedError):
        FyersDataOnlyConfig(allow_broker_execution=True).validate()
    with pytest.raises(BrokerExecutionBlockedError):
        FyersDataOnlyConfig(allow_auto_trading=True).validate()
    with pytest.raises(BrokerExecutionBlockedError):
        FyersDataOnlyConfig(allow_option_selling=True).validate()


def test_status_redacts_secret_values() -> None:
    env = {
        "FYERS_CLIENT_ID": "client-secret-value-123",
        "FYERS_ACCESS_TOKEN": "token-super-secret-456",
        "FYERS_REDIRECT_URI": "http://localhost/callback",
    }
    payload = FyersDataOnlyConnector(env=env).status(require_credentials=True)
    serialized = json.dumps(payload, sort_keys=True)
    assert "client-secret-value-123" not in serialized
    assert "token-super-secret-456" not in serialized
    assert payload["secrets"]["credentials_complete_for_future_data_transport"] is True
    assert payload["external_api_calls_executed"] is False
    assert payload["live_data_transport_started"] is False
    assert payload["order_api_block_status"] == "HARD_BLOCKED"


def test_write_local_config_excludes_secrets(tmp_path: Path) -> None:
    config_path = tmp_path / "fyers_data_only_config.json"
    payload = write_local_config(config_path, FyersDataOnlyConfig(market_symbol="NSE:NIFTY50-INDEX"))
    text = config_path.read_text(encoding="utf-8")
    assert config_path.exists()
    assert payload["mode"] == "DATA_ONLY"
    assert payload["secrets_included"] is False
    assert "password" not in text.lower()
    assert "token-super-secret" not in text
    assert payload["allow_order_api"] is False
    assert payload["allow_broker_execution"] is False


def test_preflight_without_env_is_safe_hold() -> None:
    connector = FyersDataOnlyConnector(env={})
    payload = connector.preflight(require_credentials=True)
    assert payload["preflight_status"] == "HOLD_WAITING_FOR_DATA_CREDENTIALS"
    assert payload["readiness_decision"] == "WAITING_FOR_FYERS_DATA_CREDENTIALS"
    assert payload["external_api_calls_executed"] is False
    assert payload["safety_lock"]["no_real_orders"] is True
    assert payload["safety_lock"]["order_api_hard_blocked"] is True


def test_workspace_evidence_files_are_written(tmp_path: Path) -> None:
    connector = FyersDataOnlyConnector(env={})
    payload = connector.preflight(require_credentials=False)
    files = write_workspace_evidence(tmp_path, payload)
    assert Path(files["json"]).exists()
    assert Path(files["markdown"]).exists()
    assert Path(files["ledger"]).exists()
    data = json.loads(Path(files["json"]).read_text(encoding="utf-8"))
    assert data["mode"] == "DATA_ONLY"
    assert data["order_api_block_status"] == "HARD_BLOCKED"
    ledger = Path(files["ledger"]).read_text(encoding="utf-8")
    assert "HARD_BLOCKED" in ledger


def test_guard_check_covers_blocked_api_list() -> None:
    payload = guard_check_payload()
    assert payload["guard_check_status"] == "PASS"
    assert set(payload["blocked_order_apis"].keys()) == set(BLOCKED_ORDER_APIS)
    assert all(value.endswith("HARD_BLOCKED") for value in payload["blocked_order_apis"].values())
