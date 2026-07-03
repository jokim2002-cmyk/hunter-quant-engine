from dataclasses import FrozenInstanceError

import pytest

from src.models.liquidity_sweep import LiquiditySweep
from src.models.liquidity_sweep_type import LiquiditySweepType


def test_create_high_liquidity_sweep():
    sweep = LiquiditySweep(
        candle_index=10,
        liquidity_index=5,
        sweep_price=105.50,
        liquidity_price=105.00,
        break_distance=0.50,
        reclaimed=True,
        sweep_type=LiquiditySweepType.HIGH,
        created_at=10,
    )

    assert sweep.candle_index == 10
    assert sweep.liquidity_index == 5
    assert sweep.sweep_price == 105.50
    assert sweep.liquidity_price == 105.00
    assert sweep.break_distance == 0.50
    assert sweep.reclaimed is True
    assert sweep.sweep_type == LiquiditySweepType.HIGH
    assert sweep.created_at == 10


def test_create_low_liquidity_sweep():
    sweep = LiquiditySweep(
        candle_index=20,
        liquidity_index=12,
        sweep_price=94.50,
        liquidity_price=95.00,
        break_distance=0.50,
        reclaimed=True,
        sweep_type=LiquiditySweepType.LOW,
        created_at=20,
    )

    assert sweep.sweep_type == LiquiditySweepType.LOW
    assert sweep.break_distance == 0.50
    assert sweep.reclaimed is True


def test_create_unreclaimed_liquidity_sweep():
    sweep = LiquiditySweep(
        candle_index=30,
        liquidity_index=18,
        sweep_price=110.20,
        liquidity_price=110.00,
        break_distance=0.20,
        reclaimed=False,
        sweep_type=LiquiditySweepType.HIGH,
        created_at=30,
    )

    assert sweep.reclaimed is False


def test_liquidity_sweep_is_immutable():
    sweep = LiquiditySweep(
        candle_index=1,
        liquidity_index=0,
        sweep_price=101.0,
        liquidity_price=100.0,
        break_distance=1.0,
        reclaimed=True,
        sweep_type=LiquiditySweepType.HIGH,
        created_at=1,
    )

    with pytest.raises(FrozenInstanceError):
        sweep.break_distance = 2.0