"""
Break Detector Helper

Shared helper for detecting when candles break swing points.
"""

from typing import List, Optional, Tuple

from src.models.candle import Candle
from src.models.swing_point import SwingPoint


class BreakDetector:
    """
    Detects candle breaks of swing points.
    """

    def find_close_break(
        self,
        candles: List[Candle],
        swing_point: SwingPoint,
    ) -> Optional[Tuple[int, Candle]]:
        for candle_index in range(swing_point.index + 1, len(candles)):
            candle = candles[candle_index]

            if swing_point.is_swing_high() and candle.close > swing_point.price:
                return candle_index, candle

            if swing_point.is_swing_low() and candle.close < swing_point.price:
                return candle_index, candle

        return None
