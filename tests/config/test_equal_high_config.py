from src.config.equal_high_config import EqualHighConfig, DEFAULT_EQUAL_HIGH_CONFIG


def test_default_equal_high_config_is_enabled():
    assert DEFAULT_EQUAL_HIGH_CONFIG.enabled is True


def test_default_equal_high_config_has_price_tolerance():
    assert DEFAULT_EQUAL_HIGH_CONFIG.price_tolerance == 0.20


def test_equal_high_config_can_be_disabled():
    config = EqualHighConfig(enabled=False)

    assert config.enabled is False


def test_equal_high_config_accepts_custom_price_tolerance():
    config = EqualHighConfig(price_tolerance=0.50)

    assert config.price_tolerance == 0.50
