"""Atomic isolated export model for read-only HQE cutover evidence bundles."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from src.multi_strategy.cutover_certificate import (
    CutoverCertificateError,
    DisabledCutoverReadinessCertificate,
)
from src.multi_strategy.cutover_certificate_view import (
    DisabledCutoverCertificateView,
)
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.operator_cutover_checklist import (
    OperatorChecklistStatus,
    ReadOnlyOperatorCutoverChecklist,
)

EVIDENCE_EXPORT_SCHEMA_VERSION = "1.0.0"
EVIDENCE_EXPORT_MODE = "READ_ONLY_OPERATOR_EVIDENCE_BUNDLE_EXPORT"
REQUIRED_EXPORT_NAMESPACE = "HQE_MULTI_STRATEGY_PHASE4N_REVIEW_EXPORT"


class EvidenceBundleExportError(ValueError):
    """Raised for unsafe, incomplete, or tampered review exports."""


class EvidenceBundleExportStatus(str, Enum):
    EXPORTED_REVIEW_ONLY = "EXPORTED_REVIEW_ONLY"
    ALREADY_EXPORTED = "ALREADY_EXPORTED"


@dataclass(frozen=True)
class EvidenceBundleExportManifest:
    status: EvidenceBundleExportStatus
    export_id: str
    strategy_id: str
    strategy_version: str
    certificate_hash: str
    certificate_view_hash: str
    checklist_hash: str
    file_hashes: Mapping[str, str]
    schema_version: str = EVIDENCE_EXPORT_SCHEMA_VERSION
    mode: str = EVIDENCE_EXPORT_MODE
    read_only_review_bundle: bool = True
    canonical_files_copied: bool = False
    canonical_files_written: bool = False
    activation_authorized: bool = False
    strategy_switch_authorized: bool = False
    runtime_cutover_authorized: bool = False
    broker_execution_authorized: bool = False
    real_money_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != EVIDENCE_EXPORT_SCHEMA_VERSION:
            raise EvidenceBundleExportError("unsupported evidence export schema")
        if self.mode != EVIDENCE_EXPORT_MODE:
            raise EvidenceBundleExportError("invalid evidence export mode")
        if not self.read_only_review_bundle:
            raise EvidenceBundleExportError("evidence export must remain read-only")
        if any(
            (
                self.canonical_files_copied,
                self.canonical_files_written,
                self.activation_authorized,
                self.strategy_switch_authorized,
                self.runtime_cutover_authorized,
                self.broker_execution_authorized,
                self.real_money_authorized,
            )
        ):
            raise EvidenceBundleExportError("evidence export cannot grant authority")
        if not self.export_id or not self.strategy_id or not self.strategy_version:
            raise EvidenceBundleExportError("evidence export identity is required")
        if not self.certificate_hash or not self.certificate_view_hash:
            raise EvidenceBundleExportError("certificate hashes are required")
        if not self.checklist_hash or not self.file_hashes:
            raise EvidenceBundleExportError("checklist and file hashes are required")
        object.__setattr__(
            self,
            "file_hashes",
            MappingProxyType(dict(sorted(self.file_hashes.items()))),
        )

    @property
    def manifest_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "status": self.status.value,
            "export_id": self.export_id,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "certificate_hash": self.certificate_hash,
            "certificate_view_hash": self.certificate_view_hash,
            "checklist_hash": self.checklist_hash,
            "file_hashes": dict(self.file_hashes),
            "read_only_review_bundle": True,
            "canonical_files_copied": False,
            "canonical_files_written": False,
            "activation_authorized": False,
            "strategy_switch_authorized": False,
            "runtime_cutover_authorized": False,
            "broker_execution_authorized": False,
            "real_money_authorized": False,
        }
        if include_hash:
            payload["manifest_hash"] = self.manifest_hash
        return payload


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, indent=2, separators=(",", ": "))
        + "\n"
    ).encode("utf-8")


def _bytes_hash(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _assert_safe_export_root(path: Path) -> None:
    if REQUIRED_EXPORT_NAMESPACE not in path.parts:
        raise EvidenceBundleExportError(
            f"export path must include {REQUIRED_EXPORT_NAMESPACE}"
        )


def _build_payloads(
    certificate: DisabledCutoverReadinessCertificate,
    view: DisabledCutoverCertificateView,
    checklist: ReadOnlyOperatorCutoverChecklist,
) -> dict[str, bytes]:
    return {
        "cutover_certificate.json": _json_bytes(certificate.to_dict()),
        "cutover_certificate_view.json": _json_bytes(view.to_dict()),
        "operator_cutover_checklist.json": _json_bytes(checklist.to_dict()),
    }


def export_operator_evidence_bundle(
    *,
    output_root: Path,
    export_id: str,
    certificate: DisabledCutoverReadinessCertificate,
    view: DisabledCutoverCertificateView,
    checklist: ReadOnlyOperatorCutoverChecklist,
) -> tuple[EvidenceBundleExportManifest, Path]:
    """Atomically export a metadata-only review bundle into an isolated path."""

    output_root = output_root.resolve(strict=False)
    _assert_safe_export_root(output_root)
    if not export_id or any(ch in export_id for ch in ("/", "\\", "..")):
        raise EvidenceBundleExportError("unsafe export_id")
    if checklist.status is not OperatorChecklistStatus.READY_REVIEW_EXPORT_DISABLED:
        raise EvidenceBundleExportError("blocked checklist cannot be exported")
    if not checklist.human_review_ready:
        raise EvidenceBundleExportError("checklist is not human-review ready")
    if checklist.certificate_hash != certificate.certificate_hash:
        raise EvidenceBundleExportError("checklist certificate hash mismatch")
    if checklist.certificate_view_hash != view.view_hash:
        raise EvidenceBundleExportError("checklist certificate view hash mismatch")
    if certificate.strategy_id != view.strategy_id or certificate.strategy_id != checklist.strategy_id:
        raise EvidenceBundleExportError("strategy_id mismatch across export evidence")
    if certificate.strategy_version != view.strategy_version or certificate.strategy_version != checklist.strategy_version:
        raise EvidenceBundleExportError("strategy_version mismatch across export evidence")

    payloads = _build_payloads(certificate, view, checklist)
    file_hashes = {name: _bytes_hash(data) for name, data in payloads.items()}
    manifest = EvidenceBundleExportManifest(
        status=EvidenceBundleExportStatus.EXPORTED_REVIEW_ONLY,
        export_id=export_id,
        strategy_id=certificate.strategy_id,
        strategy_version=certificate.strategy_version,
        certificate_hash=certificate.certificate_hash,
        certificate_view_hash=view.view_hash,
        checklist_hash=checklist.checklist_hash,
        file_hashes=file_hashes,
    )
    manifest_bytes = _json_bytes(manifest.to_dict())
    final_dir = output_root / export_id

    if final_dir.exists():
        verified = verify_operator_evidence_bundle(final_dir)
        if (
            verified.certificate_hash == manifest.certificate_hash
            and verified.certificate_view_hash == manifest.certificate_view_hash
            and verified.checklist_hash == manifest.checklist_hash
        ):
            return (
                EvidenceBundleExportManifest(
                    status=EvidenceBundleExportStatus.ALREADY_EXPORTED,
                    export_id=manifest.export_id,
                    strategy_id=manifest.strategy_id,
                    strategy_version=manifest.strategy_version,
                    certificate_hash=manifest.certificate_hash,
                    certificate_view_hash=manifest.certificate_view_hash,
                    checklist_hash=manifest.checklist_hash,
                    file_hashes=manifest.file_hashes,
                ),
                final_dir,
            )
        raise EvidenceBundleExportError("existing export collides with requested evidence")

    output_root.mkdir(parents=True, exist_ok=True)
    temp_dir = output_root / f".{export_id}.tmp-{uuid.uuid4().hex}"
    try:
        temp_dir.mkdir(parents=False, exist_ok=False)
        for name, data in payloads.items():
            (temp_dir / name).write_bytes(data)
        (temp_dir / "evidence_bundle_manifest.json").write_bytes(manifest_bytes)
        os.replace(temp_dir, final_dir)
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    verified = verify_operator_evidence_bundle(final_dir)
    if verified.manifest_hash != manifest.manifest_hash:
        raise EvidenceBundleExportError("post-export manifest verification failed")
    return manifest, final_dir


def verify_operator_evidence_bundle(bundle_dir: Path) -> EvidenceBundleExportManifest:
    """Verify the manifest and every exported review file hash."""

    bundle_dir = bundle_dir.resolve(strict=False)
    _assert_safe_export_root(bundle_dir)
    manifest_path = bundle_dir / "evidence_bundle_manifest.json"
    if not manifest_path.is_file():
        raise EvidenceBundleExportError("evidence bundle manifest is missing")
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceBundleExportError("evidence bundle manifest is invalid") from exc

    manifest_hash = raw.pop("manifest_hash", None)
    if not manifest_hash:
        raise EvidenceBundleExportError("manifest hash is missing")
    if canonical_mapping_hash(raw) != manifest_hash:
        raise EvidenceBundleExportError("manifest hash mismatch")

    try:
        manifest = EvidenceBundleExportManifest(
            status=EvidenceBundleExportStatus(raw["status"]),
            export_id=raw["export_id"],
            strategy_id=raw["strategy_id"],
            strategy_version=raw["strategy_version"],
            certificate_hash=raw["certificate_hash"],
            certificate_view_hash=raw["certificate_view_hash"],
            checklist_hash=raw["checklist_hash"],
            file_hashes=raw["file_hashes"],
            schema_version=raw["schema_version"],
            mode=raw["mode"],
            read_only_review_bundle=raw["read_only_review_bundle"],
            canonical_files_copied=raw["canonical_files_copied"],
            canonical_files_written=raw["canonical_files_written"],
            activation_authorized=raw["activation_authorized"],
            strategy_switch_authorized=raw["strategy_switch_authorized"],
            runtime_cutover_authorized=raw["runtime_cutover_authorized"],
            broker_execution_authorized=raw["broker_execution_authorized"],
            real_money_authorized=raw["real_money_authorized"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceBundleExportError("manifest fields are invalid") from exc

    if manifest.manifest_hash != manifest_hash:
        raise EvidenceBundleExportError("reconstructed manifest hash mismatch")
    for name, expected_hash in manifest.file_hashes.items():
        path = bundle_dir / name
        if not path.is_file():
            raise EvidenceBundleExportError(f"exported evidence file missing: {name}")
        if _bytes_hash(path.read_bytes()) != expected_hash:
            raise EvidenceBundleExportError(f"exported evidence file hash mismatch: {name}")
    return manifest
