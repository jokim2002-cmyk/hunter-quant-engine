"""
Option Chain Snapshot Tests
"""

from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType


def _contract(
    option_type,
    strike_price=24200.0,
    expiry_date=date(2026, 7, 9),
    underlying_symbol="NIFTY",
):
    return OptionContract(
        underlying_symbol=underlying_symbol,
        expiry_date=expiry_date,
        strike_price=strike_price,
        option_type=option_type,
        lot_size=65,
        symbol=f"{underlying_symbol}26JUL{int(strike_price)}{option_type.value}",
    )


def _entry(option_type, strike_price=24200.0, expiry_date=date(2026, 7, 9)):
    return OptionChainEntry(
        contract=_contract(
            option_type=option_type,
            strike_price=strike_price,
            expiry_date=expiry_date,
        ),
        last_traded_price=125.0,
        bid_price=124.0,
        ask_price=126.0,
        volume=10000,
        open_interest=50000,
    )


def test_option_chain_snapshot_stores_underlying_and_entries():
    timestamp = datetime(2026, 7, 3, 10, 15)
    ce_entry = _entry(OptionType.CE)
    pe_entry = _entry(OptionType.PE)

    snapshot = OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.5,
        timestamp=timestamp,
        entries=[ce_entry, pe_entry],
    )

    assert snapshot.underlying_symbol == "NIFTY"
    assert snapshot.underlying_price == 24210.5
    assert snapshot.timestamp == timestamp
    assert snapshot.entries == (ce_entry, pe_entry)


def test_option_chain_snapshot_filters_calls_and_puts():
    ce_entry = _entry(OptionType.CE)
    pe_entry = _entry(OptionType.PE)

    snapshot = OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.5,
        timestamp=datetime(2026, 7, 3, 10, 15),
        entries=(ce_entry, pe_entry),
    )

    assert snapshot.calls == (ce_entry,)
    assert snapshot.puts == (pe_entry,)
    assert snapshot.entries_for_type(OptionType.CE) == (ce_entry,)
    assert snapshot.entries_for_type(OptionType.PE) == (pe_entry,)


def test_option_chain_snapshot_filters_by_expiry():
    first_expiry = date(2026, 7, 9)
    second_expiry = date(2026, 7, 16)
    first_entry = _entry(OptionType.CE, expiry_date=first_expiry)
    second_entry = _entry(OptionType.CE, expiry_date=second_expiry)

    snapshot = OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.5,
        timestamp=datetime(2026, 7, 3, 10, 15),
        entries=(first_entry, second_entry),
    )

    assert snapshot.entries_for_expiry(first_expiry) == (first_entry,)
    assert snapshot.entries_for_expiry(second_expiry) == (second_entry,)


def test_option_chain_snapshot_is_immutable():
    snapshot = OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.5,
        timestamp=datetime(2026, 7, 3, 10, 15),
        entries=(),
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.underlying_price = 24250.0


@pytest.mark.parametrize(
    "field_name,field_value,error_message",
    [
        ("underlying_symbol", "", "underlying_symbol is required"),
        (
            "underlying_price",
            0.0,
            "underlying_price must be greater than 0",
        ),
    ],
)
def test_option_chain_snapshot_rejects_invalid_fields(
    field_name,
    field_value,
    error_message,
):
    values = {
        "underlying_symbol": "NIFTY",
        "underlying_price": 24210.5,
        "timestamp": datetime(2026, 7, 3, 10, 15),
        "entries": (),
    }
    values[field_name] = field_value

    with pytest.raises(ValueError, match=error_message):
        OptionChainSnapshot(**values)


def test_option_chain_snapshot_rejects_mismatched_underlying():
    banknifty_entry = OptionChainEntry(
        contract=_contract(
            option_type=OptionType.CE,
            underlying_symbol="BANKNIFTY",
        ),
        last_traded_price=125.0,
    )

    with pytest.raises(
        ValueError,
        match="entry contract underlying_symbol must match snapshot",
    ):
        OptionChainSnapshot(
            underlying_symbol="NIFTY",
            underlying_price=24210.5,
            timestamp=datetime(2026, 7, 3, 10, 15),
            entries=(banknifty_entry,),
        )
