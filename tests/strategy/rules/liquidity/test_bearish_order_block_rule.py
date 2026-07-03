"""
Tests for BearishOrderBlockRule.
"""

from src.strategy.rules.liquidity.bearish_order_block_rule import BearishOrderBlockRule
from tests.builders.models.order_block_builder import OrderBlockBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_returns_only_bearish_order_block_events():
    bullish = OrderBlockBuilder().bullish().build()
    bearish = OrderBlockBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_order_blocks(bullish, bearish)
        .build()
    )

    result = BearishOrderBlockRule().evaluate(context)

    assert result == (bearish,)


def test_returns_empty_tuple_when_no_bearish_order_block_exists():
    bullish = OrderBlockBuilder().bullish().build()

    context = (
        StrategyContextBuilder()
        .with_order_blocks(bullish)
        .build()
    )

    result = BearishOrderBlockRule().evaluate(context)

    assert result == ()


def test_returns_empty_tuple_when_context_has_no_order_blocks():
    context = StrategyContextBuilder().with_order_blocks().build()

    result = BearishOrderBlockRule().evaluate(context)

    assert result == ()
