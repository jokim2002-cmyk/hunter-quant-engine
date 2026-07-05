"""
Option Greeks Tests
"""

import pytest

from src.models.option_greeks import OptionGreeks


def test_option_greeks_store_values():
    greeks = OptionGreeks(
        delta=0.52,
        theta=-4.25,
        vega=8.1,
        gamma=0.02,
        implied_volatility=14.5,
    )

    assert greeks.delta == 0.52
    assert greeks.theta == -4.25
    assert greeks.vega == 8.1
    assert greeks.gamma == 0.02
    assert greeks.implied_volatility == 14.5
    assert greeks.is_complete is True
    assert greeks.has_missing_values is False


def test_option_greeks_allow_missing_values():
    greeks = OptionGreeks(delta=0.45)

    assert greeks.delta == 0.45
    assert greeks.theta is None
    assert greeks.is_complete is False
    assert greeks.has_missing_values is True


@pytest.mark.parametrize(
    "field_name,field_value,error_message",
    [
        ("delta", 1.5, "delta must be between -1 and 1"),
        ("vega", -0.1, "vega must not be negative"),
        ("gamma", -0.1, "gamma must not be negative"),
        (
            "implied_volatility",
            -1.0,
            "implied_volatility must not be negative",
        ),
    ],
)
def test_option_greeks_reject_invalid_values(
    field_name,
    field_value,
    error_message,
):
    values = {
        "delta": 0.5,
        "theta": -3.0,
        "vega": 5.0,
        "gamma": 0.01,
        "implied_volatility": 12.0,
    }
    values[field_name] = field_value

    with pytest.raises(ValueError, match=error_message):
        OptionGreeks(**values)
