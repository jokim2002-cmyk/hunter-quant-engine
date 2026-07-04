"""
Strategy Config Tests
"""

import pytest

from src.config.strategy_config import (
    BALANCED_SMC_STRATEGY_CONFIG,
    DEFAULT_SMC_STRATEGY_CONFIG,
    RELAXED_SMC_STRATEGY_CONFIG,
    STRICT_SMC_STRATEGY_CONFIG,
    SMCStrategyConfig,
    StrategyMode,
    normalize_strategy_mode,
    smc_strategy_config_for_mode,
    supported_strategy_mode_names,
)
from src.strategy.signal_strength import SignalStrength


def test_default_smc_strategy_config_is_balanced():
    assert DEFAULT_SMC_STRATEGY_CONFIG == BALANCED_SMC_STRATEGY_CONFIG
    assert DEFAULT_SMC_STRATEGY_CONFIG.mode is StrategyMode.BALANCED
    assert DEFAULT_SMC_STRATEGY_CONFIG.directional_signal_strength is (
        SignalStrength.MEDIUM
    )
    assert DEFAULT_SMC_STRATEGY_CONFIG.directional_signal_confidence == 0.75
    assert DEFAULT_SMC_STRATEGY_CONFIG.neutral_signal_strength is SignalStrength.WEAK
    assert DEFAULT_SMC_STRATEGY_CONFIG.neutral_signal_confidence == 0.0
    assert DEFAULT_SMC_STRATEGY_CONFIG.emit_neutral_signal is True


def test_strategy_modes_have_expected_presets():
    assert STRICT_SMC_STRATEGY_CONFIG.mode is StrategyMode.STRICT
    assert STRICT_SMC_STRATEGY_CONFIG.directional_signal_confidence == 0.9
    assert STRICT_SMC_STRATEGY_CONFIG.directional_signal_strength is (
        SignalStrength.STRONG
    )

    assert BALANCED_SMC_STRATEGY_CONFIG.mode is StrategyMode.BALANCED
    assert BALANCED_SMC_STRATEGY_CONFIG.directional_signal_confidence == 0.75

    assert RELAXED_SMC_STRATEGY_CONFIG.mode is StrategyMode.RELAXED
    assert RELAXED_SMC_STRATEGY_CONFIG.directional_signal_confidence == 0.6


def test_strategy_mode_can_be_normalized_from_string():
    config = SMCStrategyConfig(mode="strict")

    assert config.mode is StrategyMode.STRICT
    assert normalize_strategy_mode("relaxed") is StrategyMode.RELAXED


def test_unsupported_strategy_mode_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported strategy mode"):
        SMCStrategyConfig(mode="random")


def test_directional_signal_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValueError, match="directional_signal_confidence"):
        SMCStrategyConfig(directional_signal_confidence=-0.1)

    with pytest.raises(ValueError, match="directional_signal_confidence"):
        SMCStrategyConfig(directional_signal_confidence=1.1)


def test_neutral_signal_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValueError, match="neutral_signal_confidence"):
        SMCStrategyConfig(neutral_signal_confidence=-0.1)

    with pytest.raises(ValueError, match="neutral_signal_confidence"):
        SMCStrategyConfig(neutral_signal_confidence=1.1)


def test_supported_strategy_mode_names_are_cli_friendly():
    assert supported_strategy_mode_names() == (
        "strict",
        "balanced",
        "relaxed",
    )


def test_smc_strategy_config_for_mode_returns_expected_preset():
    assert smc_strategy_config_for_mode("strict") == STRICT_SMC_STRATEGY_CONFIG
    assert smc_strategy_config_for_mode("balanced") == BALANCED_SMC_STRATEGY_CONFIG
    assert smc_strategy_config_for_mode("relaxed") == RELAXED_SMC_STRATEGY_CONFIG
