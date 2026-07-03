"""
Liquidity Sweep Type

Defines the side of liquidity that was swept.
"""

from enum import Enum


class LiquiditySweepType(Enum):
    """
    Represents the side of liquidity that was swept.
    """

    HIGH = "high"
    LOW = "low"