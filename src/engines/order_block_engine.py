"""
Order Block Engine

Detects bullish and bearish order blocks from candle data.
"""

from typing import List

from src.config.order_block_config import (
    DEFAULT_ORDER_BLOCK_CONFIG,
    OrderBlockConfig,
)
from src.models.candle import Candle
from src.models.order_block import OrderBlock
from src.models.order_block_type import OrderBlockType


class OrderBlockEngine:
    """
    Detects order blocks.

    Engine is stateless.
    It only detects market events.
    It does not make trading decisions.
    """

    def __init__(
        self,
        config: OrderBlockConfig = DEFAULT_ORDER_BLOCK_CONFIG,
    ) -> None:
        self.config = config

    def detect(self, candles: List[Candle]) -> List[OrderBlock]:
        if not self.config.enabled:
            return []

        if len(candles) < 2:
            return []

        order_blocks: List[OrderBlock] = []

        for index in range(1, len(candles)):
            previous_candle = candles[index - 1]
            current_candle = candles[index]

            displacement_size = abs(current_candle.close - current_candle.open)

            if displacement_size < self.config.minimum_displacement_size:
                continue

            if self._is_bullish_displacement(current_candle):
                if self._can_create_bullish_order_block(previous_candle):
                    order_blocks.append(
                        self._create_order_block(
                            candle=previous_candle,
                            candle_index=index - 1,
                            order_block_type=OrderBlockType.BULLISH,
                        )
                    )

            if self._is_bearish_displacement(current_candle):
                if self._can_create_bearish_order_block(previous_candle):
                    order_blocks.append(
                        self._create_order_block(
                            candle=previous_candle,
                            candle_index=index - 1,
                            order_block_type=OrderBlockType.BEARISH,
                        )
                    )

        return order_blocks

    def _is_bullish_displacement(self, candle: Candle) -> bool:
        return candle.is_bullish

    def _is_bearish_displacement(self, candle: Candle) -> bool:
        return candle.is_bearish

    def _can_create_bullish_order_block(self, candle: Candle) -> bool:
        if not self.config.require_opposite_candle:
            return True

        return candle.is_bearish

    def _can_create_bearish_order_block(self, candle: Candle) -> bool:
        if not self.config.require_opposite_candle:
            return True

        return candle.is_bullish

    def _create_order_block(
        self,
        candle: Candle,
        candle_index: int,
        order_block_type: OrderBlockType,
    ) -> OrderBlock:
        return OrderBlock(
            candle_index=candle_index,
            high=candle.high,
            low=candle.low,
            open=candle.open,
            close=candle.close,
            order_block_type=order_block_type,
            created_at=candle.datetime,
        )