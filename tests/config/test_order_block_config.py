from src.config.order_block_config import (
    DEFAULT_ORDER_BLOCK_CONFIG,
    OrderBlockConfig,
)


def test_default_order_block_config_is_enabled():
    assert DEFAULT_ORDER_BLOCK_CONFIG.enabled is True


def test_default_order_block_config_minimum_displacement_size():
    assert DEFAULT_ORDER_BLOCK_CONFIG.minimum_displacement_size == 0.0


def test_default_order_block_config_require_opposite_candle():
    assert DEFAULT_ORDER_BLOCK_CONFIG.require_opposite_candle is True


def test_order_block_config_can_be_customized():
    config = OrderBlockConfig(
        enabled=False,
        minimum_displacement_size=5.0,
        require_opposite_candle=False,
    )

    assert config.enabled is False
    assert config.minimum_displacement_size == 5.0
    assert config.require_opposite_candle is False