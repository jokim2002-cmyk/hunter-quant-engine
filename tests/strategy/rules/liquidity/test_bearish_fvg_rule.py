"""
Tests for BearishFVGRule.
"""

from src.strategy.rules.liquidity.bearish_fvg_rule import BearishFVGRule
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_returns_only_bearish_fair_value_gap_events():
    bullish = FairValueGapBuilder().bullish().build()
    bearish = FairValueGapBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_fair_value_gaps(bullish, bearish)
        .build()
    )

    result = BearishFVGRule().evaluate(context)

    assert result == (bearish,)


def test_returns_empty_tuple_when_no_bearish_fair_value_gap_exists():
    bullish = FairValueGapBuilder().bullish().build()

    context = (
        StrategyContextBuilder()
        .with_fair_value_gaps(bullish)
        .build()
    )

    result = BearishFVGRule().evaluate(context)

    assert result == ()


def test_returns_empty_tuple_when_context_has_no_fair_value_gaps():
    context = StrategyContextBuilder().with_fair_value_gaps().build()

    result = BearishFVGRule().evaluate(context)

    assert result == ()
