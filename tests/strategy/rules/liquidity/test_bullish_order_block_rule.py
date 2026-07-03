"""
Tests for BullishOrderBlockRule.
"""

from src.strategy.rules.liquidity.bullish_order_block_rule import BullishOrderBlockRule
from tests.builders.models.order_block_builder import OrderBlockBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_returns_only_bullish_order_block_events():
    bullish = OrderBlockBuilder().bullish().build()
    bearish = OrderBlockBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_order_blocks(bullish, bearish)
        .build()
    )

    result = BullishOrderBlockRule().evaluate(context)

    assert result == (bullish,)


def test_returns_empty_tuple_when_no_bullish_order_block_exists():
    bearish = OrderBlockBuilder().bearish().build()

    context = (
        StrategyContextBuilder()
        .with_order_blocks(bearish)
        .build()
    )

    result = BullishOrderBlockRule().evaluate(context)

    assert result == ()


def test_returns_empty_tuple_when_context_has_no_order_blocks():
    context = StrategyContextBuilder().with_order_blocks().build()

    result = BullishOrderBlockRule().evaluate(context)

    assert result == ()
