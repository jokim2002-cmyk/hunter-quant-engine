from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_fyers_option_chain_data_only.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "hqe_fyers_option_chain_data_only",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def optionchain(self, *, data):
        self.calls.append(dict(data))
        return self.response


def sample_response():
    return {
        "s": "ok",
        "code": 200,
        "message": "",
        "data": {
            "expiryData": [
                {
                    "expiry": "2026-07-16",
                    "date": "2026-07-16",
                }
            ],
            "optionsChain": [
                {
                    "symbol": "NSE:NIFTY26JUL25000CE",
                    "option_type": "CE",
                    "strike_price": 25000,
                    "ltp": 120.5,
                    "bid": 120.0,
                    "ask": 121.0,
                    "oi": 10000,
                    "volume": 5000,
                },
                {
                    "symbol": "NSE:NIFTY26JUL25000PE",
                    "option_type": "PE",
                    "strike_price": 25000,
                    "ltp": 110.0,
                    "bid": 109.5,
                    "ask": 110.5,
                    "oi": 12000,
                    "volume": 6000,
                },
            ],
        },
    }


def test_guard_check_is_data_only():
    module = load_module()
    payload = module.build_guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["live_api_call_performed"] is False
    assert payload["order_api_available_to_module"] is False
    assert payload["safety_lock"]["no_real_orders"] is True
    assert payload["safety_lock"]["no_broker_execution"] is True


def test_normalize_chain_maps_both_buy_sides():
    module = load_module()
    rows = module.normalize_chain(
        sample_response(),
        underlying_symbol="NSE:NIFTY50-INDEX",
        trading_date="2026-07-13",
        generated_at_utc="2026-07-13T16:00:00+00:00",
    )
    assert len(rows) == 2
    assert {row["option_type"] for row in rows} == {"CE", "PE"}
    assert {row["signal_side"] for row in rows} == {
        "CE_BUY",
        "PE_BUY",
    }
    assert {row["dte"] for row in rows} == {3}

    readiness = module.chain_readiness(rows)
    assert readiness["status"] == "BOTH_SIDES_READY"
    assert readiness["both_sides_ready"] is True


def test_live_data_only_writes_truthful_snapshot(tmp_path):
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    client = FakeClient(sample_response())
    payload = module.run_live_data_only(
        workspace=workspace,
        symbol="NSE:NIFTY50-INDEX",
        trading_date="2026-07-13",
        strike_count=20,
        expiry_timestamp="",
        client=client,
        env={},
    )

    assert client.calls == [
        {
            "symbol": "NSE:NIFTY50-INDEX",
            "strikecount": 20,
            "timestamp": "",
        }
    ]
    assert payload["readiness"]["both_sides_ready"] is True
    assert payload["recorded_data_replay_ready"] is False
    assert payload["historical_premium_candles_ready"] is False
    assert payload["next_required_step"] == (
        "FETCH_SELECTED_CE_PE_HISTORICAL_5M_CANDLES"
    )
    assert payload["real_orders_allowed"] is False

    csv_path = Path(payload["premium_csv"])
    snapshot_path = Path(payload["snapshot_json"])
    assert csv_path.exists()
    assert snapshot_path.exists()

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert {row["signal_side"] for row in rows} == {
        "CE_BUY",
        "PE_BUY",
    }

    snapshot = json.loads(
        snapshot_path.read_text(encoding="utf-8")
    )
    assert "FYERS_ACCESS_TOKEN" not in json.dumps(snapshot)
    assert snapshot["readiness"]["status"] == "BOTH_SIDES_READY"


def test_incomplete_chain_is_blocked_not_fabricated(tmp_path):
    module = load_module()
    response = sample_response()
    response["data"]["optionsChain"] = [
        response["data"]["optionsChain"][0]
    ]
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    payload = module.run_live_data_only(
        workspace=workspace,
        symbol="NSE:NIFTY50-INDEX",
        trading_date="2026-07-13",
        strike_count=10,
        expiry_timestamp="",
        client=FakeClient(response),
        env={},
    )

    assert payload["readiness"]["status"] == (
        "OPTION_CHAIN_INCOMPLETE"
    )
    assert payload["readiness"]["ce_count"] == 1
    assert payload["readiness"]["pe_count"] == 0
    assert payload["recorded_data_replay_ready"] is False
    assert payload["next_required_step"] == (
        "REPAIR_OR_REFRESH_OPTION_CHAIN_DATA"
    )


def test_source_has_no_order_execution_calls():
    text = SCRIPT.read_text(encoding="utf-8-sig")
    forbidden = (
        ".place_order(",
        ".submit_order(",
        ".modify_order(",
        ".cancel_order(",
        ".exit_positions(",
    )
    assert not any(marker in text for marker in forbidden)
    assert ".optionchain(" in text
