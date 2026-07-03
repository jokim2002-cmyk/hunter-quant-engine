"""
Liquidity Cluster Configuration

This module defines configuration for liquidity cluster detection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LiquidityClusterConfig:
    """
    Configuration for LiquidityClusterEngine.
    """

    enabled: bool = True
    price_tolerance: float = 0.20
    minimum_points: int = 2


DEFAULT_LIQUIDITY_CLUSTER_CONFIG = LiquidityClusterConfig()