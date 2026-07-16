from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from scripts.hqe_multi_strategy_runtime_shadow_view_dry_run import (
    run_dry_run as run_phase4f_dry_run,
)
from src.multi_strategy.activation import DisabledActivationPreflight
from src.multi_strategy.adapters.current_smc import current_smc_manifest
from src.multi_strategy.evidence_view import OperatorEvidenceViewReader
from src.multi_strategy.errors import ProductUiModelError
from src.multi_strategy.recovery import OfflineRestartRecoveryReader
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.ui_model import ReadOnlyProductStrategyUiModel


@pytest.fixture(scope="module")
def model_evidence(tmp_path_factory):
    root = tmp_path_factory.mktemp("phase4g_ui")
    payload = run_phase4f_dry_run(root / "phase4f")
    selection = StrategySelectionSnapshot.from_dict(
        payload["phase4c_copy"]["selection"]
    )
    target_root = Path(payload["phase4c_copy"]["target_root"])
    recovery = OfflineRestartRecoveryReader(target_root).read(selection)
    operator_view = OperatorEvidenceViewReader(
        payload["journal_path"],
        strategy_namespace=recovery.namespace_directory,
    ).read()
    manifest = current_smc_manifest()
    runtime_payload = {
        "status": "STOPPED",
        "pid": None,
        "paper_only": True,
        "broker_execution": False,
    }
    observation = StableRuntimeObservation(
        observed_at="2026-07-16T11:25:00+05:30",
        runtime_status="STOPPED",
        runtime_pid=None,
        first_read=runtime_payload,
        second_read=dict(runtime_payload),
    )
    preflight = DisabledActivationPreflight().evaluate(
        manifest=manifest,
        selection=selection,
        recovery=recovery,
        operator_view=operator_view,
        runtime_observation=observation,
    )
    return manifest, selection, operator_view, observation, preflight


def build_model(model_evidence):
    manifest, selection, operator_view, observation, preflight = model_evidence
    return ReadOnlyProductStrategyUiModel.build(
        manifest=manifest,
        selection=selection,
        preflight=preflight,
        operator_view=operator_view,
        runtime_observation=observation,
    )


def test_product_model_is_display_only(model_evidence):
    model = build_model(model_evidence)
    payload = model.to_dict()

    assert payload["preflight_status"] == "READY_DISABLED"
    assert payload["trader_status"] == (
        "Evidence ready — activation remains locked"
    )
    assert payload["read_only"] is True
    assert set(payload["controls"].values()) == {False}
    assert model.match_count == model.cycle_count == 3
    assert model.mismatch_count == 0


def test_product_model_displays_exact_identity_and_parameters(model_evidence):
    manifest, selection, _, _, _ = model_evidence
    model = build_model(model_evidence)

    assert model.strategy_name == manifest.display_name
    assert model.strategy_id == selection.strategy_id
    assert model.strategy_version == selection.strategy_version
    assert dict(model.parameters) == dict(selection.parameters)
    assert model.selection_hash == selection.selection_hash


def test_product_model_markdown_keeps_controls_disabled(model_evidence):
    markdown = build_model(model_evidence).render_markdown()

    assert "activation remains locked" in markdown
    assert "Select strategy: **DISABLED**" in markdown
    assert "Activate strategy: **DISABLED**" in markdown
    assert "Real orders: **DISABLED**" in markdown


def test_product_model_parameters_are_immutable(model_evidence):
    model = build_model(model_evidence)

    with pytest.raises(TypeError):
        model.parameters["minimum_dte"] = 2


def test_product_model_hash_is_deterministic(model_evidence):
    first = build_model(model_evidence)
    second = build_model(model_evidence)

    assert first.model_hash == second.model_hash
    assert first.to_dict() == second.to_dict()


def test_product_model_manifest_mismatch_fails_closed(model_evidence):
    manifest, selection, operator_view, observation, preflight = model_evidence
    changed = replace(manifest, display_name="Changed Name")

    with pytest.raises(ProductUiModelError, match="fingerprint"):
        ReadOnlyProductStrategyUiModel.build(
            manifest=changed,
            selection=selection,
            preflight=preflight,
            operator_view=operator_view,
            runtime_observation=observation,
        )
