"""
Option Chain Entry Tests
"""

from datetime import date

import pytest

from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_greeks import OptionGreeks
from src.models.option_type import OptionType


def _contract(option_type=OptionType.CE):
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=option_type,
        lot_size=65,
        symbol=f"NIFTY26JUL24200{option_type.value}",
    )


def test_option_chain_entry_stores_market_data():
    greeks = OptionGreeks(
        delta=0.52,
        theta=-4.25,
        vega=8.1,
        gamma=0.02,
        implied_volatility=14.5,
    )
    entry = OptionChainEntry(
        contract=_contract(),
        last_traded_price=125.0,
        bid_price=124.0,
        ask_price=126.0,
        volume=12000,
        open_interest=85000,
        greeks=greeks,
    )

    assert entry.contract.option_type == OptionType.CE
    assert entry.option_type == OptionType.CE
    assert entry.last_traded_price == 125.0
    assert entry.bid_price == 124.0
    assert entry.ask_price == 126.0
    assert entry.volume == 12000
    assert entry.open_interest == 85000
    assert entry.greeks == greeks
    assert entry.has_bid_ask_quote is True
    assert entry.spread == 2.0
    assert entry.mid_price == 125.0
    assert entry.is_call is True
    assert entry.is_put is False


def test_option_chain_entry_handles_missing_bid_ask_quote():
    entry = OptionChainEntry(
        contract=_contract(OptionType.PE),
        last_traded_price=115.0,
        volume=5000,
        open_interest=30000,
    )

    assert entry.has_bid_ask_quote is False
    assert entry.spread is None
    assert entry.mid_price is None
    assert entry.is_call is False
    assert entry.is_put is True


@pytest.mark.parametrize(
    "field_name,field_value,error_message",
    [
        (
            "last_traded_price",
            0.0,
            "last_traded_price must be greater than 0",
        ),
        ("bid_price", -1.0, "bid_price must not be negative"),
        ("ask_price", -1.0, "ask_price must not be negative"),
        ("volume", -1, "volume must not be negative"),
        ("open_interest", -1, "open_interest must not be negative"),
    ],
)
def test_option_chain_entry_rejects_invalid_market_data(
    field_name,
    field_value,
    error_message,
):
    values = {
        "contract": _contract(),
        "last_traded_price": 125.0,
        "bid_price": 124.0,
        "ask_price": 126.0,
        "volume": 12000,
        "open_interest": 85000,
    }
    values[field_name] = field_value

    with pytest.raises(ValueError, match=error_message):
        OptionChainEntry(**values)


def test_option_chain_entry_rejects_ask_below_bid():
    with pytest.raises(
        ValueError,
        match="ask_price must be greater than or equal to bid_price",
    ):
        OptionChainEntry(
            contract=_contract(),
            last_traded_price=125.0,
            bid_price=126.0,
            ask_price=124.0,
        )
