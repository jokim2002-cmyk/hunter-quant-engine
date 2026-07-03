"""
Liquidity Cluster Engine

Groups nearby liquidity points into liquidity clusters.
"""

from typing import List

from src.config.liquidity_cluster_config import (
    DEFAULT_LIQUIDITY_CLUSTER_CONFIG,
    LiquidityClusterConfig,
)
from src.models.liquidity_cluster import LiquidityCluster
from src.models.liquidity_point import LiquidityPoint


class LiquidityClusterEngine:
    """
    Builds liquidity clusters from individual liquidity points.
    """

    def __init__(
        self,
        config: LiquidityClusterConfig = DEFAULT_LIQUIDITY_CLUSTER_CONFIG,
    ) -> None:
        self.config = config

    def build_clusters(
        self,
        liquidity_points: List[LiquidityPoint],
    ) -> List[LiquidityCluster]:

        if not self.config.enabled:
            return []

        clusters: List[LiquidityCluster] = []
        processed_indexes = set()

        sorted_points = sorted(
            liquidity_points,
            key=lambda point: point.index,
        )

        for current_point in sorted_points:
            if current_point.index in processed_indexes:
                continue

            cluster_points = [current_point]

            for candidate_point in sorted_points:
                if candidate_point.index == current_point.index:
                    continue

                if candidate_point.index in processed_indexes:
                    continue

                if self._is_nearby(current_point, candidate_point):
                    cluster_points.append(candidate_point)

            if len(cluster_points) < self.config.minimum_points:
                continue

            cluster_points = sorted(
                cluster_points,
                key=lambda point: point.index,
            )

            for point in cluster_points:
                processed_indexes.add(point.index)

            clusters.append(
                self._create_cluster(cluster_points)
            )

        return clusters

    def _is_nearby(
        self,
        first_point: LiquidityPoint,
        second_point: LiquidityPoint,
    ) -> bool:
        return (
            abs(first_point.price - second_point.price)
            <= self.config.price_tolerance
        )

    def _create_cluster(
        self,
        liquidity_points: List[LiquidityPoint],
    ) -> LiquidityCluster:
        return LiquidityCluster(
            start_index=liquidity_points[0].index,
            end_index=liquidity_points[-1].index,
            start_time=liquidity_points[0].timestamp,
            end_time=liquidity_points[-1].timestamp,
            average_price=self._average_price(liquidity_points),
            liquidity_points=liquidity_points,
        )

    def _average_price(
        self,
        liquidity_points: List[LiquidityPoint],
    ) -> float:
        total_price = sum(point.price for point in liquidity_points)
        return total_price / len(liquidity_points)