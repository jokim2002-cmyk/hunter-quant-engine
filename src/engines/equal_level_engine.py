"""
Equal Level Engine

Detects Equal High and Equal Low liquidity areas.
"""

from typing import List, Union

from src.config.equal_level_config import EqualLevelConfig, DEFAULT_EQUAL_LEVEL_CONFIG
from src.models.equal_high_point import EqualHighPoint
from src.models.equal_level_type import EqualLevelType
from src.models.equal_low_point import EqualLowPoint
from src.models.market_structure import MarketStructurePoint, MarketStructureType
from src.models.swing_point import SwingPoint


EqualLevelPoint = Union[EqualHighPoint, EqualLowPoint]


class EqualLevelEngine:
    """
    Detects equal highs and equal lows using one shared algorithm.
    """

    def __init__(
        self,
        config: EqualLevelConfig = DEFAULT_EQUAL_LEVEL_CONFIG,
    ) -> None:
        self.config = config

    def detect_equal_levels(
        self,
        market_structure_points: List[MarketStructurePoint],
        level_type: EqualLevelType,
    ) -> List[EqualLevelPoint]:

        if not self.config.enabled:
            return []

        swings = self._get_matching_swings(
            market_structure_points=market_structure_points,
            level_type=level_type,
        )

        clusters = self._build_clusters(swings)

        return [
            self._create_equal_level_point(
                cluster=cluster,
                level_type=level_type,
            )
            for cluster in clusters
        ]

    def _get_matching_swings(
        self,
        market_structure_points: List[MarketStructurePoint],
        level_type: EqualLevelType,
    ) -> List[SwingPoint]:

        matching_swings: List[SwingPoint] = []

        for structure_point in market_structure_points:
            if self._matches_level_type(structure_point, level_type):
                matching_swings.append(structure_point.swing_point)

        return matching_swings

    def _matches_level_type(
        self,
        structure_point: MarketStructurePoint,
        level_type: EqualLevelType,
    ) -> bool:

        if level_type.is_high():
            return structure_point.structure_type in (
                MarketStructureType.HIGHER_HIGH,
                MarketStructureType.LOWER_HIGH,
            )

        if level_type.is_low():
            return structure_point.structure_type in (
                MarketStructureType.HIGHER_LOW,
                MarketStructureType.LOWER_LOW,
            )

        raise ValueError(f"Invalid equal level type: {level_type}")

    def _build_clusters(self, swings: List[SwingPoint]) -> List[List[SwingPoint]]:
        clusters: List[List[SwingPoint]] = []
        processed_indexes = set()

        for current_swing in swings:
            if current_swing.index in processed_indexes:
                continue

            cluster = [current_swing]

            for candidate_swing in swings:
                if candidate_swing.index == current_swing.index:
                    continue

                if candidate_swing.index in processed_indexes:
                    continue

                if self._is_equal_level(current_swing, candidate_swing):
                    cluster.append(candidate_swing)

            if len(cluster) < 2:
                continue

            cluster = sorted(cluster, key=lambda swing: swing.index)

            for swing in cluster:
                processed_indexes.add(swing.index)

            clusters.append(cluster)

        return clusters

    def _is_equal_level(
        self,
        first_swing: SwingPoint,
        second_swing: SwingPoint,
    ) -> bool:
        return abs(first_swing.price - second_swing.price) <= self.config.price_tolerance

    def _create_equal_level_point(
        self,
        cluster: List[SwingPoint],
        level_type: EqualLevelType,
    ) -> EqualLevelPoint:

        if level_type.is_high():
            return EqualHighPoint(
                index=cluster[-1].index,
                timestamp=cluster[-1].timestamp,
                price=self._average_price(cluster),
                source_swings=cluster,
            )

        if level_type.is_low():
            return EqualLowPoint(
                index=cluster[-1].index,
                timestamp=cluster[-1].timestamp,
                price=self._average_price(cluster),
                source_swings=cluster,
            )

        raise ValueError(f"Invalid equal level type: {level_type}")

    def _average_price(self, swings: List[SwingPoint]) -> float:
        total_price = sum(swing.price for swing in swings)
        return total_price / len(swings)