from dataclasses import FrozenInstanceError

import pytest

from src.config.liquidity_sweep_config import (
    DEFAULT_LIQUIDITY_SWEEP_CONFIG,
    LiquiditySweepConfig,
)


def test_default_liquidity_sweep_config_is_enabled():
    assert DEFAULT_LIQUIDITY_SWEEP_CONFIG.enabled is True


def test_default_sweep_tolerance_is_zero():
    assert DEFAULT_LIQUIDITY_SWEEP_CONFIG.sweep_tolerance == 0.0


def test_default_require_close_back_inside_is_true():
    assert DEFAULT_LIQUIDITY_SWEEP_CONFIG.require_close_back_inside is True


def test_custom_liquidity_sweep_config():
    config = LiquiditySweepConfig(
        enabled=False,
        sweep_tolerance=0.25,
        require_close_back_inside=False,
    )

    assert config.enabled is False
    assert config.sweep_tolerance == 0.25
    assert config.require_close_back_inside is False


def test_liquidity_sweep_config_is_immutable():
    config = LiquiditySweepConfig()

    with pytest.raises(FrozenInstanceError):
        config.enabled = False