from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from src.models.order_block import OrderBlock
from src.models.order_block_type import OrderBlockType


def test_order_block_can_be_created():
    created_at = datetime(2026, 1, 1)

    order_block = OrderBlock(
        candle_index=5,
        high=110.0,
        low=100.0,
        open=108.0,
        close=102.0,
        order_block_type=OrderBlockType.BULLISH,
        created_at=created_at,
    )

    assert order_block.candle_index == 5
    assert order_block.high == 110.0
    assert order_block.low == 100.0
    assert order_block.open == 108.0
    assert order_block.close == 102.0
    assert order_block.order_block_type == OrderBlockType.BULLISH
    assert order_block.created_at == created_at
    assert order_block.mitigated is False
    assert order_block.mitigated_at is None


def test_order_block_is_immutable():
    order_block = OrderBlock(
        candle_index=1,
        high=110.0,
        low=100.0,
        open=108.0,
        close=102.0,
        order_block_type=OrderBlockType.BULLISH,
        created_at=datetime(2026, 1, 1),
    )

    with pytest.raises(FrozenInstanceError):
        order_block.high = 120.0