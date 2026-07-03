"""
SMC Rule Set Result

Immutable result object returned by SMC rule sets.
"""

from dataclasses import dataclass

from src.models.bos_point import BOSPoint
from src.models.choch_point import CHOCHPoint
from src.models.fair_value_gap import FairValueGap
from src.models.liquidity_sweep import LiquiditySweep
from src.models.order_block import OrderBlock


@dataclass(frozen=True)
class SMCRuleSetResult:
    bos_events: tuple[BOSPoint, ...]
    choch_events: tuple[CHOCHPoint, ...]
    liquidity_sweeps: tuple[LiquiditySweep, ...]
    fair_value_gaps: tuple[FairValueGap, ...]
    order_blocks: tuple[OrderBlock, ...]
