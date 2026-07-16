"""Offline data-only strategy package quarantine and import preview.

Phase 4H copies only already-validated data-only packages into an isolated
quarantine workspace. It never mutates the execution registry, authorizes
activation, connects the canonical runtime, or exposes broker/order controls.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.multi_strategy.errors import (
    ImportPreviewError,
    PackageQuarantineError,
)
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.manifest import StrategyManifest
from src.multi_strategy.package import (
    StrategyPackage,
    validate_strategy_package,
)
from src.multi_strategy.registry import (
    RegistrationStatus,
    StrategyRegistry,
)

QUARANTINE_SCHEMA_VERSION = "1.0.0"
IMPORT_PREVIEW_SCHEMA_VERSION = "1.0.0"
QUARANTINE_PACKAGE_DIRECTORY = "package"


class ImportPreviewStatus(str, Enum):
    """Read-only package preview classification."""

    PREVIEW_METADATA_ONLY = "PREVIEW_METADATA_ONLY"
    PREVIEW_REVIEWED_REFERENCE = "PREVIEW_REVIEWED_REFERENCE"
    DUPLICATE_EXISTING = "DUPLICATE_EXISTING"
    BLOCKED_ID_VERSION_CONFLICT = "BLOCKED_ID_VERSION_CONFLICT"


@dataclass(frozen=True)
class PackageFileEvidence:
    """One stable source-package file observation."""

    relative_path: str
    size_bytes: int
    modified_time_ns: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "modified_time_ns": self.modified_time_ns,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class StrategyPackageImportPreview:
    """Immutable, non-authorizing preview of one quarantined package."""

    strategy_id: str
    strategy_version: str
    display_name: str
    implementation_key: str
    manifest_fingerprint: str
    package_fingerprint: str
    preview_status: ImportPreviewStatus
    reviewed_implementation_available: bool
    registration_conflict: bool
    blockers: tuple[str, ...]
    schema_version: str = IMPORT_PREVIEW_SCHEMA_VERSION
    import_authorized: bool = False
    registry_mutation_authorized: bool = False
    activation_authorized: bool = False
    runtime_connection_authorized: bool = False
    runtime_cutover_authorized: bool = False
    state_write_authorized: bool = False
    ledger_write_authorized: bool = False
    broker_execution_authorized: bool = False
    real_money_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != IMPORT_PREVIEW_SCHEMA_VERSION:
            raise ImportPreviewError("unsupported import preview schema")
        if not self.strategy_id or not self.strategy_version:
            raise ImportPreviewError("strategy identity is required")
        if any(
            (
                self.import_authorized,
                self.registry_mutation_authorized,
                self.activation_authorized,
                self.runtime_connection_authorized,
                self.runtime_cutover_authorized,
                self.state_write_authorized,
                self.ledger_write_authorized,
                self.broker_execution_authorized,
                self.real_money_authorized,
            )
        ):
            raise ImportPreviewError(
                "Phase 4H import preview cannot authorize execution"
            )
        object.__setattr__(self, "blockers", tuple(self.blockers))

    @property
    def preview_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "display_name": self.display_name,
            "implementation_key": self.implementation_key,
            "manifest_fingerprint": self.manifest_fingerprint,
            "package_fingerprint": self.package_fingerprint,
            "preview_status": self.preview_status.value,
            "reviewed_implementation_available": (
                self.reviewed_implementation_available
            ),
            "registration_conflict": self.registration_conflict,
            "blockers": list(self.blockers),
            "import_authorized": False,
            "registry_mutation_authorized": False,
            "activation_authorized": False,
            "runtime_connection_authorized": False,
            "runtime_cutover_authorized": False,
            "state_write_authorized": False,
            "ledger_write_authorized": False,
            "broker_execution_authorized": False,
            "real_money_authorized": False,
        }
        if include_hash:
            payload["preview_hash"] = self.preview_hash
        return payload


@dataclass(frozen=True)
class QuarantinedStrategyPackage:
    """Result of one isolated package quarantine copy."""

    source_root: Path
    quarantine_record_directory: Path
    quarantined_package_directory: Path
    manifest: StrategyManifest
    package_fingerprint: str
    source_evidence: tuple[PackageFileEvidence, ...]
    preview: StrategyPackageImportPreview
    reused_existing: bool
    schema_version: str = QUARANTINE_SCHEMA_VERSION
    source_modified: bool = False
    import_performed: bool = False
    registry_mutated: bool = False
    activation_authorized: bool = False
    runtime_connected: bool = False
    runtime_cutover_performed: bool = False
    state_written: bool = False
    ledger_written: bool = False
    broker_execution_performed: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != QUARANTINE_SCHEMA_VERSION:
            raise PackageQuarantineError("unsupported quarantine schema")
        if self.source_modified:
            raise PackageQuarantineError("source package changed during copy")
        if any(
            (
                self.import_performed,
                self.registry_mutated,
                self.activation_authorized,
                self.runtime_connected,
                self.runtime_cutover_performed,
                self.state_written,
                self.ledger_written,
                self.broker_execution_performed,
            )
        ):
            raise PackageQuarantineError(
                "quarantine result cannot authorize or perform execution"
            )
        object.__setattr__(
            self,
            "source_evidence",
            tuple(self.source_evidence),
        )

    @property
    def result_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "source_root": str(self.source_root),
            "quarantine_record_directory": str(
                self.quarantine_record_directory
            ),
            "quarantined_package_directory": str(
                self.quarantined_package_directory
            ),
            "strategy_id": self.manifest.strategy_id,
            "strategy_version": self.manifest.strategy_version,
            "manifest_fingerprint": self.manifest.fingerprint(),
            "package_fingerprint": self.package_fingerprint,
            "source_evidence": [
                item.to_dict()
                for item in self.source_evidence
            ],
            "preview": self.preview.to_dict(),
            "reused_existing": self.reused_existing,
            "source_modified": False,
            "import_performed": False,
            "registry_mutated": False,
            "activation_authorized": False,
            "runtime_connected": False,
            "runtime_cutover_performed": False,
            "state_written": False,
            "ledger_written": False,
            "broker_execution_performed": False,
        }
        if include_hash:
            payload["result_hash"] = self.result_hash
        return payload


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture_package_evidence(
    package_root: Path,
) -> tuple[PackageFileEvidence, ...]:
    package_root = Path(package_root)
    if not package_root.is_dir():
        raise PackageQuarantineError(
            f"package directory does not exist: {package_root}"
        )

    evidence: list[PackageFileEvidence] = []
    for path in sorted(package_root.rglob("*")):
        relative = path.relative_to(package_root).as_posix()
        if path.is_symlink():
            raise PackageQuarantineError(
                f"symlink is not allowed: {relative}"
            )
        if not path.is_file():
            continue
        stat = path.stat()
        evidence.append(
            PackageFileEvidence(
                relative_path=relative,
                size_bytes=stat.st_size,
                modified_time_ns=stat.st_mtime_ns,
                sha256=_sha256(path),
            )
        )
    return tuple(evidence)


def _copy_package_bytes(
    *,
    source_root: Path,
    target_root: Path,
    evidence: Sequence[PackageFileEvidence],
) -> None:
    for item in evidence:
        source = source_root / Path(item.relative_path)
        target = target_root / Path(item.relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        if _sha256(target) != item.sha256:
            raise PackageQuarantineError(
                f"quarantine copy hash mismatch: {item.relative_path}"
            )


def build_import_preview(
    strategy_package: StrategyPackage,
    registry: StrategyRegistry,
) -> StrategyPackageImportPreview:
    """Classify a package without registering or executing it."""

    manifest = strategy_package.manifest
    registrations = registry.list_registrations()
    reviewed_keys = {
        registration.manifest.implementation_key
        for registration in registrations
        if registration.status is RegistrationStatus.EXECUTABLE_REVIEWED
    }
    reviewed_available = manifest.implementation_key in reviewed_keys

    existing = next(
        (
            registration
            for registration in registrations
            if registration.registration_key == manifest.registration_key
        ),
        None,
    )

    blockers: list[str] = []
    conflict = False
    if existing is not None:
        if existing.manifest.fingerprint() == manifest.fingerprint():
            status = ImportPreviewStatus.DUPLICATE_EXISTING
            blockers.append(
                "strategy ID/version already exists with identical manifest"
            )
        else:
            status = ImportPreviewStatus.BLOCKED_ID_VERSION_CONFLICT
            conflict = True
            blockers.append(
                "strategy ID/version conflicts with an existing manifest"
            )
    elif reviewed_available:
        status = ImportPreviewStatus.PREVIEW_REVIEWED_REFERENCE
    else:
        status = ImportPreviewStatus.PREVIEW_METADATA_ONLY
        blockers.append(
            "implementation key is not available in the reviewed registry"
        )

    return StrategyPackageImportPreview(
        strategy_id=manifest.strategy_id,
        strategy_version=manifest.strategy_version,
        display_name=manifest.display_name,
        implementation_key=manifest.implementation_key,
        manifest_fingerprint=manifest.fingerprint(),
        package_fingerprint=strategy_package.package_fingerprint,
        preview_status=status,
        reviewed_implementation_available=reviewed_available,
        registration_conflict=conflict,
        blockers=tuple(blockers),
    )


class OfflineStrategyPackageQuarantine:
    """Copy validated packages to isolated quarantine without import."""

    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry

    def quarantine(
        self,
        *,
        source_root: Path,
        quarantine_root: Path,
    ) -> QuarantinedStrategyPackage:
        source = Path(source_root).resolve()
        quarantine = Path(quarantine_root).resolve()

        if source == quarantine:
            raise PackageQuarantineError(
                "source and quarantine roots must be different"
            )
        if quarantine in source.parents or source in quarantine.parents:
            raise PackageQuarantineError(
                "source and quarantine roots must not contain each other"
            )

        before = _capture_package_evidence(source)
        strategy_package = validate_strategy_package(source)
        preview = build_import_preview(strategy_package, self._registry)

        final_record = (
            quarantine
            / "packages"
            / strategy_package.manifest.strategy_id
            / strategy_package.manifest.strategy_version
            / strategy_package.package_fingerprint
        )
        final_package = final_record / QUARANTINE_PACKAGE_DIRECTORY

        if final_record.exists():
            if not final_package.is_dir():
                raise PackageQuarantineError(
                    "existing quarantine record is incomplete"
                )
            existing_package = validate_strategy_package(final_package)
            existing_evidence = _capture_package_evidence(final_package)
            if (
                existing_package.package_fingerprint
                != strategy_package.package_fingerprint
                or tuple(
                    (item.relative_path, item.size_bytes, item.sha256)
                    for item in existing_evidence
                )
                != tuple(
                    (item.relative_path, item.size_bytes, item.sha256)
                    for item in before
                )
            ):
                raise PackageQuarantineError(
                    "existing quarantine record does not match source"
                )
            after = _capture_package_evidence(source)
            if before != after:
                raise PackageQuarantineError(
                    "source package changed during quarantine verification"
                )
            return QuarantinedStrategyPackage(
                source_root=source,
                quarantine_record_directory=final_record,
                quarantined_package_directory=final_package,
                manifest=strategy_package.manifest,
                package_fingerprint=strategy_package.package_fingerprint,
                source_evidence=before,
                preview=preview,
                reused_existing=True,
            )

        quarantine.mkdir(parents=True, exist_ok=True)
        staging = quarantine / f".staging-{uuid.uuid4().hex}"
        staging_package = staging / QUARANTINE_PACKAGE_DIRECTORY

        try:
            staging_package.mkdir(parents=True, exist_ok=False)
            _copy_package_bytes(
                source_root=source,
                target_root=staging_package,
                evidence=before,
            )
            copied = validate_strategy_package(staging_package)
            if copied.package_fingerprint != strategy_package.package_fingerprint:
                raise PackageQuarantineError(
                    "quarantined package fingerprint mismatch"
                )

            after = _capture_package_evidence(source)
            if before != after:
                raise PackageQuarantineError(
                    "source package changed during quarantine copy"
                )

            preview_payload = preview.to_dict()
            quarantine_payload = {
                "schema_version": QUARANTINE_SCHEMA_VERSION,
                "strategy_id": strategy_package.manifest.strategy_id,
                "strategy_version": (
                    strategy_package.manifest.strategy_version
                ),
                "manifest_fingerprint": (
                    strategy_package.manifest.fingerprint()
                ),
                "package_fingerprint": (
                    strategy_package.package_fingerprint
                ),
                "source_evidence": [
                    item.to_dict()
                    for item in before
                ],
                "preview_hash": preview.preview_hash,
                "source_modified": False,
                "import_performed": False,
                "registry_mutated": False,
                "activation_authorized": False,
                "runtime_connected": False,
                "runtime_cutover_performed": False,
                "state_written": False,
                "ledger_written": False,
                "broker_execution_performed": False,
            }
            (staging / "preview.json").write_text(
                json.dumps(preview_payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            (staging / "quarantine.json").write_text(
                json.dumps(quarantine_payload, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )

            final_record.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging, final_record)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

        return QuarantinedStrategyPackage(
            source_root=source,
            quarantine_record_directory=final_record,
            quarantined_package_directory=final_package,
            manifest=strategy_package.manifest,
            package_fingerprint=strategy_package.package_fingerprint,
            source_evidence=before,
            preview=preview,
            reused_existing=False,
        )
