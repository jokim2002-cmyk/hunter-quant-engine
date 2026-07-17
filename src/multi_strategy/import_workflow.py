"""Reviewed, evidence-first strategy package import workflow for HQE Phase 6.

The workflow composes the existing offline quarantine, tamper-evident approval
and atomic metadata-only installation primitives.  It never imports strategy
source code, registers an implementation, changes the paper selection, creates
a canonical cutover gate, controls a runtime, writes lifecycle evidence or
enables execution.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.multi_strategy.approval import (
    PackageApprovalError,
    approve_review_request,
    build_review_request,
    canonical_json,
    sha256_hex,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.installation import (
    CatalogInstallError,
    install_approved_metadata,
    read_installed_catalog,
)
from src.multi_strategy.quarantine import (
    ImportPreviewStatus,
    OfflineStrategyPackageQuarantine,
)
from src.multi_strategy.registry import RegistrationStatus

IMPORT_WORKFLOW_SCHEMA_VERSION = "1.0.0"
IMPORT_ROOT = Path("HQE_MULTI_STRATEGY_IMPORT")
LATEST_POINTER = IMPORT_ROOT / "latest_workflow.json"
WORKFLOW_FILE = "workflow.json"
PACKAGE_METADATA_FILE = "package_metadata.json"
QUARANTINE_RECORD_FILE = "quarantine_record.json"
REVIEW_REQUEST_FILE = "review_request.json"
APPROVAL_FILE = "approval.json"
INSTALL_RESULT_FILE = "install_result.json"
AUDIT_FILE = "audit.jsonl"
APPROVAL_PHRASE = "APPROVE REVIEWED METADATA IMPORT"

SAFETY = {
    "paper_only": True,
    "source_code_import_allowed": False,
    "package_payload_install_allowed": False,
    "metadata_catalog_install_only": True,
    "registration_allowed": False,
    "selection_allowed": False,
    "canonical_activation_allowed": False,
    "human_cutover_gate_creation_allowed": False,
    "runtime_control_allowed": False,
    "lifecycle_write_allowed": False,
    "state_write_allowed": False,
    "ledger_write_allowed": False,
    "real_orders_allowed": False,
    "broker_execution_allowed": False,
    "auto_trading_allowed": False,
    "real_money_allowed": False,
    "option_selling_allowed": False,
}


class ReviewedImportWorkflowError(RuntimeError):
    """Raised when a Phase 6 reviewed import step is unsafe or invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _text(value: Any) -> str:
    return str(value or "").strip()


def _mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ReviewedImportWorkflowError("Expected a JSON mapping.")
    copied = deepcopy(dict(value))
    try:
        canonical_json(copied)
    except (TypeError, ValueError) as exc:
        raise ReviewedImportWorkflowError("Payload must be JSON serializable.") from exc
    return copied


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        serialized = json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n"
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewedImportWorkflowError(f"Evidence could not be read: {path}") from exc
    return _mapping(payload)


def _record_hash(payload: Mapping[str, Any]) -> str:
    material = {key: deepcopy(value) for key, value in payload.items() if key != "workflow_hash"}
    return sha256_hex(material)


def _verify_workflow(payload: Mapping[str, Any]) -> dict[str, Any]:
    record = _mapping(payload)
    if record.get("schema_version") != IMPORT_WORKFLOW_SCHEMA_VERSION:
        raise ReviewedImportWorkflowError("Unsupported import workflow schema.")
    if record.get("workflow_type") != "HQE_REVIEWED_STRATEGY_IMPORT":
        raise ReviewedImportWorkflowError("Unexpected import workflow type.")
    if record.get("safety") != SAFETY:
        raise ReviewedImportWorkflowError("Import workflow safety boundary changed.")
    if record.get("workflow_hash") != _record_hash(record):
        raise ReviewedImportWorkflowError("Import workflow hash verification failed.")
    return record


