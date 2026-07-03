from src.config.liquidity_cluster_config import (
    DEFAULT_LIQUIDITY_CLUSTER_CONFIG,
    LiquidityClusterConfig,
)


def test_default_liquidity_cluster_config_is_enabled():
    assert DEFAULT_LIQUIDITY_CLUSTER_CONFIG.enabled is True


def test_default_liquidity_cluster_config_has_price_tolerance():
    assert DEFAULT_LIQUIDITY_CLUSTER_CONFIG.price_tolerance == 0.20


def test_default_liquidity_cluster_config_has_minimum_points():
    assert DEFAULT_LIQUIDITY_CLUSTER_CONFIG.minimum_points == 2


def test_liquidity_cluster_config_can_be_disabled():
    config = LiquidityClusterConfig(enabled=False)

    assert config.enabled is False


def test_liquidity_cluster_config_accepts_custom_values():
    config = LiquidityClusterConfig(
        price_tolerance=0.50,
        minimum_points=3,
    )

    assert config.price_tolerance == 0.50
    assert config.minimum_points == 3