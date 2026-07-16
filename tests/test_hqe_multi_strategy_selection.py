from __future__ import annotations

import copy

import pytest

from src.multi_strategy.errors import (
    SelectionValidationError,
    UnreviewedImplementationError,
)
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    ParameterSpec,
    StrategyManifest,
)
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.selection import (
    SelectionActivationStatus,
    StrategySelectionSnapshot,
)


IMPLEMENTATION_KEY = "hqe.test.selection_v1"


class FakeStrategy:
    def generate(self, context):
        return ()


def manifest(strategy_id="selection_test"):
    return StrategyManifest(
        strategy_id=strategy_id,
        display_name="Selection Test",
        strategy_version="1.0.0",
        description="test",
        implementation_key=IMPLEMENTATION_KEY,
        supported_instruments=("TEST",),
        required_timeframe="5m",
        required_data_columns=("close",),
        warmup_bars=0,
        parameters=(
            ParameterSpec(
                name="threshold",
                value_type="number",
                default=0.30,
                minimum=0.0,
                maximum=1.0,
            ),
        ),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    )


def reviewed_registration(strategy_id="selection_test"):
    registry = StrategyRegistry(
        {IMPLEMENTATION_KEY: lambda parameters: FakeStrategy()}
    )
    return registry.register(manifest(strategy_id))


def test_selection_is_deterministic_and_disabled():
    registration = reviewed_registration()
    first = StrategySelectionSnapshot.from_registration(
        registration, {"threshold": 0.45}
    )
    second = StrategySelectionSnapshot.from_registration(
        registration, {"threshold": 0.45}
    )

    assert first.selection_hash == second.selection_hash
    assert first.activation_status is SelectionActivationStatus.DISABLED
    assert first.runtime_connected is False
    assert first.parameters == {"threshold": 0.45}


def test_selection_round_trip_verifies_hash():
    selection = StrategySelectionSnapshot.from_registration(
        reviewed_registration()
    )
    loaded = StrategySelectionSnapshot.from_dict(selection.to_dict())
    assert loaded == selection
    assert loaded.selection_hash == selection.selection_hash


def test_selection_rejects_tampering():
    selection = StrategySelectionSnapshot.from_registration(
        reviewed_registration()
    )
    payload = copy.deepcopy(selection.to_dict())
    payload["parameters"]["threshold"] = 0.80

    with pytest.raises(SelectionValidationError, match="parameters_hash"):
        StrategySelectionSnapshot.from_dict(payload)


def test_selection_cannot_enable_runtime():
    selection = StrategySelectionSnapshot.from_registration(
        reviewed_registration()
    )
    payload = selection.to_dict()
    payload["runtime_connected"] = True

    with pytest.raises(SelectionValidationError, match="runtime"):
        StrategySelectionSnapshot.from_dict(payload)


def test_metadata_only_registration_cannot_be_selected():
    registry = StrategyRegistry()
    registration = registry.register(manifest())

    with pytest.raises(UnreviewedImplementationError, match="metadata-only"):
        StrategySelectionSnapshot.from_registration(registration)
