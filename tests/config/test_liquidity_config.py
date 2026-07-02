from src.config.liquidity_config import LiquidityConfig, DEFAULT_LIQUIDITY_CONFIG


def test_default_liquidity_config_is_enabled():
    assert DEFAULT_LIQUIDITY_CONFIG.enabled is True


def test_liquidity_config_can_be_disabled():
    config = LiquidityConfig(enabled=False)

    assert config.enabled is False
