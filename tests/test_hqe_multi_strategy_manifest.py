from __future__ import annotations

import copy

import pytest

from src.multi_strategy.errors import ManifestValidationError
from src.multi_strategy.manifest import StrategyManifest

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

def test_valid_manifest_and_fingerprint_are_deterministic():
    manifest = sample_manifest()
    manifest.require_valid()
    reconstructed = StrategyManifest.from_dict(manifest.to_dict())
    reconstructed.require_valid()

    assert reconstructed.to_dict() == manifest.to_dict()
    assert reconstructed.fingerprint() == manifest.fingerprint()


def test_canonical_signal_mapping_cannot_be_changed():
    payload = sample_manifest().to_dict()
    payload["option_mapping"]["LONG"] = "PE_BUY"
    manifest = StrategyManifest.from_dict(payload)

    with pytest.raises(
        ManifestValidationError,
        match="canonical mapping",
    ):
        manifest.require_valid()


def test_all_execution_safety_flags_are_fail_closed():
    payload = sample_manifest().to_dict()
    payload["safety"]["real_orders_allowed"] = True
    manifest = StrategyManifest.from_dict(payload)

    with pytest.raises(
        ManifestValidationError,
        match="real_orders_allowed must remain false",
    ):
        manifest.require_valid()


def test_parameter_defaults_and_overrides_are_validated():
    manifest = sample_manifest()
    assert manifest.validate_parameters() == {
        "er20_min": 0.30,
        "minimum_dte": 1,
        "mode": "strict",
    }
    assert manifest.validate_parameters(
        {"er20_min": 0.45, "mode": "relaxed"}
    ) == {
        "er20_min": 0.45,
        "minimum_dte": 1,
        "mode": "relaxed",
    }

    with pytest.raises(
        ManifestValidationError,
        match="unknown parameter",
    ):
        manifest.validate_parameters({"unknown": 1})

    with pytest.raises(
        ManifestValidationError,
        match="exceeds maximum",
    ):
        manifest.validate_parameters({"er20_min": 1.5})


def test_duplicate_parameter_names_are_rejected():
    manifest = sample_manifest()
    payload = manifest.to_dict()
    payload["parameters"].append(copy.deepcopy(payload["parameters"][0]))
    duplicate = StrategyManifest.from_dict(payload)

    with pytest.raises(
        ManifestValidationError,
        match="duplicate parameter",
    ):
        duplicate.require_valid()

def test_untrusted_manifest_collection_types_fail_closed():
    payload = sample_manifest().to_dict()
    payload["supported_instruments"] = "NIFTY"
    payload["required_data_columns"] = "close"
    manifest = StrategyManifest.from_dict(payload)

    with pytest.raises(ManifestValidationError):
        manifest.require_valid()


def test_invalid_numeric_bounds_report_validation_error():
    payload = sample_manifest().to_dict()
    payload["parameters"][0]["minimum"] = "bad"
    manifest = StrategyManifest.from_dict(payload)

    with pytest.raises(
        ManifestValidationError,
        match="minimum must be numeric",
    ):
        manifest.require_valid()
