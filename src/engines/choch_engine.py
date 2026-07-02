"""
CHOCH Engine

Detects Change of Character (CHOCH) events.
"""

from typing import List

from src.config.choch_config import CHOCHConfig, DEFAULT_CHOCH_CONFIG
from src.engines.helpers.break_detector import BreakDetector
from src.models.candle import Candle
from src.models.choch_point import CHOCHPoint, CHOCHType
from src.models.market_structure import MarketStructurePoint, MarketStructureType


class CHOCHEngine:
    """
    Detects Change of Character events using MarketStructurePoint.
    """

    def __init__(self, config: CHOCHConfig = DEFAULT_CHOCH_CONFIG) -> None:
        self.config = config
        self.break_detector = BreakDetector()

    def detect_choch(
        self,
        candles: List[Candle],
        market_structure_points: List[MarketStructurePoint],
    ) -> List[CHOCHPoint]:
        choch_points: List[CHOCHPoint] = []

        if not candles or not market_structure_points:
            return choch_points

        for structure_point in market_structure_points:
            if not self._can_create_choch(structure_point):
                continue

            swing_point = structure_point.swing_point

            break_result = self.break_detector.find_close_break(
                candles=candles,
                swing_point=swing_point,
            )

            if break_result is None:
                continue

            break_index, break_candle = break_result

            choch_points.append(
                CHOCHPoint(
                    index=break_index,
                    timestamp=break_candle.datetime,
                    break_price=break_candle.close,
                    choch_type=self._get_choch_type(structure_point),
                    broken_swing=swing_point,
                )
            )

        return choch_points

    def _can_create_choch(self, structure_point: MarketStructurePoint) -> bool:
        return structure_point.structure_type in (
            MarketStructureType.HIGHER_LOW,
            MarketStructureType.LOWER_HIGH,
        )

    def _get_choch_type(self, structure_point: MarketStructurePoint) -> CHOCHType:
        if structure_point.structure_type == MarketStructureType.HIGHER_LOW:
            return CHOCHType.BEARISH

        if structure_point.structure_type == MarketStructureType.LOWER_HIGH:
            return CHOCHType.BULLISH

        raise ValueError(
            f"Invalid CHOCH market structure type: {structure_point.structure_type}"
        )
