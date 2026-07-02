"""
Swing Detection Engine

This module detects Swing Highs and Swing Lows from candle data.

A Swing High is a candle whose high is greater than highs on both left and right side.
A Swing Low is a candle whose low is lower than lows on both left and right side.
"""

from typing import List

from src.models.candle import Candle
from src.models.swing_point import SwingPoint, SwingPointType


class SwingDetectionEngine:
    """
    Detects swing points from a list of candles.

    This engine is part of the Market Structure Foundation.
    """

    def __init__(self, lookback: int = 2) -> None:
        """
        Initialize Swing Detection Engine.

        Args:
            lookback: Number of candles to check on left and right side.
        """
        if lookback < 1:
            raise ValueError("lookback must be greater than or equal to 1")

        self.lookback = lookback

    def detect_swings(self, candles: List[Candle]) -> List[SwingPoint]:
        """
        Detect swing highs and swing lows from candles.

        Args:
            candles: List of Candle objects.

        Returns:
            List of SwingPoint objects.
        """
        if not candles:
            return []

        minimum_required_candles = (self.lookback * 2) + 1

        if len(candles) < minimum_required_candles:
            return []

        swing_points: List[SwingPoint] = []

        for current_index in range(self.lookback, len(candles) - self.lookback):
            current_candle = candles[current_index]

            if self._is_swing_high(candles, current_index):
                swing_points.append(
                    SwingPoint(
                        index=current_index,
                        timestamp=current_candle.datetime,
                        price=current_candle.high,
                        swing_type=SwingPointType.SWING_HIGH,
                    )
                )

            if self._is_swing_low(candles, current_index):
                swing_points.append(
                    SwingPoint(
                        index=current_index,
                        timestamp=current_candle.datetime,
                        price=current_candle.low,
                        swing_type=SwingPointType.SWING_LOW,
                    )
                )

        return swing_points

    def _is_swing_high(self, candles: List[Candle], current_index: int) -> bool:
        """
        Check whether current candle is a swing high.
        """
        current_high = candles[current_index].high

        start_index = current_index - self.lookback
        end_index = current_index + self.lookback

        for index in range(start_index, end_index + 1):
            if index == current_index:
                continue

            if candles[index].high >= current_high:
                return False

        return True

    def _is_swing_low(self, candles: List[Candle], current_index: int) -> bool:
        """
        Check whether current candle is a swing low.
        """
        current_low = candles[current_index].low

        start_index = current_index - self.lookback
        end_index = current_index + self.lookback

        for index in range(start_index, end_index + 1):
            if index == current_index:
                continue

            if candles[index].low <= current_low:
                return False

        return True