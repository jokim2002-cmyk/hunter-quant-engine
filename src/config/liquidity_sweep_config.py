"""
Liquidity Sweep Config

Configuration for liquidity sweep detection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LiquiditySweepConfig:
    """
    Immutable configuration for liquidity sweep detection.
    """

    enabled: bool = True
    sweep_tolerance: float = 0.0
    require_close_back_inside: bool = True


DEFAULT_LIQUIDITY_SWEEP_CONFIG = LiquiditySweepConfig()