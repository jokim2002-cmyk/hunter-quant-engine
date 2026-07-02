"""
CHOCH Engine

Detects Change of Character (CHOCH) events.
"""

from typing import List

from src.config.choch_config import CHOCHConfig, DEFAULT_CHOCH_CONFIG
from src.engines.helpers.break_detector import BreakDetector
from src.models.candle import Candle
from src.models.choch_point import CHOCHPoint
from src.models.swing_point import SwingPoint


class CHOCHEngine:
    """
    Detects Change of Character events.
    """

    def __init__(self, config: CHOCHConfig = DEFAULT_CHOCH_CONFIG) -> None:
        self.config = config
        self.break_detector = BreakDetector()

    def detect_choch(
        self,
        candles: List[Candle],
        swing_points: List[SwingPoint],
    ) -> List[CHOCHPoint]:
        """
        Detect CHOCH events.

        TODO:
        Implement detection logic.
        """
        return []
