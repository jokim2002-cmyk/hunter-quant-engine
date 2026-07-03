from src.config.equal_level_config import (
    EqualLevelConfig,
    DEFAULT_EQUAL_LEVEL_CONFIG,
)


def test_default_equal_level_config_is_enabled():
    assert DEFAULT_EQUAL_LEVEL_CONFIG.enabled is True


def test_default_equal_level_config_has_price_tolerance():
    assert DEFAULT_EQUAL_LEVEL_CONFIG.price_tolerance == 0.20


def test_equal_level_config_can_be_disabled():
    config = EqualLevelConfig(enabled=False)

    assert config.enabled is False


def test_equal_level_config_accepts_custom_price_tolerance():
    config = EqualLevelConfig(price_tolerance=0.50)

    assert config.price_tolerance == 0.50