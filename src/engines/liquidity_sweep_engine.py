"""
Liquidity Sweep Engine

Detects liquidity sweep market events from candles and liquidity points.
"""

from typing import List

from src.config.liquidity_sweep_config import (
    DEFAULT_LIQUIDITY_SWEEP_CONFIG,
    LiquiditySweepConfig,
)
from src.models.candle import Candle
from src.models.liquidity_point import LiquidityPoint
from src.models.liquidity_sweep import LiquiditySweep
from src.models.liquidity_sweep_type import LiquiditySweepType


class LiquiditySweepEngine:
    """
    Detects liquidity sweeps from candle data and liquidity points.
    """

    def __init__(
        self,
        config: LiquiditySweepConfig = DEFAULT_LIQUIDITY_SWEEP_CONFIG,
    ):
        self.config = config

    def detect(
        self,
        candles: List[Candle],
        liquidity_points: List[LiquidityPoint],
    ) -> List[LiquiditySweep]:
        """
        Detect liquidity sweeps.
        """
        if not self.config.enabled:
            return []

        sweeps: List[LiquiditySweep] = []

        for liquidity_point in liquidity_points:
            for candle_index in range(liquidity_point.index + 1, len(candles)):
                candle = candles[candle_index]

                if liquidity_point.is_buy_side():
                    sweep = self._detect_buy_side_sweep(
                        candle_index=candle_index,
                        candle=candle,
                        liquidity_point=liquidity_point,
                    )
                    if sweep is not None:
                        sweeps.append(sweep)

                if liquidity_point.is_sell_side():
                    sweep = self._detect_sell_side_sweep(
                        candle_index=candle_index,
                        candle=candle,
                        liquidity_point=liquidity_point,
                    )
                    if sweep is not None:
                        sweeps.append(sweep)

        return sweeps

    def _detect_buy_side_sweep(
        self,
        candle_index: int,
        candle: Candle,
        liquidity_point: LiquidityPoint,
    ) -> LiquiditySweep | None:
        break_distance = candle.high - liquidity_point.price
        reclaimed = candle.close < liquidity_point.price

        if break_distance < self.config.sweep_tolerance:
            return None

        if self.config.require_close_back_inside and not reclaimed:
            return None

        if candle.high <= liquidity_point.price:
            return None

        return LiquiditySweep(
            candle_index=candle_index,
            liquidity_index=liquidity_point.index,
            sweep_price=candle.high,
            liquidity_price=liquidity_point.price,
            break_distance=break_distance,
            reclaimed=reclaimed,
            sweep_type=LiquiditySweepType.HIGH,
            created_at=candle_index,
        )

    def _detect_sell_side_sweep(
        self,
        candle_index: int,
        candle: Candle,
        liquidity_point: LiquidityPoint,
    ) -> LiquiditySweep | None:
        break_distance = liquidity_point.price - candle.low
        reclaimed = candle.close > liquidity_point.price

        if break_distance < self.config.sweep_tolerance:
            return None

        if self.config.require_close_back_inside and not reclaimed:
            return None

        if candle.low >= liquidity_point.price:
            return None

        return LiquiditySweep(
            candle_index=candle_index,
            liquidity_index=liquidity_point.index,
            sweep_price=candle.low,
            liquidity_price=liquidity_point.price,
            break_distance=break_distance,
            reclaimed=reclaimed,
            sweep_type=LiquiditySweepType.LOW,
            created_at=candle_index,
        )