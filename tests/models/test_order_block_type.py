from src.models.order_block_type import OrderBlockType


def test_order_block_type_values():
    assert OrderBlockType.BULLISH.value == "bullish"
    assert OrderBlockType.BEARISH.value == "bearish"