"""
Fair Value Gap Type

Defines the direction of a Fair Value Gap.
"""

from enum import Enum


class FairValueGapType(Enum):
    """
    Represents the direction of a Fair Value Gap.
    """

    BULLISH = "bullish"
    BEARISH = "bearish"