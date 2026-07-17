from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.multi_strategy.cutover_certificate import (
    DisabledCutoverCertificateStatus,
    DisabledCutoverReadinessCertificate,
)
from src.multi_strategy.cutover_certificate_view import build_cutover_certificate_view
from src.multi_strategy.evidence_bundle_export import (
    EvidenceBundleExportError,
    EvidenceBundleExportStatus,
    export_operator_evidence_bundle,
    verify_operator_evidence_bundle,
)
from src.multi_strategy.operator_cutover_checklist import build_operator_cutover_checklist


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


def ready_evidence():
    cert = certificate()
    view = build_cutover_certificate_view(cert)
    checklist = build_operator_cutover_checklist(cert, view)
    return cert, view, checklist


def export_root(tmp_path: Path) -> Path:
    return tmp_path / "HQE_MULTI_STRATEGY_PHASE4N_REVIEW_EXPORT"


def test_atomic_export_and_verify(tmp_path):
    cert, view, checklist = ready_evidence()
    manifest, bundle = export_operator_evidence_bundle(
        output_root=export_root(tmp_path), export_id="review-1",
        certificate=cert, view=view, checklist=checklist,
    )
    assert manifest.status is EvidenceBundleExportStatus.EXPORTED_REVIEW_ONLY
    assert verify_operator_evidence_bundle(bundle).manifest_hash == manifest.manifest_hash


def test_export_contains_four_files(tmp_path):
    cert, view, checklist = ready_evidence()
    _, bundle = export_operator_evidence_bundle(
        output_root=export_root(tmp_path), export_id="review-1",
        certificate=cert, view=view, checklist=checklist,
    )
    assert sorted(p.name for p in bundle.iterdir()) == [
        "cutover_certificate.json", "cutover_certificate_view.json",
        "evidence_bundle_manifest.json", "operator_cutover_checklist.json",
    ]


def test_repeated_identical_export_is_idempotent(tmp_path):
    cert, view, checklist = ready_evidence()
    root = export_root(tmp_path)
    export_operator_evidence_bundle(output_root=root, export_id="review-1", certificate=cert, view=view, checklist=checklist)
    manifest, _ = export_operator_evidence_bundle(output_root=root, export_id="review-1", certificate=cert, view=view, checklist=checklist)
    assert manifest.status is EvidenceBundleExportStatus.ALREADY_EXPORTED


def test_blocked_checklist_cannot_export(tmp_path):
    cert = certificate(DisabledCutoverCertificateStatus.BLOCKED_OPEN_POSITION)
    view = build_cutover_certificate_view(cert)
    checklist = build_operator_cutover_checklist(cert, view)
    with pytest.raises(EvidenceBundleExportError, match="blocked checklist"):
        export_operator_evidence_bundle(output_root=export_root(tmp_path), export_id="blocked", certificate=cert, view=view, checklist=checklist)


def test_unsafe_export_path_is_blocked(tmp_path):
    cert, view, checklist = ready_evidence()
    with pytest.raises(EvidenceBundleExportError, match="must include"):
        export_operator_evidence_bundle(output_root=tmp_path / "unsafe", export_id="review", certificate=cert, view=view, checklist=checklist)


def test_unsafe_export_id_is_blocked(tmp_path):
    cert, view, checklist = ready_evidence()
    with pytest.raises(EvidenceBundleExportError, match="unsafe export_id"):
        export_operator_evidence_bundle(output_root=export_root(tmp_path), export_id="../escape", certificate=cert, view=view, checklist=checklist)


def test_tampered_evidence_file_is_blocked(tmp_path):
    cert, view, checklist = ready_evidence()
    _, bundle = export_operator_evidence_bundle(output_root=export_root(tmp_path), export_id="review", certificate=cert, view=view, checklist=checklist)
    (bundle / "cutover_certificate.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(EvidenceBundleExportError, match="file hash mismatch"):
        verify_operator_evidence_bundle(bundle)


def test_tampered_manifest_is_blocked(tmp_path):
    cert, view, checklist = ready_evidence()
    _, bundle = export_operator_evidence_bundle(output_root=export_root(tmp_path), export_id="review", certificate=cert, view=view, checklist=checklist)
    path = bundle / "evidence_bundle_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["strategy_version"] = "9.9.9"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(EvidenceBundleExportError, match="manifest hash mismatch"):
        verify_operator_evidence_bundle(bundle)


def test_missing_exported_file_is_blocked(tmp_path):
    cert, view, checklist = ready_evidence()
    _, bundle = export_operator_evidence_bundle(output_root=export_root(tmp_path), export_id="review", certificate=cert, view=view, checklist=checklist)
    (bundle / "operator_cutover_checklist.json").unlink()
    with pytest.raises(EvidenceBundleExportError, match="missing"):
        verify_operator_evidence_bundle(bundle)


def test_identity_mismatch_is_blocked(tmp_path):
    cert, view, checklist = ready_evidence()
    mismatched = replace(checklist, certificate_hash="wrong", status=checklist.status, blockers=())
    with pytest.raises(EvidenceBundleExportError, match="certificate hash mismatch"):
        export_operator_evidence_bundle(output_root=export_root(tmp_path), export_id="review", certificate=cert, view=view, checklist=mismatched)


def test_manifest_has_zero_authority(tmp_path):
    cert, view, checklist = ready_evidence()
    manifest, _ = export_operator_evidence_bundle(output_root=export_root(tmp_path), export_id="review", certificate=cert, view=view, checklist=checklist)
    payload = manifest.to_dict()
    for key in (
        "canonical_files_copied", "canonical_files_written", "activation_authorized",
        "strategy_switch_authorized", "runtime_cutover_authorized",
        "broker_execution_authorized", "real_money_authorized",
    ):
        assert payload[key] is False


def test_existing_collision_is_blocked(tmp_path):
    cert, view, checklist = ready_evidence()
    root = export_root(tmp_path)
    _, bundle = export_operator_evidence_bundle(output_root=root, export_id="review", certificate=cert, view=view, checklist=checklist)
    (bundle / "cutover_certificate.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(EvidenceBundleExportError):
        export_operator_evidence_bundle(output_root=root, export_id="review", certificate=cert, view=view, checklist=checklist)
