"""
Equal High Engine

Detects equal high liquidity areas from market structure points.
"""

from typing import List

from src.config.equal_high_config import EqualHighConfig, DEFAULT_EQUAL_HIGH_CONFIG
from src.models.equal_high_point import EqualHighPoint
from src.models.market_structure import MarketStructurePoint, MarketStructureType
from src.models.swing_point import SwingPoint


class EqualHighEngine:
    """
    Detects equal highs using swing highs from market structure points.
    """

    def __init__(
        self,
        config: EqualHighConfig = DEFAULT_EQUAL_HIGH_CONFIG,
    ) -> None:
        self.config = config

    def detect_equal_highs(
        self,
        market_structure_points: List[MarketStructurePoint],
    ) -> List[EqualHighPoint]:

        if not self.config.enabled:
            return []

        swing_highs = self._get_swing_highs(market_structure_points)
        clusters = self._build_clusters(swing_highs)

        return [
            EqualHighPoint(
                index=cluster[-1].index,
                timestamp=cluster[-1].timestamp,
                price=self._average_price(cluster),
                source_swings=cluster,
            )
            for cluster in clusters
        ]

    def _get_swing_highs(
        self,
        market_structure_points: List[MarketStructurePoint],
    ) -> List[SwingPoint]:

        swing_highs: List[SwingPoint] = []

        for structure_point in market_structure_points:
            if structure_point.structure_type in (
                MarketStructureType.HIGHER_HIGH,
                MarketStructureType.LOWER_HIGH,
            ):
                swing_highs.append(structure_point.swing_point)

        return swing_highs

    def _build_clusters(self, swing_highs: List[SwingPoint]) -> List[List[SwingPoint]]:
        clusters: List[List[SwingPoint]] = []
        processed_indexes = set()

        for current_swing in swing_highs:
            if current_swing.index in processed_indexes:
                continue

            cluster = [current_swing]

            for candidate_swing in swing_highs:
                if candidate_swing.index == current_swing.index:
                    continue

                if candidate_swing.index in processed_indexes:
                    continue

                if self._is_equal_high(current_swing, candidate_swing):
                    cluster.append(candidate_swing)

            if len(cluster) < 2:
                continue

            cluster = sorted(cluster, key=lambda swing: swing.index)

            for swing in cluster:
                processed_indexes.add(swing.index)

            clusters.append(cluster)

        return clusters

    def _is_equal_high(
        self,
        first_swing: SwingPoint,
        second_swing: SwingPoint,
    ) -> bool:
        return abs(first_swing.price - second_swing.price) <= self.config.price_tolerance

    def _average_price(self, swings: List[SwingPoint]) -> float:
        total_price = sum(swing.price for swing in swings)
        return total_price / len(swings)
