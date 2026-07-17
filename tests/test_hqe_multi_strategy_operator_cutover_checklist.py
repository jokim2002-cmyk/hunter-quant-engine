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
from src.multi_strategy.operator_cutover_checklist import (
    OperatorChecklistStatus,
    ReadOnlyOperatorCutoverChecklist,
    build_operator_cutover_checklist,
)


def certificate(status=DisabledCutoverCertificateStatus.READY_FLAT_DISABLED):
    blockers = () if status is DisabledCutoverCertificateStatus.READY_FLAT_DISABLED else ("blocked",)
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
        canonical_evidence_hashes={"state": "abc", "ledger": "def"},
        blockers=blockers,
    )


def test_ready_checklist_status():
    cert = certificate()
    checklist = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert))
    assert checklist.status is OperatorChecklistStatus.READY_REVIEW_EXPORT_DISABLED
    assert checklist.human_review_ready is True


def test_ready_checklist_has_eight_items():
    cert = certificate()
    checklist = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert))
    assert len(checklist.items) == 8
    assert all(item.passed for item in checklist.items)


def test_ready_checklist_zero_authority():
    cert = certificate()
    payload = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert)).to_dict()
    for key in (
        "export_authorized", "activation_authorized", "strategy_switch_authorized",
        "selection_write_authorized", "lifecycle_write_authorized", "state_write_authorized",
        "ledger_write_authorized", "runtime_control_authorized", "runtime_cutover_authorized",
        "broker_execution_authorized", "real_money_authorized",
    ):
        assert payload[key] is False


def test_blocked_certificate_status():
    cert = certificate(DisabledCutoverCertificateStatus.BLOCKED_OPEN_POSITION)
    checklist = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert))
    assert checklist.status is OperatorChecklistStatus.BLOCKED_CERTIFICATE
    assert checklist.human_review_ready is False


def test_view_identity_mismatch_blocks():
    cert = certificate()
    view = replace(build_cutover_certificate_view(cert), certificate_hash="wrong")
    checklist = build_operator_cutover_checklist(cert, view)
    assert checklist.status is OperatorChecklistStatus.BLOCKED_IDENTITY


def test_view_recommendation_mismatch_blocks_view():
    cert = certificate()
    view = replace(build_cutover_certificate_view(cert), recommendation="REVIEW_REQUIRED")
    checklist = build_operator_cutover_checklist(cert, view)
    assert checklist.status is OperatorChecklistStatus.BLOCKED_VIEW


def test_blocked_evidence_certificate_has_blockers():
    cert = certificate(DisabledCutoverCertificateStatus.BLOCKED_EVIDENCE)
    checklist = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert))
    assert checklist.status is OperatorChecklistStatus.BLOCKED_CERTIFICATE
    assert checklist.blockers


def test_checklist_hash_is_deterministic():
    cert = certificate()
    first = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert))
    second = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert))
    assert first.checklist_hash == second.checklist_hash


def test_checklist_item_hashes_present():
    cert = certificate()
    checklist = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert))
    assert all(item.evidence_hash for item in checklist.items)


def test_checklist_rejects_read_write_mode():
    cert = certificate()
    checklist = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert))
    with pytest.raises(CutoverCertificateError, match="read-only"):
        replace(checklist, read_only=False)


def test_checklist_rejects_authority():
    cert = certificate()
    checklist = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert))
    with pytest.raises(CutoverCertificateError, match="cannot grant authority"):
        replace(checklist, activation_authorized=True)


def test_ready_checklist_rejects_failed_item():
    cert = certificate()
    checklist = build_operator_cutover_checklist(cert, build_cutover_certificate_view(cert))
    failed = replace(checklist.items[0], passed=False)
    with pytest.raises(CutoverCertificateError, match="all items"):
        replace(checklist, items=(failed,) + checklist.items[1:])
