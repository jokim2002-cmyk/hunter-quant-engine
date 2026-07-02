"""
BOS Engine

This module detects Break of Structure events.
"""

from typing import List

from src.config.bos_config import BOSConfig, DEFAULT_BOS_CONFIG
from src.engines.helpers.break_detector import BreakDetector
from src.models.bos_point import BOSPoint, BOSType
from src.models.candle import Candle
from src.models.market_structure import MarketStructurePoint


class BOSEngine:
    """
    Detects bullish and bearish Break of Structure events
    using MarketStructurePoint.
    """

    def __init__(self, config: BOSConfig = DEFAULT_BOS_CONFIG) -> None:
        self.config = config
        self.break_detector = BreakDetector()

    def detect_bos(
        self,
        candles: List[Candle],
        market_structure_points: List[MarketStructurePoint],
    ) -> List[BOSPoint]:
        bos_points: List[BOSPoint] = []

        if not candles or not market_structure_points:
            return bos_points

        for structure_point in market_structure_points:
            swing_point = structure_point.swing_point

            break_result = self.break_detector.find_close_break(
                candles=candles,
                swing_point=swing_point,
            )

            if break_result is None:
                continue

            break_index, break_candle = break_result

            bos_type = (
                BOSType.BULLISH
                if swing_point.is_swing_high()
                else BOSType.BEARISH
            )

            bos_points.append(
                BOSPoint(
                    index=break_index,
                    timestamp=break_candle.datetime,
                    break_price=break_candle.close,
                    bos_type=bos_type,
                    broken_swing=structure_point,
                )
            )

        return bos_points
