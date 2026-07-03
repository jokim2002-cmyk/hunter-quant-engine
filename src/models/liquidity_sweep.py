"""
Liquidity Sweep Model

Represents a detected liquidity sweep market event.
"""

from dataclasses import dataclass

from src.models.liquidity_sweep_type import LiquiditySweepType


@dataclass(frozen=True)
class LiquiditySweep:
    """
    Immutable model for a liquidity sweep event.
    """

    candle_index: int
    liquidity_index: int
    sweep_price: float
    liquidity_price: float
    break_distance: float
    reclaimed: bool
    sweep_type: LiquiditySweepType
    created_at: int

    def is_buy_side(self) -> bool:
        """
        Return True when high liquidity was swept.
        """
        return self.sweep_type == LiquiditySweepType.HIGH

    def is_sell_side(self) -> bool:
        """
        Return True when low liquidity was swept.
        """
        return self.sweep_type == LiquiditySweepType.LOW
