"""
Tests for PriceFillResult.
"""

from dataclasses import FrozenInstanceError

import pytest

from src.backtesting.price_fill_result import PriceFillResult


def test_price_fill_result_can_be_created_for_filled_trade():
    result = PriceFillResult(
        filled=True,
        fill_price=110.0,
        reason="take_profit",
    )

    assert result.filled is True
    assert result.fill_price == 110.0
    assert result.reason == "take_profit"


def test_price_fill_result_can_be_created_for_unfilled_trade():
    result = PriceFillResult(
        filled=False,
        fill_price=None,
        reason=None,
    )

    assert result.filled is False
    assert result.fill_price is None
    assert result.reason is None


def test_price_fill_result_is_immutable():
    result = PriceFillResult(
        filled=False,
        fill_price=None,
        reason=None,
    )

    with pytest.raises(FrozenInstanceError):
        result.filled = True