def _write_workflow(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    record = _mapping(payload)
    record["workflow_hash"] = _record_hash(record)
    _atomic_json(path, record)
    return _verify_workflow(_read_json(path))


def _append_audit(directory: Path, event: str, details: Mapping[str, Any]) -> None:
    path = directory / AUDIT_FILE
    payload = {
        "event": event,
        "at_utc": _utc_now(),
        "details": _mapping(details),
        "safety": SAFETY,
    }
    line = json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def _reviewed_implementation_keys() -> tuple[str, ...]:
    registry = build_phase3_registry()
    return tuple(
        sorted(
            registration.manifest.implementation_key
            for registration in registry.list_registrations()
            if registration.status is RegistrationStatus.EXECUTABLE_REVIEWED
        )
    )


def _workflow_directory(workspace: Path, strategy_id: str, version: str, package_hash: str) -> Path:
    return (
        workspace
        / IMPORT_ROOT
        / "workflows"
        / strategy_id
        / version
        / package_hash
    )


def _write_latest_pointer(workspace: Path, workflow_path: Path) -> None:
    payload = {
        "schema_version": IMPORT_WORKFLOW_SCHEMA_VERSION,
        "workflow_path": str(workflow_path),
        "workflow_path_hash": sha256_hex(str(workflow_path)),
    }
    _atomic_json(workspace / LATEST_POINTER, payload)


def _load_latest_path(workspace: Path) -> Path | None:
    pointer = workspace / LATEST_POINTER
    if not pointer.exists():
        return None
    payload = _read_json(pointer)
    path_text = _text(payload.get("workflow_path"))
    if not path_text or payload.get("workflow_path_hash") != sha256_hex(path_text):
        raise ReviewedImportWorkflowError("Latest workflow pointer verification failed.")
    path = Path(path_text)
    expected_root = (workspace / IMPORT_ROOT / "workflows").resolve()
    resolved = path.resolve()
    if expected_root != resolved and expected_root not in resolved.parents:
        raise ReviewedImportWorkflowError("Latest workflow pointer escaped the workspace.")
    return resolved


def _load_workflow(workspace: Path, workflow_path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    path = Path(workflow_path) if workflow_path else _load_latest_path(workspace)
    if path is None:
        raise ReviewedImportWorkflowError("No reviewed import workflow exists.")
    if path.is_dir():
        path = path / WORKFLOW_FILE
    return path, _verify_workflow(_read_json(path))


def _package_metadata(quarantined: Any) -> dict[str, Any]:
    manifest = quarantined.manifest
    return {
        "strategy_id": manifest.strategy_id,
        "version": manifest.strategy_version,
        "display_name": manifest.display_name,
        "implementation_key": manifest.implementation_key,
        "package_hash": quarantined.package_fingerprint,
        "manifest_hash": manifest.fingerprint(),
        "description": manifest.description,
        "paper_only": manifest.paper_only,
        "quarantined_package_directory": str(quarantined.quarantined_package_directory),
    }


def _quarantine_record(quarantined: Any) -> dict[str, Any]:
    return {
        "status": "QUARANTINED",
        "strategy_id": quarantined.manifest.strategy_id,
        "version": quarantined.manifest.strategy_version,
        "package_hash": quarantined.package_fingerprint,
        "manifest_hash": quarantined.manifest.fingerprint(),
        "quarantine_record_directory": str(quarantined.quarantine_record_directory),
        "quarantined_package_directory": str(quarantined.quarantined_package_directory),
        "preview": quarantined.preview.to_dict(),
        "result_hash": quarantined.result_hash,
        "source_modified": False,
        "source_code_imported": False,
        "registry_mutated": False,
        "selected": False,
        "activated": False,
        "runtime_connected": False,
    }


def begin_reviewed_import(
    source_root: Path | str,
    workspace: Path | str,
    *,
    requested_by: str,
    requested_at_utc: str | None = None,
) -> dict[str, Any]:
    """Validate, quarantine and create a non-authorizing review request."""

    root = Path(workspace).resolve()
    source = Path(source_root).resolve()
    actor = requested_by.strip()
    if not actor:
        raise ReviewedImportWorkflowError("requested_by is required.")

    registry = build_phase3_registry()
    service = OfflineStrategyPackageQuarantine(registry)
    quarantined = service.quarantine(
        source_root=source,
        quarantine_root=root / IMPORT_ROOT / "quarantine",
    )
    metadata = _package_metadata(quarantined)
    quarantine = _quarantine_record(quarantined)
    request = build_review_request(
        metadata,
        quarantine,
        requested_by=actor,
        requested_at_utc=(requested_at_utc or _utc_now()),
    )

    preview = quarantined.preview
    blockers = list(preview.blockers)
    if preview.preview_status is ImportPreviewStatus.DUPLICATE_EXISTING:
        blockers.append("The strategy ID/version already exists in the reviewed registry.")
    if preview.registration_conflict:
        blockers.append("The strategy ID/version conflicts with reviewed registry metadata.")
    if not preview.reviewed_implementation_available:
        blockers.append("The implementation key has not been reviewed locally.")
    blockers = list(dict.fromkeys(_text(item) for item in blockers if _text(item)))

    state = "PENDING_REVIEW" if not blockers else "REVIEW_BLOCKED"
    directory = _workflow_directory(
        root,
        metadata["strategy_id"],
        metadata["version"],
        metadata["package_hash"],
    )
    directory.mkdir(parents=True, exist_ok=True)

    _atomic_json(directory / PACKAGE_METADATA_FILE, metadata)
    _atomic_json(directory / QUARANTINE_RECORD_FILE, quarantine)
    _atomic_json(directory / REVIEW_REQUEST_FILE, request)

    workflow = {
        "schema_version": IMPORT_WORKFLOW_SCHEMA_VERSION,
        "workflow_type": "HQE_REVIEWED_STRATEGY_IMPORT",
        "state": state,
        "strategy_id": metadata["strategy_id"],
        "version": metadata["version"],
        "display_name": metadata["display_name"],
        "implementation_key": metadata["implementation_key"],
        "package_hash": metadata["package_hash"],
        "manifest_hash": metadata["manifest_hash"],
        "source_root": str(source),
        "workflow_directory": str(directory),
        "quarantine_directory": quarantine["quarantined_package_directory"],
        "package_metadata_path": str(directory / PACKAGE_METADATA_FILE),
        "quarantine_record_path": str(directory / QUARANTINE_RECORD_FILE),
        "review_request_path": str(directory / REVIEW_REQUEST_FILE),
        "approval_path": "",
        "install_result_path": "",
        "preview_status": preview.preview_status.value,
        "reviewed_implementation_available": preview.reviewed_implementation_available,
        "blockers": blockers,
        "approval_phrase_required": APPROVAL_PHRASE,
        "created_at_utc": requested_at_utc or _utc_now(),
        "updated_at_utc": requested_at_utc or _utc_now(),
        "safety": SAFETY,
    }
    written = _write_workflow(directory / WORKFLOW_FILE, workflow)
    _write_latest_pointer(root, directory / WORKFLOW_FILE)
    _append_audit(directory, "QUARANTINED_AND_REVIEW_REQUESTED", {
        "state": state,
        "request_hash": request["request_hash"],
        "blockers": blockers,
    })
    return workflow_snapshot(root, directory / WORKFLOW_FILE)


def approve_reviewed_import(
    workspace: Path | str,
    *,
    approval_phrase: str,
    approved_by: str,
    decided_at_utc: str | None = None,
    review_note: str = "",
    workflow_path: Path | None = None,
) -> dict[str, Any]:
    """Explicitly approve a reviewed reference; never authorize activation."""

    root = Path(workspace).resolve()
    path, workflow = _load_workflow(root, workflow_path)
    directory = path.parent

    if approval_phrase.strip() != APPROVAL_PHRASE:
        raise ReviewedImportWorkflowError("Exact reviewed-import approval phrase is required.")
    if workflow["state"] != "PENDING_REVIEW":
        raise ReviewedImportWorkflowError("Workflow is not pending review.")
    if workflow.get("blockers"):
        raise ReviewedImportWorkflowError("Blocked workflow cannot be approved.")
    if not workflow.get("reviewed_implementation_available"):
        raise ReviewedImportWorkflowError("Implementation key is not reviewed.")
    if workflow.get("preview_status") != ImportPreviewStatus.PREVIEW_REVIEWED_REFERENCE.value:
        raise ReviewedImportWorkflowError("Only a reviewed-reference preview can be approved.")

    metadata = _read_json(Path(workflow["package_metadata_path"]))
    quarantine = _read_json(Path(workflow["quarantine_record_path"]))
    request = _read_json(Path(workflow["review_request_path"]))
    if metadata["package_hash"] != workflow["package_hash"]:
        raise ReviewedImportWorkflowError("Workflow/package metadata hash mismatch.")
    if quarantine["package_hash"] != workflow["package_hash"]:
        raise ReviewedImportWorkflowError("Workflow/quarantine package hash mismatch.")

    approval = approve_review_request(
        request,
        approved_by=approved_by,
        decided_at_utc=(decided_at_utc or _utc_now()),
        review_note=review_note,
    )
    approval_path = directory / APPROVAL_FILE
    _atomic_json(approval_path, approval)

    workflow["state"] = "APPROVED_METADATA_ONLY"
    workflow["approval_path"] = str(approval_path)
    workflow["approval_hash"] = approval["approval_hash"]
    workflow["updated_at_utc"] = decided_at_utc or _utc_now()
    _write_workflow(path, workflow)
    _append_audit(directory, "EXPLICITLY_APPROVED_METADATA_ONLY", {
        "approval_hash": approval["approval_hash"],
        "approved_by": approved_by,
    })
    return workflow_snapshot(root, path)


def install_reviewed_metadata(
    workspace: Path | str,
    *,
    installed_at_utc: str | None = None,
    workflow_path: Path | None = None,
) -> dict[str, Any]:
    """Atomically install approved metadata without importing package code."""

    root = Path(workspace).resolve()
    path, workflow = _load_workflow(root, workflow_path)
    directory = path.parent
    if workflow["state"] not in {"APPROVED_METADATA_ONLY", "INSTALLED_METADATA_ONLY"}:
        raise ReviewedImportWorkflowError("Workflow has not been explicitly approved.")

    metadata = _read_json(Path(workflow["package_metadata_path"]))
    approval_path = Path(_text(workflow.get("approval_path")))
    if not approval_path.is_file():
        raise ReviewedImportWorkflowError("Approval evidence is missing.")
    approval = _read_json(approval_path)

    try:
        result = install_approved_metadata(
            root,
            metadata,
            approval,
            allowed_implementation_keys=_reviewed_implementation_keys(),
            installed_at_utc=(installed_at_utc or _utc_now()),
        )
    except CatalogInstallError as exc:
        raise ReviewedImportWorkflowError(str(exc)) from exc

    result = _mapping(result)
    result.update({
        "source_code_imported": False,
        "package_payload_installed": False,
        "registered": False,
        "selected": False,
        "activated": False,
        "runtime_connected": False,
        "human_cutover_gate_created": False,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "real_money_allowed": False,
    })
    result_path = directory / INSTALL_RESULT_FILE
    _atomic_json(result_path, result)

    workflow["state"] = "INSTALLED_METADATA_ONLY"
    workflow["install_result_path"] = str(result_path)
    workflow["catalog_path"] = result["catalog_path"]
    workflow["catalog_hash"] = result["catalog_hash_after"]
    workflow["updated_at_utc"] = installed_at_utc or _utc_now()
    _write_workflow(path, workflow)
    _append_audit(directory, "ATOMIC_METADATA_INSTALL", {
        "status": result["status"],
        "changed": result["changed"],
        "catalog_hash": result["catalog_hash_after"],
    })
    return workflow_snapshot(root, path)


def workflow_snapshot(
    workspace: Path | str,
    workflow_path: Path | None = None,
) -> dict[str, Any]:
    """Return verified operator evidence for the latest workflow."""

    root = Path(workspace).resolve()
    try:
        path, workflow = _load_workflow(root, workflow_path)
    except ReviewedImportWorkflowError as exc:
        if "No reviewed import workflow exists" not in str(exc):
            raise
        catalog = read_installed_catalog(root)
        return {
            "schema_version": IMPORT_WORKFLOW_SCHEMA_VERSION,
            "exists": False,
            "state": "NO_WORKFLOW",
            "display_text": "Reviewed import: no package selected",
            "workflow_path": "",
            "blockers": [],
            "controls": {
                "choose_and_quarantine_enabled": True,
                "approve_enabled": False,
                "install_metadata_enabled": False,
                "view_evidence_enabled": False,
            },
            "installed_metadata_count": len(catalog["entries"]),
            "installed_catalog_hash": catalog["catalog_hash"],
            **SAFETY,
        }

    state = workflow["state"]
    blockers = list(workflow.get("blockers", []))
    catalog = read_installed_catalog(root)
    return {
        **workflow,
        "exists": True,
        "workflow_path": str(path),
        "display_text": (
            f"Reviewed import: {workflow['display_name']} "
            f"{workflow['version']} | {state}"
        ),
        "controls": {
            "choose_and_quarantine_enabled": True,
            "approve_enabled": state == "PENDING_REVIEW" and not blockers,
            "install_metadata_enabled": state == "APPROVED_METADATA_ONLY",
            "view_evidence_enabled": True,
            "select_enabled": False,
            "activate_enabled": False,
            "runtime_control_enabled": False,
        },
        "installed_metadata_count": len(catalog["entries"]),
        "installed_catalog_hash": catalog["catalog_hash"],
        **SAFETY,
    }


def guard_payload() -> dict[str, Any]:
    return {
        "schema_version": IMPORT_WORKFLOW_SCHEMA_VERSION,
        "guard_check_status": "PASS",
        "workflow": "REVIEWED_PACKAGE_IMPORT_METADATA_ONLY",
        "stable_quarantine_copy": True,
        "tamper_evident_review_request": True,
        "exact_approval_phrase_required": True,
        "reviewed_implementation_allowlist_required": True,
        "atomic_metadata_catalog_install": True,
        "duplicate_identical_install_idempotent": True,
        "id_version_collision_blocked": True,
        "audit_evidence_written": True,
        **SAFETY,
    }
