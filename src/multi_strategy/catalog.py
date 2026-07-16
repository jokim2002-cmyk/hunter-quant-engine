"""Reviewed built-in catalog for the current multi-strategy phases."""

from __future__ import annotations

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    build_current_smc_adapter,
    current_smc_manifest,
)
from src.multi_strategy.adapters.historical_smc import (
    HISTORICAL_SMC_IMPLEMENTATION_KEY,
    build_historical_smc_strategy,
    historical_smc_manifest,
)
from src.multi_strategy.registry import StrategyRegistry


def build_phase3_registry() -> StrategyRegistry:
    """Build a deterministic registry with reviewed local factories only."""

    registry = StrategyRegistry(
        {
            CURRENT_SMC_IMPLEMENTATION_KEY: build_current_smc_adapter,
            HISTORICAL_SMC_IMPLEMENTATION_KEY: (
                build_historical_smc_strategy
            ),
        }
    )
    registry.register(
        current_smc_manifest(),
        source="builtin:current_smc_compatibility",
    )
    registry.register(
        historical_smc_manifest(),
        source="builtin:historical_smc_backtest",
    )
    return registry
