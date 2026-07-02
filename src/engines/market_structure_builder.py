"""
Market Structure Builder

This module converts swing points into classified market structure points.
"""

from typing import List

from src.models.market_structure import MarketStructurePoint, MarketStructureType
from src.models.swing_point import SwingPoint


class MarketStructureBuilder:
    """
    Converts swing points into market structure points.

    Swing highs become:
    - Higher High
    - Lower High

    Swing lows become:
    - Higher Low
    - Lower Low
    """

    def build(self, swing_points: List[SwingPoint]) -> List[MarketStructurePoint]:
        market_structure_points: List[MarketStructurePoint] = []

        if not swing_points:
            return market_structure_points

        last_high_price = None
        last_low_price = None

        for swing_point in swing_points:
            if swing_point.is_swing_high():
                if last_high_price is None or swing_point.price > last_high_price:
                    structure_type = MarketStructureType.HIGHER_HIGH
                else:
                    structure_type = MarketStructureType.LOWER_HIGH

                last_high_price = swing_point.price

            elif swing_point.is_swing_low():
                if last_low_price is None or swing_point.price > last_low_price:
                    structure_type = MarketStructureType.HIGHER_LOW
                else:
                    structure_type = MarketStructureType.LOWER_LOW

                last_low_price = swing_point.price

            else:
                raise ValueError("Invalid swing point type")

            market_structure_points.append(
                MarketStructurePoint(
                    swing_point=swing_point,
                    structure_type=structure_type,
                )
            )

        return market_structure_points
