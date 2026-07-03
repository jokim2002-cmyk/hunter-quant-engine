"""
Tests for SellSideSweepRule.
"""

from src.strategy.rules.liquidity.sell_side_sweep_rule import SellSideSweepRule
from tests.builders.models.liquidity_sweep_builder import LiquiditySweepBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def test_returns_only_sell_side_sweep_events():
    buy_side = LiquiditySweepBuilder().buy_side().build()
    sell_side = LiquiditySweepBuilder().sell_side().build()

    context = (
        StrategyContextBuilder()
        .with_liquidity_sweeps(buy_side, sell_side)
        .build()
    )

    result = SellSideSweepRule().evaluate(context)

    assert result == (sell_side,)


def test_returns_empty_tuple_when_no_sell_side_sweep_exists():
    buy_side = LiquiditySweepBuilder().buy_side().build()

    context = (
        StrategyContextBuilder()
        .with_liquidity_sweeps(buy_side)
        .build()
    )

    result = SellSideSweepRule().evaluate(context)

    assert result == ()


def test_returns_empty_tuple_when_context_has_no_liquidity_sweeps():
    context = StrategyContextBuilder().with_liquidity_sweeps().build()

    result = SellSideSweepRule().evaluate(context)

    assert result == ()
