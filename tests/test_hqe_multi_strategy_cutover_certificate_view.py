from __future__ import annotations

from dataclasses import replace

import pytest

from src.multi_strategy.cutover_certificate import (
    CutoverCertificateError,
    DisabledCutoverCertificateStatus,
    DisabledCutoverReadinessCertificate,
)
from src.multi_strategy.cutover_certificate_view import (
    build_cutover_certificate_view,
)


def certificate(status=DisabledCutoverCertificateStatus.READY_FLAT_DISABLED):
    blockers = () if status is DisabledCutoverCertificateStatus.READY_FLAT_DISABLED else (
        "blocked",
    )
    return DisabledCutoverReadinessCertificate(
        status=status,
        strategy_id="hqe_current_smc_compatibility",
        strategy_version="1.0.0",
        implementation_key="hqe.current_smc.compatibility",
        selection_hash="selection-hash",
        one_active_set_hash="one-active-hash",
        lifecycle_plan_hash="lifecycle-plan-hash",
        activation_preflight_hash="preflight-hash",
        reconciliation_hash="reconciliation-hash",
        reconciliation_view_hash="reconciliation-view-hash",
        sandbox_bundle_hash="sandbox-bundle-hash",
        canonical_plan_hash="canonical-plan-hash",
        canonical_evidence_hashes={"state": "abc"},
        blockers=blockers,
    )


def test_ready_view_recommendation():
    view = build_cutover_certificate_view(certificate())
    assert (
        view.recommendation
        == "READY_FOR_HUMAN_CUTOVER_REVIEW_ACTIVATION_DISABLED"
    )
    assert view.human_review_ready is True


def test_open_position_view_recommendation():
    view = build_cutover_certificate_view(
        certificate(DisabledCutoverCertificateStatus.BLOCKED_OPEN_POSITION)
    )
    assert view.recommendation == "WAIT_FOR_FLAT_RECONCILIATION"


def test_runtime_view_recommendation():
    view = build_cutover_certificate_view(
        certificate(DisabledCutoverCertificateStatus.BLOCKED_RUNTIME_ACTIVE)
    )
    assert view.recommendation == "STOP_CANONICAL_RUNTIME_AND_REVIEW"


def test_reconciliation_view_recommendation():
    view = build_cutover_certificate_view(
        certificate(DisabledCutoverCertificateStatus.BLOCKED_RECONCILIATION)
    )
    assert view.recommendation == "RESOLVE_RECONCILIATION_DIVERGENCE"


def test_evidence_view_recommendation():
    view = build_cutover_certificate_view(
        certificate(DisabledCutoverCertificateStatus.BLOCKED_EVIDENCE)
    )
    assert view.recommendation == "RESOLVE_EVIDENCE_BLOCKERS"


def test_identity_view_recommendation():
    view = build_cutover_certificate_view(
        certificate(DisabledCutoverCertificateStatus.BLOCKED_IDENTITY)
    )
    assert view.recommendation == "REBUILD_EVIDENCE_IDENTITY_CHAIN"


def test_view_all_controls_are_disabled():
    payload = build_cutover_certificate_view(certificate()).to_dict()
    for key in (
        "activation_button_enabled",
        "strategy_switch_enabled",
        "selection_write_enabled",
        "lifecycle_write_enabled",
        "state_write_enabled",
        "ledger_write_enabled",
        "runtime_control_enabled",
        "runtime_cutover_enabled",
        "broker_execution_enabled",
        "real_money_enabled",
    ):
        assert payload[key] is False


def test_view_hash_is_deterministic():
    first = build_cutover_certificate_view(certificate())
    second = build_cutover_certificate_view(certificate())
    assert first.view_hash == second.view_hash


def test_view_rejects_unsafe_controls():
    view = build_cutover_certificate_view(certificate())
    with pytest.raises(CutoverCertificateError, match="read-only"):
        replace(view, read_only=False)
    with pytest.raises(CutoverCertificateError, match="mutating controls"):
        replace(view, activation_button_enabled=True)
