from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from src.multi_strategy.errors import (
    DuplicateStrategyError,
    UnreviewedImplementationError,
)
from src.multi_strategy.registry import (
    RegistrationStatus,
    StrategyRegistry,
)

from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    ParameterSpec,
    StrategyManifest,
)


def sample_manifest(
    *,
    strategy_id: str = "sample_smc",
    strategy_version: str = "1.0.0",
    implementation_key: str = "hqe.reviewed.sample_smc",
) -> StrategyManifest:
    return StrategyManifest(
        strategy_id=strategy_id,
        display_name="Sample SMC",
        strategy_version=strategy_version,
        description="Deterministic paper-only test strategy.",
        implementation_key=implementation_key,
        supported_instruments=("NIFTY_INDEX_OPTION_BUY",),
        required_timeframe="5m",
        required_data_columns=(
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ),
        warmup_bars=20,
        parameters=(
            ParameterSpec(
                name="er20_min",
                value_type="number",
                default=0.30,
                minimum=0.0,
                maximum=1.0,
            ),
            ParameterSpec(
                name="minimum_dte",
                value_type="integer",
                default=1,
                minimum=0,
                maximum=30,
            ),
            ParameterSpec(
                name="mode",
                value_type="choice",
                default="strict",
                choices=("strict", "relaxed"),
            ),
        ),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    )

class DummyStrategy:
    def __init__(self, parameters: Mapping[str, Any]) -> None:
        self.parameters = dict(parameters)

    def generate(self, context):
        del context
        return ()


def dummy_factory(parameters: Mapping[str, Any]) -> DummyStrategy:
    return DummyStrategy(parameters)


def test_duplicate_id_and_version_are_rejected():
    registry = StrategyRegistry()
    manifest = sample_manifest()
    registry.register(manifest)

    with pytest.raises(DuplicateStrategyError):
        registry.register(manifest)


def test_same_id_with_a_new_version_is_allowed():
    registry = StrategyRegistry()
    first = registry.register(sample_manifest())
    second = registry.register(
        sample_manifest(strategy_version="1.1.0")
    )

    assert first.registration_key == ("sample_smc", "1.0.0")
    assert second.registration_key == ("sample_smc", "1.1.0")


def test_unreviewed_implementation_is_metadata_only():
    registry = StrategyRegistry()
    registration = registry.register(sample_manifest())

    assert registration.status is RegistrationStatus.METADATA_ONLY
    with pytest.raises(UnreviewedImplementationError):
        registry.create("sample_smc", "1.0.0")


def test_reviewed_factory_receives_validated_parameters():
    manifest = sample_manifest()
    registry = StrategyRegistry(
        {manifest.implementation_key: dummy_factory}
    )
    registration = registry.register(manifest)
    strategy = registry.create(
        "sample_smc",
        "1.0.0",
        parameters={"er20_min": 0.55},
    )

    assert (
        registration.status
        is RegistrationStatus.EXECUTABLE_REVIEWED
    )
    assert strategy.parameters == {
        "er20_min": 0.55,
        "minimum_dte": 1,
        "mode": "strict",
    }


def test_batch_registration_is_atomic_on_duplicate():
    registry = StrategyRegistry()
    manifests = (
        sample_manifest(),
        sample_manifest(),
    )

    with pytest.raises(DuplicateStrategyError):
        registry.register_many(manifests)

    assert registry.list_registrations() == ()
