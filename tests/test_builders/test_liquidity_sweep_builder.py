"""
Tests for LiquiditySweepBuilder.
"""

from src.models.liquidity_sweep_type import LiquiditySweepType
from tests.builders.models.liquidity_sweep_builder import LiquiditySweepBuilder


def test_builds_default_liquidity_sweep():
    sweep = LiquiditySweepBuilder().build()

    assert sweep.candle_index == 10
    assert sweep.liquidity_index == 5
    assert sweep.sweep_price == 101.0
    assert sweep.liquidity_price == 100.0
    assert sweep.break_distance == 1.0
    assert sweep.reclaimed is True
    assert sweep.sweep_type == LiquiditySweepType.HIGH
    assert sweep.created_at == 10


def test_builds_buy_side_liquidity_sweep():
    sweep = LiquiditySweepBuilder().buy_side().build()

    assert sweep.is_buy_side() is True
    assert sweep.is_sell_side() is False


def test_builds_sell_side_liquidity_sweep():
    sweep = LiquiditySweepBuilder().sell_side().build()

    assert sweep.is_sell_side() is True
    assert sweep.is_buy_side() is False


def test_builds_unreclaimed_liquidity_sweep():
    sweep = LiquiditySweepBuilder().not_reclaimed().build()

    assert sweep.reclaimed is False


def test_builds_custom_liquidity_sweep():
    sweep = (
        LiquiditySweepBuilder()
        .sell_side()
        .not_reclaimed()
        .at_candle(20)
        .with_liquidity_index(12)
        .at_sweep_price(94.5)
        .at_liquidity_price(95.0)
        .with_break_distance(0.5)
        .created_at(21)
        .build()
    )

    assert sweep.candle_index == 20
    assert sweep.liquidity_index == 12
    assert sweep.sweep_price == 94.5
    assert sweep.liquidity_price == 95.0
    assert sweep.break_distance == 0.5
    assert sweep.reclaimed is False
    assert sweep.sweep_type == LiquiditySweepType.LOW
    assert sweep.created_at == 21
