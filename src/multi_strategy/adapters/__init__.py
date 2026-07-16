"""Reviewed compatibility adapters for existing HQE strategies."""

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
    CurrentSmcCompatibilityAdapter,
    build_current_smc_adapter,
    current_smc_manifest,
)
from src.multi_strategy.adapters.historical_smc import (
    HISTORICAL_SMC_IMPLEMENTATION_KEY,
    HISTORICAL_SMC_STRATEGY_ID,
    HISTORICAL_SMC_STRATEGY_VERSION,
    SUPPORTED_SMC_MODES,
    build_historical_smc_strategy,
    historical_smc_manifest,
)

__all__ = [
    "CURRENT_SMC_IMPLEMENTATION_KEY",
    "CURRENT_SMC_STRATEGY_ID",
    "CURRENT_SMC_STRATEGY_VERSION",
    "CurrentSmcCompatibilityAdapter",
    "HISTORICAL_SMC_IMPLEMENTATION_KEY",
    "HISTORICAL_SMC_STRATEGY_ID",
    "HISTORICAL_SMC_STRATEGY_VERSION",
    "SUPPORTED_SMC_MODES",
    "build_current_smc_adapter",
    "build_historical_smc_strategy",
    "current_smc_manifest",
    "historical_smc_manifest",
]
