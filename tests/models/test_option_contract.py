"""
Option Contract Tests
"""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from src.models.option_contract import OptionContract
from src.models.option_type import OptionType


def test_option_contract_stores_nifty_option_fields():
    contract = OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol="NIFTY26JUL24200CE",
    )

    assert contract.underlying_symbol == "NIFTY"
    assert contract.expiry_date == date(2026, 7, 9)
    assert contract.strike_price == 24200.0
    assert contract.option_type == OptionType.CE
    assert contract.lot_size == 65
    assert contract.symbol == "NIFTY26JUL24200CE"


def test_option_contract_is_immutable():
    contract = OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.PE,
        lot_size=65,
        symbol="NIFTY26JUL24200PE",
    )

    with pytest.raises(FrozenInstanceError):
        contract.strike_price = 24100.0


def test_option_contract_calculates_quantity_for_lots():
    contract = OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol="NIFTY26JUL24200CE",
    )

    assert contract.quantity_for_lots(1) == 65
    assert contract.quantity_for_lots(2) == 130


@pytest.mark.parametrize(
    "field_name,field_value,error_message",
    [
        ("underlying_symbol", "", "underlying_symbol is required"),
        ("strike_price", 0.0, "strike_price must be greater than 0"),
        ("lot_size", 0, "lot_size must be greater than 0"),
        ("symbol", "", "symbol is required"),
    ],
)
def test_option_contract_rejects_invalid_fields(
    field_name,
    field_value,
    error_message,
):
    values = {
        "underlying_symbol": "NIFTY",
        "expiry_date": date(2026, 7, 9),
        "strike_price": 24200.0,
        "option_type": OptionType.CE,
        "lot_size": 65,
        "symbol": "NIFTY26JUL24200CE",
    }
    values[field_name] = field_value

    with pytest.raises(ValueError, match=error_message):
        OptionContract(**values)


def test_option_contract_rejects_non_positive_lots():
    contract = OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol="NIFTY26JUL24200CE",
    )

    with pytest.raises(ValueError, match="lots must be greater than 0"):
        contract.quantity_for_lots(0)
