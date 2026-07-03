from datetime import datetime, timedelta

from src.models.liquidity_cluster import LiquidityCluster
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


def test_liquidity_cluster_stores_values():
    points = [
        create_liquidity_point(1, 100.00),
        create_liquidity_point(2, 100.10),
    ]

    cluster = LiquidityCluster(
        start_index=1,
        end_index=2,
        start_time=points[0].timestamp,
        end_time=points[1].timestamp,
        average_price=100.05,
        liquidity_points=points,
    )

    assert cluster.start_index == 1
    assert cluster.end_index == 2
    assert cluster.average_price == 100.05
    assert cluster.liquidity_points == points


def test_liquidity_cluster_point_count():
    points = [
        create_liquidity_point(1, 100.00),
        create_liquidity_point(2, 100.10),
    ]

    cluster = LiquidityCluster(
        start_index=1,
        end_index=2,
        start_time=points[0].timestamp,
        end_time=points[1].timestamp,
        average_price=100.05,
        liquidity_points=points,
    )

    assert cluster.point_count() == 2


def test_liquidity_cluster_is_valid_with_two_or_more_points():
    points = [
        create_liquidity_point(1, 100.00),
        create_liquidity_point(2, 100.10),
    ]

    cluster = LiquidityCluster(
        start_index=1,
        end_index=2,
        start_time=points[0].timestamp,
        end_time=points[1].timestamp,
        average_price=100.05,
        liquidity_points=points,
    )

    assert cluster.is_valid() is True


def test_liquidity_cluster_is_invalid_with_less_than_two_points():
    points = [
        create_liquidity_point(1, 100.00),
    ]

    cluster = LiquidityCluster(
        start_index=1,
        end_index=1,
        start_time=points[0].timestamp,
        end_time=points[0].timestamp,
        average_price=100.00,
        liquidity_points=points,
    )

    assert cluster.is_valid() is False