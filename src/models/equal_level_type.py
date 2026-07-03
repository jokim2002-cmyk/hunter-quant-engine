"""
Equal Level Type Model

This module defines equal level direction types.
"""

from enum import Enum


class EqualLevelType(Enum):
    """
    Defines which equal level direction should be detected.
    """

    HIGH = "high"
    LOW = "low"

    def is_high(self) -> bool:
        return self == EqualLevelType.HIGH

    def is_low(self) -> bool:
        return self == EqualLevelType.LOW