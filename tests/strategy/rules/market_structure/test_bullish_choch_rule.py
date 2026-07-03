"""
Tests for BullishCHOCHRule.
"""

from src.strategy.rules.market_structure.bullish_choch_rule import BullishCHOCHRule
from tests.builders.models.choch_builder import CHOCHBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_returns_only_bullish_choch_events():
    bullish = CHOCHBuilder().bullish().build()
    bearish = CHOCHBuilder().bearish().build()

    context = StrategyContextBuilder()\
        .with_choch(bullish, bearish)\
        .build()

    result = BullishCHOCHRule().evaluate(context)

    assert result == (bullish,)


def test_returns_empty_tuple_when_no_bullish_choch_exists():
    bearish = CHOCHBuilder().bearish().build()

    context = StrategyContextBuilder()\
        .with_choch(bearish)\
        .build()

    result = BullishCHOCHRule().evaluate(context)

    assert result == ()


def test_returns_all_bullish_choch_events():
    first_bullish = CHOCHBuilder().bullish().at_index(1).build()
    second_bullish = CHOCHBuilder().bullish().at_index(2).build()

    context = StrategyContextBuilder()\
        .with_choch(first_bullish, second_bullish)\
        .build()

    result = BullishCHOCHRule().evaluate(context)

    assert result == (first_bullish, second_bullish)
