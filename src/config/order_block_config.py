"""
Order Block Configuration

Stores configurable parameters for order block detection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderBlockConfig:
    enabled: bool = True
    minimum_displacement_size: float = 0.0
    require_opposite_candle: bool = True


DEFAULT_ORDER_BLOCK_CONFIG = OrderBlockConfig()