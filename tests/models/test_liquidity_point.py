from datetime import datetime

from src.models.liquidity_point import LiquidityPoint, LiquidityType
from src.models.swing_point import SwingPoint, SwingPointType


def make_swing_point(swing_type):
    return SwingPoint(
        index=1,
        timestamp=datetime(2026, 1, 1, 9, 15),
        price=100.0,
        swing_type=swing_type,
    )


def test_liquidity_point_identifies_buy_side_liquidity():
    swing = make_swing_point(SwingPointType.SWING_HIGH)

    liquidity = LiquidityPoint(
        index=1,
        timestamp=swing.timestamp,
        price=swing.price,
        liquidity_type=LiquidityType.BUY_SIDE,
        source_swing=swing,
    )

    assert liquidity.is_buy_side() is True
    assert liquidity.is_sell_side() is False


def test_liquidity_point_identifies_sell_side_liquidity():
    swing = make_swing_point(SwingPointType.SWING_LOW)

    liquidity = LiquidityPoint(
        index=1,
        timestamp=swing.timestamp,
        price=swing.price,
        liquidity_type=LiquidityType.SELL_SIDE,
        source_swing=swing,
    )

    assert liquidity.is_sell_side() is True
    assert liquidity.is_buy_side() is False


def test_liquidity_point_keeps_source_swing():
    swing = make_swing_point(SwingPointType.SWING_HIGH)

    liquidity = LiquidityPoint(
        index=1,
        timestamp=swing.timestamp,
        price=swing.price,
        liquidity_type=LiquidityType.BUY_SIDE,
        source_swing=swing,
    )

    assert liquidity.source_swing == swing
