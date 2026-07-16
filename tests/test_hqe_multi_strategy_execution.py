from __future__ import annotations

import json

import pytest

from src.multi_strategy.adapters.historical_smc import (
    historical_smc_manifest,
)
from src.multi_strategy.execution import (
    ExecutionMode,
    StrategyRunMetadata,
    canonical_mapping_hash,
)
from src.multi_strategy.registry import StrategyRegistry


def test_canonical_mapping_hash_is_order_independent():
    assert canonical_mapping_hash({"a": 1, "b": 2}) == (
        canonical_mapping_hash({"b": 2, "a": 1})
    )


def test_run_metadata_normalizes_parameters_and_is_json_ready():
    manifest = historical_smc_manifest()
    registry = StrategyRegistry()
    registration = registry.register(manifest)

    metadata = StrategyRunMetadata.from_registration(
        registration,
        parameters={},
        execution_mode=ExecutionMode.BACKTEST,
        symbol="NIFTY",
        timeframe="5m",
        data_identity="sha256:test",
        data_start="2026-01-01T09:15:00",
        data_end="2026-01-01T15:30:00",
    )

    payload = metadata.to_dict()
    assert payload["strategy_id"] == manifest.strategy_id
    assert payload["parameters"] == {"strategy_mode": "balanced"}
    assert payload["execution_mode"] == "BACKTEST"
    json.dumps(payload, sort_keys=True)

    with pytest.raises(TypeError):
        metadata.parameters["strategy_mode"] = "strict"


def test_run_metadata_requires_data_identity():
    manifest = historical_smc_manifest()
    registry = StrategyRegistry()
    registration = registry.register(manifest)

    with pytest.raises(ValueError, match="data_identity"):
        StrategyRunMetadata.from_registration(
            registration,
            parameters={},
            execution_mode=ExecutionMode.BACKTEST,
            symbol="NIFTY",
            timeframe="5m",
            data_identity="",
        )
