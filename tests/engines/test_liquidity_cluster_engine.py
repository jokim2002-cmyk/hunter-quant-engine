from datetime import datetime, timedelta

from src.engines.liquidity_cluster_engine import LiquidityClusterEngine
from src.models.liquidity_point import LiquidityPoint, LiquidityType
from src.models.swing_point import SwingPoint, SwingPointType


def create_swing_point(index: int, price: float) -> SwingPoint:
    return SwingPoint(
        index=index,
        timestamp=datetime(2024, 1, 1) + timedelta(minutes=index),
        price=price,
        swing_type=SwingPointType.SWING_HIGH,
    )


def create_liquidity_point(index: int, price: float) -> LiquidityPoint:
    return LiquidityPoint(
        index=index,
        timestamp=datetime(2024, 1, 1) + timedelta(minutes=index),
        price=price,
        liquidity_type=LiquidityType.BUY_SIDE,
        source_swing=create_swing_point(index, price),
    )


def test_liquidity_cluster_engine_returns_empty_for_no_points():
    result = LiquidityClusterEngine().build_clusters([])

    assert result == []


def test_liquidity_cluster_engine_builds_cluster_from_nearby_points():
    points = [
        create_liquidity_point(1, 100.00),
        create_liquidity_point(2, 100.10),
    ]

    result = LiquidityClusterEngine().build_clusters(points)

    assert len(result) == 1
    assert result[0].start_index == 1
    assert result[0].end_index == 2
    assert result[0].average_price == 100.05
    assert result[0].point_count() == 2
    assert result[0].is_valid() is True


def test_liquidity_cluster_engine_ignores_points_outside_tolerance():
    points = [
        create_liquidity_point(1, 100.00),
        create_liquidity_point(2, 101.00),
    ]

    result = LiquidityClusterEngine().build_clusters(points)

    assert result == []


def test_liquidity_cluster_engine_builds_multiple_clusters():
    points = [
        create_liquidity_point(1, 100.00),
        create_liquidity_point(2, 100.10),
        create_liquidity_point(10, 110.00),
        create_liquidity_point(11, 110.10),
    ]

    result = LiquidityClusterEngine().build_clusters(points)

    assert len(result) == 2
    assert result[0].start_index == 1
    assert result[0].end_index == 2
    assert result[1].start_index == 10
    assert result[1].end_index == 11


def test_liquidity_cluster_engine_sorts_points_before_clustering():
    points = [
        create_liquidity_point(2, 100.10),
        create_liquidity_point(1, 100.00),
    ]

    result = LiquidityClusterEngine().build_clusters(points)

    assert len(result) == 1
    assert result[0].start_index == 1
    assert result[0].end_index == 2