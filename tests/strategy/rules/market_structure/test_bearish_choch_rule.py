"""
Tests for BearishCHOCHRule.
"""

from src.strategy.rules.market_structure.bearish_choch_rule import BearishCHOCHRule
from tests.builders.models.choch_builder import CHOCHBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_returns_only_bearish_choch_events():
    bullish = CHOCHBuilder().bullish().build()
    bearish = CHOCHBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_choch(bullish, bearish)
        .build()
    )

    result = BearishCHOCHRule().evaluate(context)

    assert result == (bearish,)


def test_returns_empty_tuple_when_no_bearish_choch_exists():
    bullish = CHOCHBuilder().bullish().build()

    context = (
        StrategyContextBuilder()
        .with_choch(bullish)
        .build()
    )

    result = BearishCHOCHRule().evaluate(context)

    assert result == ()


def test_returns_all_bearish_choch_events():
    first = CHOCHBuilder().bearish().at_index(1).build()
    second = CHOCHBuilder().bearish().at_index(2).build()

    context = (
        StrategyContextBuilder()
        .with_choch(first, second)
        .build()
    )

    result = BearishCHOCHRule().evaluate(context)

    assert result == (first, second)
