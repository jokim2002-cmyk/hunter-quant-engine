"""
Liquidity Configuration

This module contains configuration for liquidity detection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LiquidityConfig:
    enabled: bool = True


DEFAULT_LIQUIDITY_CONFIG = LiquidityConfig()
