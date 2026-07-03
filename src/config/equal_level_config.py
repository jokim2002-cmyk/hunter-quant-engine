"""
Equal Level Configuration

Shared configuration for Equal High and Equal Low detection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EqualLevelConfig:
    """
    Configuration for Equal High and Equal Low detection.
    """

    enabled: bool = True
    price_tolerance: float = 0.20


DEFAULT_EQUAL_LEVEL_CONFIG = EqualLevelConfig()