"""
Order Block Type Model

Defines bullish and bearish order block types.
"""

from enum import Enum


class OrderBlockType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"