"""
Market Structure Model

This module defines classified market structure points.
"""

from dataclasses import dataclass
from enum import Enum

from src.models.swing_point import SwingPoint


class MarketStructureType(Enum):
    HIGHER_HIGH = "higher_high"
    LOWER_HIGH = "lower_high"
    HIGHER_LOW = "higher_low"
    LOWER_LOW = "lower_low"


@dataclass(frozen=True)
class MarketStructurePoint:
    swing_point: SwingPoint
    structure_type: MarketStructureType

    def is_higher_high(self) -> bool:
        return self.structure_type == MarketStructureType.HIGHER_HIGH

    def is_lower_high(self) -> bool:
        return self.structure_type == MarketStructureType.LOWER_HIGH

    def is_higher_low(self) -> bool:
        return self.structure_type == MarketStructureType.HIGHER_LOW

    def is_lower_low(self) -> bool:
        return self.structure_type == MarketStructureType.LOWER_LOW
