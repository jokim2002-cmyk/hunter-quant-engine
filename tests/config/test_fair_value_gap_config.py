from dataclasses import FrozenInstanceError

import pytest

from src.config.fair_value_gap_config import (
    DEFAULT_FAIR_VALUE_GAP_CONFIG,
    FairValueGapConfig,
)


def test_default_fair_value_gap_config_is_enabled():
    assert DEFAULT_FAIR_VALUE_GAP_CONFIG.enabled is True


def test_default_minimum_gap_size_is_zero():
    assert DEFAULT_FAIR_VALUE_GAP_CONFIG.minimum_gap_size == 0.0


def test_default_require_body_imbalance_is_false():
    assert DEFAULT_FAIR_VALUE_GAP_CONFIG.require_body_imbalance is False


def test_default_allow_wick_gap_is_true():
    assert DEFAULT_FAIR_VALUE_GAP_CONFIG.allow_wick_gap is True


def test_custom_fair_value_gap_config():
    config = FairValueGapConfig(
        enabled=False,
        minimum_gap_size=0.25,
        require_body_imbalance=True,
        allow_wick_gap=False,
    )

    assert config.enabled is False
    assert config.minimum_gap_size == 0.25
    assert config.require_body_imbalance is True
    assert config.allow_wick_gap is False


def test_fair_value_gap_config_is_immutable():
    config = FairValueGapConfig()

    with pytest.raises(FrozenInstanceError):
        config.minimum_gap_size = 1.0