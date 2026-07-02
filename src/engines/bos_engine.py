"""
BOS Engine

This module detects Break of Structure events.
"""

from typing import List

from src.config.bos_config import BOSConfig, DEFAULT_BOS_CONFIG
from src.models.bos_point import BOSPoint, BOSType
from src.models.candle import Candle
from src.models.swing_point import SwingPoint


class BOSEngine:
    """
    Detects bullish and bearish Break of Structure events.
    """

    def __init__(self, config: BOSConfig = DEFAULT_BOS_CONFIG) -> None:
        self.config = config

    def detect_bos(
        self,
        candles: List[Candle],
        swing_points: List[SwingPoint],
    ) -> List[BOSPoint]:
        bos_points: List[BOSPoint] = []

        if not candles or not swing_points:
            return bos_points

        for swing_point in swing_points:
            for candle_index in range(swing_point.index + 1, len(candles)):
                candle = candles[candle_index]

                if swing_point.is_swing_high() and candle.close > swing_point.price:
                    bos_points.append(
                        BOSPoint(
                            index=candle_index,
                            timestamp=candle.datetime,
                            break_price=candle.close,
                            bos_type=BOSType.BULLISH,
                            broken_swing=swing_point,
                        )
                    )
                    break

                if swing_point.is_swing_low() and candle.close < swing_point.price:
                    bos_points.append(
                        BOSPoint(
                            index=candle_index,
                            timestamp=candle.datetime,
                            break_price=candle.close,
                            bos_type=BOSType.BEARISH,
                            broken_swing=swing_point,
                        )
                    )
                    break

        return bos_points
