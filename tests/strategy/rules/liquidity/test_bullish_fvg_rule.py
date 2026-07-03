"""
Tests for BullishFVGRule.
"""

from src.strategy.rules.liquidity.bullish_fvg_rule import BullishFVGRule
from tests.builders.models.fair_value_gap_builder import FairValueGapBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_returns_only_bullish_fair_value_gap_events():
    bullish = FairValueGapBuilder().bullish().build()
    bearish = FairValueGapBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_fair_value_gaps(bullish, bearish)
        .build()
    )

    result = BullishFVGRule().evaluate(context)

    assert result == (bullish,)


def test_returns_empty_tuple_when_no_bullish_fair_value_gap_exists():
    bearish = FairValueGapBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_fair_value_gaps(bearish)
        .build()
    )

    result = BullishFVGRule().evaluate(context)

    assert result == ()


def test_returns_empty_tuple_when_context_has_no_fair_value_gaps():
    context = StrategyContextBuilder().with_fair_value_gaps().build()

    result = BullishFVGRule().evaluate(context)

    assert result == ()
