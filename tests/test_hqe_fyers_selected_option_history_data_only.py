from __future__ import annotations

import csv
import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO
    / "scripts"
    / "hqe_fyers_selected_option_history_data_only.py"
)
IST = ZoneInfo("Asia/Kolkata")


def load_module():
    spec = importlib.util.spec_from_file_location(
        "hqe_fyers_selected_option_history_data_only",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def epoch_ist(value: str) -> int:
    dt = datetime.fromisoformat(value).replace(tzinfo=IST)
    return int(dt.timestamp())


def chain_rows():
    return [
        {
            "symbol": "NSE:NIFTY26JUL25000CE",
            "option_type": "CE",
            "signal_side": "CE_BUY",
            "strike_price": "25000",
            "ltp": "120",
            "volume": "5000",
            "oi": "10000",
            "expiry_timestamp": "2026-07-16",
            "dte": "3",
        },
        {
            "symbol": "NSE:NIFTY26JUL25000PE",
            "option_type": "PE",
            "signal_side": "PE_BUY",
            "strike_price": "25000",
            "ltp": "115",
            "volume": "6000",
            "oi": "12000",
            "expiry_timestamp": "2026-07-16",
            "dte": "3",
        },
        {
            "symbol": "NSE:NIFTY26JUL25100CE",
            "option_type": "CE",
            "signal_side": "CE_BUY",
            "strike_price": "25100",
            "ltp": "60",
            "volume": "4000",
            "oi": "9000",
            "expiry_timestamp": "2026-07-16",
            "dte": "3",
        },
        {
            "symbol": "NSE:NIFTY26JUL25100PE",
            "option_type": "PE",
            "signal_side": "PE_BUY",
            "strike_price": "25100",
            "ltp": "180",
            "volume": "4500",
            "oi": "9500",
            "expiry_timestamp": "2026-07-16",
            "dte": "3",
        },
    ]


class FakeClient:
    def __init__(self):
        self.calls = []

    def history(self, *, data):
        self.calls.append(dict(data))
        base = 120 if data["symbol"].endswith("CE") else 110
        return {
            "s": "ok",
            "code": 200,
            "candles": [
                [
                    epoch_ist("2026-07-13 09:15:00"),
                    base,
                    base + 5,
                    base - 4,
                    base + 2,
                    1000,
                ],
                [
                    epoch_ist("2026-07-13 09:20:00"),
                    base + 2,
                    base + 7,
                    base,
                    base + 4,
                    1200,
                ],
            ],
        }


def write_chain(path: Path) -> None:
    rows = chain_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_pair_selection_prefers_same_strike_balanced_premium():
    module = load_module()
    selected = module.select_ce_pe_pair(chain_rows())
    assert selected["strike_price"] == 25000.0
    assert selected["ce"]["signal_side"] == "CE_BUY"
    assert selected["pe"]["signal_side"] == "PE_BUY"
    assert selected["dte"] == 3


def test_history_request_is_single_symbol_five_minute():
    module = load_module()
    request = module.history_request(
        symbol="NSE:NIFTY26JUL25000CE",
        trading_date="2026-07-13",
    )
    assert request == {
        "symbol": "NSE:NIFTY26JUL25000CE",
        "resolution": "5",
        "date_format": "1",
        "range_from": "2026-07-13",
        "range_to": "2026-07-13",
        "cont_flag": "1",
    }


def test_live_data_only_fetches_both_sides_and_writes_csv(tmp_path):
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    chain = (
        workspace
        / "HQE_CURRENT_DAY_OPTION_DATA"
        / "2026-07-13"
        / "FYERS_NIFTY_OPTION_CHAIN_PREMIUM_SNAPSHOT.csv"
    )
    write_chain(chain)

    client = FakeClient()
    payload = module.run_live_data_only(
        workspace=workspace,
        trading_date="2026-07-13",
        client=client,
        env={},
    )

    assert payload["status"] == (
        "SELECTED_CE_PE_HISTORY_5M_READY"
    )
    assert payload["rows"] == {
        "ce": 2,
        "pe": 2,
        "combined": 4,
    }
    assert payload["recorded_data_replay_ready"] is False
    assert payload["supervisor_wired"] is False
    assert payload["real_orders_allowed"] is False
    assert len(client.calls) == 2
    assert {
        call["symbol"][-2:]
        for call in client.calls
    } == {"CE", "PE"}

    combined = Path(payload["outputs"]["combined_csv"])
    with combined.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 4
    assert {row["signal_side"] for row in rows} == {
        "CE_BUY",
        "PE_BUY",
    }
    assert {row["dte"] for row in rows} == {"3"}
    assert all(row["source"] == "FYERS_HISTORY_5M_DATA_ONLY" for row in rows)


def test_missing_one_side_is_failed_safe():
    module = load_module()
    only_ce = [
        row for row in chain_rows()
        if row["signal_side"] == "CE_BUY"
    ]
    try:
        module.select_ce_pe_pair(only_ce)
    except module.SelectedOptionHistoryError as exc:
        assert "No same-expiry, same-strike CE/PE pair" in str(exc)
    else:
        raise AssertionError("Incomplete chain was incorrectly accepted.")


def test_source_has_no_order_calls():
    text = SCRIPT.read_text(encoding="utf-8-sig")
    forbidden = (
        ".place_order(",
        ".submit_order(",
        ".modify_order(",
        ".cancel_order(",
        ".exit_positions(",
    )
    assert not any(marker in text for marker in forbidden)
    assert ".history(" in text
