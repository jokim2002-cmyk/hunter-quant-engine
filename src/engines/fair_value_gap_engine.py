"""
Fair Value Gap Engine

Detects Fair Value Gap market events from candles.
"""

from typing import List

from src.config.fair_value_gap_config import (
    DEFAULT_FAIR_VALUE_GAP_CONFIG,
    FairValueGapConfig,
)
from src.models.candle import Candle
from src.models.fair_value_gap import FairValueGap
from src.models.fair_value_gap_type import FairValueGapType


class FairValueGapEngine:
    """
    Detects Fair Value Gaps from candle data.
    """

    def __init__(
        self,
        config: FairValueGapConfig = DEFAULT_FAIR_VALUE_GAP_CONFIG,
    ):
        self.config = config

    def detect(self, candles: List[Candle]) -> List[FairValueGap]:
        """
        Detect Fair Value Gaps from a list of candles.
        """
        if not self.config.enabled:
            return []

        gaps: List[FairValueGap] = []

        for index in range(2, len(candles)):
            first_candle = candles[index - 2]
            third_candle = candles[index]

            bullish_gap_size = third_candle.low - first_candle.high
            bearish_gap_size = first_candle.low - third_candle.high

            if bullish_gap_size > self.config.minimum_gap_size:
                gaps.append(
                    FairValueGap(
                        start_index=index - 2,
                        end_index=index,
                        high=third_candle.low,
                        low=first_candle.high,
                        direction=FairValueGapType.BULLISH,
                        created_at=index,
                    )
                )

            if bearish_gap_size > self.config.minimum_gap_size:
                gaps.append(
                    FairValueGap(
                        start_index=index - 2,
                        end_index=index,
                        high=first_candle.low,
                        low=third_candle.high,
                        direction=FairValueGapType.BEARISH,
                        created_at=index,
                    )
                )

        return gaps