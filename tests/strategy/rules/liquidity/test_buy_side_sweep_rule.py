"""
Tests for BuySideSweepRule.
"""

from src.strategy.rules.liquidity.buy_side_sweep_rule import BuySideSweepRule
from tests.builders.models.liquidity_sweep_builder import LiquiditySweepBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_returns_only_buy_side_sweep_events():
    buy_side = LiquiditySweepBuilder().buy_side().build()
    sell_side = LiquiditySweepBuilder().sell_side().build()

    context = (
        StrategyContextBuilder()
        .with_liquidity_sweeps(buy_side, sell_side)
        .build()
    )

    result = BuySideSweepRule().evaluate(context)

    assert result == (buy_side,)


def test_returns_empty_tuple_when_no_buy_side_sweep_exists():
    sell_side = LiquiditySweepBuilder().sell_side().build()

    context = (
        StrategyContextBuilder()
        .with_liquidity_sweeps(sell_side)
        .build()
    )

    result = BuySideSweepRule().evaluate(context)

    assert result == ()


def test_returns_empty_tuple_when_context_has_no_liquidity_sweeps():
    context = StrategyContextBuilder().with_liquidity_sweeps().build()

    result = BuySideSweepRule().evaluate(context)

    assert result == ()
