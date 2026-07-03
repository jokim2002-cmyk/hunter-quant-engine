"""
Liquidity Cluster Model

This module defines liquidity clusters.

A LiquidityCluster groups multiple nearby liquidity points
into one liquidity area.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from src.models.liquidity_point import LiquidityPoint


@dataclass(frozen=True)
class LiquidityCluster:
    """
    Represents a grouped liquidity area.
    """

    start_index: int
    end_index: int
    start_time: datetime
    end_time: datetime
    average_price: float
    liquidity_points: List[LiquidityPoint]

    def point_count(self) -> int:
        """
        Returns number of liquidity points inside this cluster.
        """
        return len(self.liquidity_points)

    def is_valid(self) -> bool:
        """
        A liquidity cluster is valid if it has at least two points.
        """
        return self.point_count() >= 2