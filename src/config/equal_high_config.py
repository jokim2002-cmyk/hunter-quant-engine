"""
Equal High Configuration

This module contains configuration for equal high detection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EqualHighConfig:
    enabled: bool = True
    price_tolerance: float = 0.20


DEFAULT_EQUAL_HIGH_CONFIG = EqualHighConfig()
