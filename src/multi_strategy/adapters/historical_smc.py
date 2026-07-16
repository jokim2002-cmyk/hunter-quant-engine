"""Reviewed registry adapter for HQE's existing historical SMCStrategy."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    ParameterSpec,
    StrategyManifest,
)

HISTORICAL_SMC_STRATEGY_ID = "hqe_historical_smc_backtest"
HISTORICAL_SMC_STRATEGY_VERSION = "1.0.0"
HISTORICAL_SMC_IMPLEMENTATION_KEY = (
    "hqe.reviewed.historical_smc_backtest_v1"
)
SUPPORTED_SMC_MODES = ("strict", "balanced", "relaxed")


def historical_smc_manifest() -> StrategyManifest:
    """Return metadata for the existing deterministic SMCStrategy."""

    return StrategyManifest(
        strategy_id=HISTORICAL_SMC_STRATEGY_ID,
        display_name="HQE Historical SMC Backtest",
        strategy_version=HISTORICAL_SMC_STRATEGY_VERSION,
        description=(
            "Reviewed adapter for the existing SMCStrategy used by "
            "HQE's historical BacktestPipeline."
        ),
        implementation_key=HISTORICAL_SMC_IMPLEMENTATION_KEY,
        supported_instruments=("INDEX_OHLCV",),
        required_timeframe="5m",
        required_data_columns=(
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ),
        warmup_bars=1,
        parameters=(
            ParameterSpec(
                name="strategy_mode",
                value_type="choice",
                default="balanced",
                choices=SUPPORTED_SMC_MODES,
                description=(
                    "Existing SMCStrategy strict, balanced, or relaxed mode."
                ),
            ),
        ),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    ).require_valid()


def build_historical_smc_strategy(
    parameters: Mapping[str, Any] | None = None,
):
    """Build the existing SMCStrategy from a validated mode snapshot."""

    normalized = historical_smc_manifest().validate_parameters(
        parameters
    )
    from src.config.strategy_config import smc_strategy_config_for_mode
    from src.strategy.smc_strategy import SMCStrategy

    return SMCStrategy(
        config=smc_strategy_config_for_mode(
            str(normalized["strategy_mode"])
        )
    )
