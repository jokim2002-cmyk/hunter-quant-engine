"""
Institutional Setup Model

Represents an immutable institutional trading setup created from
Smart Money Concept confluence.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from src.models.bos_point import BOSPoint
from src.models.choch_point import CHOCHPoint
from src.models.fair_value_gap import FairValueGap
from src.models.liquidity_sweep import LiquiditySweep
from src.models.order_block import OrderBlock
from src.strategy.signal_type import SignalType


@dataclass(frozen=True)
class InstitutionalSetup:
    """
    Immutable institutional setup.

    This model represents higher-level SMC confluence before trade planning.
    """

    direction: SignalType
    confidence: float
    rationale: Tuple[str, ...]
    created_at: datetime

    bos_event: Optional[BOSPoint] = None
    choch_event: Optional[CHOCHPoint] = None
    liquidity_sweep: Optional[LiquiditySweep] = None
    fair_value_gap: Optional[FairValueGap] = None
    order_block: Optional[OrderBlock] = None

    def is_long(self) -> bool:
        """
        Return True when setup direction is long.
        """
        return self.direction == SignalType.LONG

    def is_short(self) -> bool:
        """
        Return True when setup direction is short.
        """
        return self.direction == SignalType.SHORT

    def has_market_structure(self) -> bool:
        """
        Return True when BOS or CHOCH evidence exists.
        """
        return self.bos_event is not None or self.choch_event is not None

    def has_liquidity_sweep(self) -> bool:
        """
        Return True when liquidity sweep evidence exists.
        """
        return self.liquidity_sweep is not None

    def has_entry_zone(self) -> bool:
        """
        Return True when FVG or order block entry zone evidence exists.
        """
        return self.fair_value_gap is not None or self.order_block is not None

    def is_actionable(self) -> bool:
        """
        Return True when setup contains core institutional confluence.
        """
        return (
            self.direction != SignalType.NEUTRAL
            and self.has_market_structure()
            and self.has_liquidity_sweep()
            and self.has_entry_zone()
        )
