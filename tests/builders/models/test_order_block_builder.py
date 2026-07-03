"""
Tests for OrderBlockBuilder.
"""

from datetime import datetime

from src.models.order_block_type import OrderBlockType
from tests.builders.models.order_block_builder import OrderBlockBuilder


def test_builds_bullish_order_block_by_default():
    order_block = OrderBlockBuilder().build()

    assert order_block.is_bullish()
    assert order_block.order_block_type == OrderBlockType.BULLISH


def test_builds_bearish_order_block():
    order_block = OrderBlockBuilder().bearish().build()

    assert order_block.is_bearish()
    assert order_block.order_block_type == OrderBlockType.BEARISH


def test_builds_order_block_with_custom_index():
    order_block = OrderBlockBuilder().at_index(25).build()

    assert order_block.candle_index == 25


def test_builds_order_block_with_custom_prices():
    order_block = (
        OrderBlockBuilder()
        .with_high(120.0)
        .with_low(95.0)
        .with_open(118.0)
        .with_close(98.0)
        .build()
    )

    assert order_block.high == 120.0
    assert order_block.low == 95.0
    assert order_block.open == 118.0
    assert order_block.close == 98.0


def test_builds_order_block_with_custom_created_at():
    created_at = datetime(2026, 2, 1)

    order_block = OrderBlockBuilder().created_at(created_at).build()

    assert order_block.created_at == created_at


def test_builds_mitigated_order_block():
    mitigated_at = datetime(2026, 2, 2)

    order_block = OrderBlockBuilder().mitigated_at(mitigated_at).build()

    assert order_block.mitigated is True
    assert order_block.mitigated_at == mitigated_at


def test_builds_unmitigated_order_block():
    mitigated_at = datetime(2026, 2, 2)

    order_block = (
        OrderBlockBuilder()
        .mitigated_at(mitigated_at)
        .unmitigated()
        .build()
    )

    assert order_block.mitigated is False
    assert order_block.mitigated_at is None
