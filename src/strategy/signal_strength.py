"""
Signal Strength

Defines the confidence level of a strategy signal.
"""

from enum import Enum


class SignalStrength(Enum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
