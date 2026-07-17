from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

import pytest

from src.multi_strategy.activation import (
    ActivationPreflightStatus,
    DisabledActivationPreflightResult,
)
from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    build_current_smc_adapter,
    current_smc_manifest,
)
from src.multi_strategy.cutover_certificate import (
    CutoverCertificateError,
    DisabledCutoverCertificateStatus,
    build_disabled_cutover_readiness_certificate,
)
from src.multi_strategy.lifecycle_adapter import (
    DisabledCanonicalLifecyclePlan,
    DisabledLifecyclePlanStatus,
)
from src.multi_strategy.lifecycle_reconciliation import (
    LifecycleReconciliationStatus,
    LifecycleSemanticObservation,
    ReadOnlyLifecycleReconciliation,
)
from src.multi_strategy.lifecycle_reconciliation_view import (
    build_reconciliation_view,
)
from src.multi_strategy.one_active import DisabledOneActiveStrategySet
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle


def selection():
    registry = StrategyRegistry(
        {CURRENT_SMC_IMPLEMENTATION_KEY: build_current_smc_adapter}
    )
    registration = registry.register(
        current_smc_manifest(), source="phase4m:test"
    )
    return StrategySelectionSnapshot.from_registration(registration)


def one_active(selected):
    return DisabledOneActiveStrategySet.build(selected, (selected,))


def preflight(selected, status=ActivationPreflightStatus.READY_DISABLED):
    blockers = () if status is ActivationPreflightStatus.READY_DISABLED else (
        "preflight blocked",
    )
    return DisabledActivationPreflightResult(
        status=status,
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        recovery_snapshot_hash="recovery-hash",
        operator_view_hash="operator-hash",
        runtime_observation_hash="runtime-hash",
        blockers=blockers,
        minimum_cycles=3,
        observed_cycles=3,
        match_count=3,
        mismatch_count=0,
    )


def lifecycle_plan(
    selected,
    active,
    *,
    status=DisabledLifecyclePlanStatus.READY_DISABLED,
    lifecycle=PositionLifecycle.FLAT,
):
    blockers = () if status is DisabledLifecyclePlanStatus.READY_DISABLED else (
        "lifecycle plan blocked",
    )
    pf = preflight(selected)
    return DisabledCanonicalLifecyclePlan(
        status=status,
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        implementation_key=selected.implementation_key,
        manifest_fingerprint=selected.manifest_fingerprint,
        selection_hash=selected.selection_hash,
        one_active_set_hash=active.set_hash,
        current_state_hash="state-hash",
        recovery_snapshot_hash="recovery-hash",
        preflight_hash=pf.preflight_hash,
        runtime_observation_hash="runtime-hash",
        namespace_directory="phase4m-namespace",
        current_lifecycle=lifecycle,
        blockers=blockers,
    )


def observation(lifecycle="FLAT"):
    if lifecycle == "OPEN":
        return LifecycleSemanticObservation(
            lifecycle="OPEN",
            opened_count=1,
            closed_count=0,
            unmatched_open_count=1,
            option_side="CE_BUY",
            option_symbol="NIFTY_PHASE4M_CE",
            quantity=75,
            entry=100.0,
        )
    return LifecycleSemanticObservation(
        lifecycle="FLAT",
        opened_count=1,
        closed_count=1,
        unmatched_open_count=0,
    )


def reconciliation(
    selected,
    status=LifecycleReconciliationStatus.MATCH_FLAT,
):
    if status is LifecycleReconciliationStatus.MATCH_OPEN:
        sandbox = observation("OPEN")
        canonical = observation("OPEN")
        differences = ()
    elif status is LifecycleReconciliationStatus.MATCH_FLAT:
        sandbox = observation()
        canonical = observation()
        differences = ()
    elif status is LifecycleReconciliationStatus.BLOCKED_RUNTIME_RUNNING:
        sandbox = observation()
        canonical = None
        differences = ("canonical runtime appears to be running",)
    elif status is LifecycleReconciliationStatus.NO_CANONICAL_EVIDENCE:
        sandbox = observation()
        canonical = None
        differences = ("no canonical evidence",)
    else:
        sandbox = observation("OPEN")
        canonical = observation()
        differences = ("lifecycle differs",)
    return ReadOnlyLifecycleReconciliation(
        status=status,
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        sandbox_bundle_hash="bundle-hash",
        canonical_plan_hash="canonical-plan-hash",
        sandbox=sandbox,
        canonical=canonical,
        canonical_evidence_hashes={"state": "abc", "ledger": "def"},
        differences=differences,
    )


def certificate(
    *,
    plan_status=DisabledLifecyclePlanStatus.READY_DISABLED,
    reconciliation_status=LifecycleReconciliationStatus.MATCH_FLAT,
    lifecycle=PositionLifecycle.FLAT,
):
    selected = selection()
    active = one_active(selected)
    plan = lifecycle_plan(
        selected,
        active,
        status=plan_status,
        lifecycle=lifecycle,
    )
    result = reconciliation(selected, reconciliation_status)
    view = build_reconciliation_view(result)
    return build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=active,
        lifecycle_plan=plan,
        reconciliation=result,
        reconciliation_view=view,
    )


