from __future__ import annotations

import pytest

from src.multi_strategy.adapters.historical_smc import (
    HISTORICAL_SMC_IMPLEMENTATION_KEY,
    HISTORICAL_SMC_STRATEGY_ID,
    build_historical_smc_strategy,
    historical_smc_manifest,
)


def test_historical_smc_manifest_is_valid():
    manifest = historical_smc_manifest()
    manifest.require_valid()

    assert manifest.strategy_id == HISTORICAL_SMC_STRATEGY_ID
    assert manifest.implementation_key == HISTORICAL_SMC_IMPLEMENTATION_KEY
    assert manifest.validate_parameters() == {
        "strategy_mode": "balanced"
    }


def test_historical_smc_factory_uses_existing_strategy_modes():
    pytest.importorskip("src.models.institutional_setup")

    from src.config.strategy_config import StrategyMode
    from src.strategy.smc_strategy import SMCStrategy

    strict = build_historical_smc_strategy(
        {"strategy_mode": "strict"}
    )
    relaxed = build_historical_smc_strategy(
        {"strategy_mode": "relaxed"}
    )

    assert isinstance(strict, SMCStrategy)
    assert strict.config.mode is StrategyMode.STRICT
    assert relaxed.config.mode is StrategyMode.RELAXED
