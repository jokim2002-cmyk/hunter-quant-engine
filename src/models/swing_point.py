"""
Swing Point Model

This module defines the SwingPoint data model.

A SwingPoint represents an important market structure point:
- Swing High
- Swing Low

This model will be used by:
- Swing Detection Engine
- BOS Engine
- CHOCH Engine
- Liquidity Engine
- Strategy Engine
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SwingPointType(Enum):
    """
    Enum for swing point type.

    Using Enum avoids spelling mistakes like:
    - "swing_high"
    - "SwingHigh"
    - "high"

    Professional systems avoid raw strings for fixed categories.
    """

    SWING_HIGH = "swing_high"
    SWING_LOW = "swing_low"


@dataclass(frozen=True)
class SwingPoint:
    """
    Represents a single swing point in the market.

    frozen=True means once the object is created,
    it cannot be changed accidentally.

    This is important because market structure data
    should remain reliable after detection.
    """

    index: int
    timestamp: datetime
    price: float
    swing_type: SwingPointType

    def is_swing_high(self) -> bool:
        """
        Returns True if this point is a Swing High.
        """
        return self.swing_type == SwingPointType.SWING_HIGH

    def is_swing_low(self) -> bool:
        """
        Returns True if this point is a Swing Low.
        """
        return self.swing_type == SwingPointType.SWING_LOW