def test_ready_flat_certificate():
    result = certificate()
    assert result.status is DisabledCutoverCertificateStatus.READY_FLAT_DISABLED
    assert result.human_review_ready is True


def test_ready_certificate_is_review_only():
    payload = certificate().to_dict()
    for key in (
        "activation_authorized",
        "strategy_switch_authorized",
        "selection_write_authorized",
        "lifecycle_write_authorized",
        "state_write_authorized",
        "ledger_write_authorized",
        "runtime_connection_authorized",
        "runtime_control_authorized",
        "runtime_cutover_authorized",
        "broker_execution_authorized",
        "real_money_authorized",
    ):
        assert payload[key] is False


def test_match_open_blocks_cutover_review():
    result = certificate(
        reconciliation_status=LifecycleReconciliationStatus.MATCH_OPEN
    )
    assert result.status is DisabledCutoverCertificateStatus.BLOCKED_OPEN_POSITION


def test_lifecycle_plan_open_blocks_cutover_review():
    result = certificate(
        plan_status=DisabledLifecyclePlanStatus.BLOCKED_OPEN_POSITION,
        lifecycle=PositionLifecycle.OPEN,
    )
    assert result.status is DisabledCutoverCertificateStatus.BLOCKED_OPEN_POSITION


def test_lifecycle_runtime_status_blocks():
    result = certificate(
        plan_status=DisabledLifecyclePlanStatus.BLOCKED_RUNTIME_ACTIVE
    )
    assert result.status is DisabledCutoverCertificateStatus.BLOCKED_RUNTIME_ACTIVE


def test_reconciliation_runtime_status_blocks():
    result = certificate(
        reconciliation_status=LifecycleReconciliationStatus.BLOCKED_RUNTIME_RUNNING
    )
    assert result.status is DisabledCutoverCertificateStatus.BLOCKED_RUNTIME_ACTIVE


def test_divergence_blocks_reconciliation():
    result = certificate(
        reconciliation_status=LifecycleReconciliationStatus.DIVERGED_LIFECYCLE
    )
    assert result.status is DisabledCutoverCertificateStatus.BLOCKED_RECONCILIATION


def test_missing_canonical_evidence_blocks_reconciliation():
    result = certificate(
        reconciliation_status=LifecycleReconciliationStatus.NO_CANONICAL_EVIDENCE
    )
    assert result.status is DisabledCutoverCertificateStatus.BLOCKED_RECONCILIATION


def test_blocked_lifecycle_evidence_blocks_certificate():
    result = certificate(
        plan_status=DisabledLifecyclePlanStatus.BLOCKED_EVIDENCE
    )
    assert result.status is DisabledCutoverCertificateStatus.BLOCKED_EVIDENCE


def test_non_flat_view_recommendation_blocks_evidence():
    selected = selection()
    active = one_active(selected)
    plan = lifecycle_plan(selected, active)
    result = reconciliation(selected)
    view = replace(
        build_reconciliation_view(result),
        recommendation="REVIEW_REQUIRED_READ_ONLY",
    )
    cert = build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=active,
        lifecycle_plan=plan,
        reconciliation=result,
        reconciliation_view=view,
    )
    assert cert.status is DisabledCutoverCertificateStatus.BLOCKED_EVIDENCE


def test_view_hash_mismatch_blocks_identity():
    selected = selection()
    active = one_active(selected)
    plan = lifecycle_plan(selected, active)
    result = reconciliation(selected)
    view = replace(
        build_reconciliation_view(result),
        reconciliation_hash="wrong-reconciliation-hash",
    )
    cert = build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=active,
        lifecycle_plan=plan,
        reconciliation=result,
        reconciliation_view=view,
    )
    assert cert.status is DisabledCutoverCertificateStatus.BLOCKED_IDENTITY


def test_one_active_hash_mismatch_blocks_identity():
    selected = selection()
    active = one_active(selected)
    plan = replace(lifecycle_plan(selected, active), one_active_set_hash="wrong")
    result = reconciliation(selected)
    cert = build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=active,
        lifecycle_plan=plan,
        reconciliation=result,
        reconciliation_view=build_reconciliation_view(result),
    )
    assert cert.status is DisabledCutoverCertificateStatus.BLOCKED_IDENTITY


def test_certificate_hash_is_deterministic():
    assert certificate().certificate_hash == certificate().certificate_hash


def test_canonical_hashes_are_sorted_and_immutable():
    cert = certificate()
    assert list(cert.canonical_evidence_hashes) == ["ledger", "state"]
    assert isinstance(cert.canonical_evidence_hashes, MappingProxyType)


def test_certificate_rejects_authority_flag():
    with pytest.raises(CutoverCertificateError, match="cannot grant authority"):
        replace(certificate(), runtime_cutover_authorized=True)
