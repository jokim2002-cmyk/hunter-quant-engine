"""
Signal Type

Defines the direction of a strategy signal.
"""

from enum import Enum


class SignalType(Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"
