from datetime import datetime, timedelta

from src.config.liquidity_config import LiquidityConfig
from src.engines.liquidity_engine import LiquidityEngine
from src.models.liquidity_point import LiquidityType
from src.models.market_structure import MarketStructurePoint, MarketStructureType
from src.models.swing_point import SwingPoint, SwingPointType


def make_swing_point(index, price, swing_type):
    return SwingPoint(
        index=index,
        timestamp=datetime(2026, 1, 1, 9, 15) + timedelta(minutes=5 * index),
        price=price,
        swing_type=swing_type,
    )


def make_market_structure_point(index, price, swing_type, structure_type):
    swing = make_swing_point(index, price, swing_type)

    return MarketStructurePoint(
        swing_point=swing,
        structure_type=structure_type,
    )


def test_liquidity_engine_returns_empty_when_disabled():
    engine = LiquidityEngine(config=LiquidityConfig(enabled=False))

    result = engine.detect_liquidity([])

    assert result == []


def test_liquidity_engine_creates_buy_side_liquidity_from_highs():
    points = [
        make_market_structure_point(
            index=1,
            price=110.0,
            swing_type=SwingPointType.SWING_HIGH,
            structure_type=MarketStructureType.HIGHER_HIGH,
        ),
        make_market_structure_point(
            index=2,
            price=105.0,
            swing_type=SwingPointType.SWING_HIGH,
            structure_type=MarketStructureType.LOWER_HIGH,
        ),
    ]

    engine = LiquidityEngine()

    result = engine.detect_liquidity(points)

    assert len(result) == 2
    assert result[0].liquidity_type == LiquidityType.BUY_SIDE
    assert result[1].liquidity_type == LiquidityType.BUY_SIDE
    assert result[0].is_buy_side() is True
    assert result[1].is_buy_side() is True


def test_liquidity_engine_creates_sell_side_liquidity_from_lows():
    points = [
        make_market_structure_point(
            index=1,
            price=95.0,
            swing_type=SwingPointType.SWING_LOW,
            structure_type=MarketStructureType.HIGHER_LOW,
        ),
        make_market_structure_point(
            index=2,
            price=90.0,
            swing_type=SwingPointType.SWING_LOW,
            structure_type=MarketStructureType.LOWER_LOW,
        ),
    ]

    engine = LiquidityEngine()

    result = engine.detect_liquidity(points)

    assert len(result) == 2
    assert result[0].liquidity_type == LiquidityType.SELL_SIDE
    assert result[1].liquidity_type == LiquidityType.SELL_SIDE
    assert result[0].is_sell_side() is True
    assert result[1].is_sell_side() is True


def test_liquidity_engine_keeps_source_swing_data():
    point = make_market_structure_point(
        index=3,
        price=120.0,
        swing_type=SwingPointType.SWING_HIGH,
        structure_type=MarketStructureType.HIGHER_HIGH,
    )

    engine = LiquidityEngine()

    result = engine.detect_liquidity([point])

    assert len(result) == 1
    assert result[0].index == point.swing_point.index
    assert result[0].timestamp == point.swing_point.timestamp
    assert result[0].price == point.swing_point.price
    assert result[0].source_swing == point.swing_point
