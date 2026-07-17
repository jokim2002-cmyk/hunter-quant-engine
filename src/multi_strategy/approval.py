from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

APPROVAL_SCHEMA_VERSION = "1.0"
REVIEW_REQUEST_TYPE = "HQE_STRATEGY_PACKAGE_REVIEW_REQUEST"
APPROVAL_RECORD_TYPE = "HQE_STRATEGY_PACKAGE_APPROVAL"
QUARANTINE_STATUS = "QUARANTINED"
APPROVED_DECISION = "APPROVED"

_DISABLED_CONTROLS = {
    "activation_enabled": False,
    "broker_execution_enabled": False,
    "import_enabled": False,
    "real_money_enabled": False,
    "registration_enabled": False,
    "runtime_control_enabled": False,
    "selection_enabled": False,
}

_REQUIRED_METADATA_FIELDS = (
    "strategy_id",
    "version",
    "display_name",
    "implementation_key",
    "package_hash",
    "manifest_hash",
)


class PackageApprovalError(ValueError):
    """Raised when a package approval record is invalid or unsafe."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_hex(value: Any) -> str:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = canonical_json(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def package_metadata_hash(package_metadata: Mapping[str, Any]) -> str:
    return sha256_hex(_plain_mapping(package_metadata))


def _plain_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        copied = deepcopy(dict(value))
        canonical_json(copied)
    except (TypeError, ValueError) as exc:
        raise PackageApprovalError(
            "Package metadata must be JSON serializable."
        ) from exc
    return copied


def _require_text(
    payload: Mapping[str, Any],
    field: str,
) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise PackageApprovalError(f"Missing required field: {field}")
    return value


def _disabled_controls() -> dict[str, bool]:
    return dict(_DISABLED_CONTROLS)


def _verify_hash_record(
    record: Mapping[str, Any],
    hash_field: str,
) -> None:
    observed = str(record.get(hash_field) or "")
    material = {
        key: deepcopy(value)
        for key, value in record.items()
        if key != hash_field
    }
    expected = sha256_hex(material)
    if observed != expected:
        raise PackageApprovalError(
            f"{hash_field} verification failed."
        )


def build_review_request(
    package_metadata: Mapping[str, Any],
    quarantine_record: Mapping[str, Any],
    *,
    requested_by: str,
    requested_at_utc: str,
) -> dict[str, Any]:
    """Build a tamper-evident, non-executable package review request."""

    metadata = _plain_mapping(package_metadata)
    quarantine = _plain_mapping(quarantine_record)

    for field in _REQUIRED_METADATA_FIELDS:
        _require_text(metadata, field)

    if str(quarantine.get("status") or "") != QUARANTINE_STATUS:
        raise PackageApprovalError(
            "Only a QUARANTINED package may enter review."
        )

    for field in ("package_hash", "manifest_hash"):
        if _require_text(quarantine, field) != _require_text(metadata, field):
            raise PackageApprovalError(
                f"Quarantine {field} does not match package metadata."
            )

    actor = requested_by.strip()
    timestamp = requested_at_utc.strip()
    if not actor:
        raise PackageApprovalError("requested_by is required.")
    if not timestamp:
        raise PackageApprovalError("requested_at_utc is required.")

    request = {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "record_type": REVIEW_REQUEST_TYPE,
        "request_status": "PENDING_REVIEW",
        "requested_by": actor,
        "requested_at_utc": timestamp,
        "strategy_id": _require_text(metadata, "strategy_id"),
        "version": _require_text(metadata, "version"),
        "display_name": _require_text(metadata, "display_name"),
        "implementation_key": _require_text(
            metadata,
            "implementation_key",
        ),
        "package_hash": _require_text(metadata, "package_hash"),
        "manifest_hash": _require_text(metadata, "manifest_hash"),
        "package_metadata_hash": package_metadata_hash(metadata),
        "quarantine_record_hash": sha256_hex(quarantine),
        "controls": _disabled_controls(),
    }
    request["request_hash"] = sha256_hex(request)
    return request


def approve_review_request(
    review_request: Mapping[str, Any],
    *,
    approved_by: str,
    decided_at_utc: str,
    review_note: str = "",
) -> dict[str, Any]:
    """Approve an intact review request without authorizing activation."""

    request = _plain_mapping(review_request)
    _verify_hash_record(request, "request_hash")

    if request.get("record_type") != REVIEW_REQUEST_TYPE:
        raise PackageApprovalError("Unexpected review request type.")
    if request.get("request_status") != "PENDING_REVIEW":
        raise PackageApprovalError("Review request is not pending.")
    if request.get("controls") != _disabled_controls():
        raise PackageApprovalError(
            "Review request attempted to enable a control."
        )

    actor = approved_by.strip()
    timestamp = decided_at_utc.strip()
    if not actor:
        raise PackageApprovalError("approved_by is required.")
    if not timestamp:
        raise PackageApprovalError("decided_at_utc is required.")

    approval = {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "record_type": APPROVAL_RECORD_TYPE,
        "decision": APPROVED_DECISION,
        "approved_by": actor,
        "decided_at_utc": timestamp,
        "review_note": review_note.strip(),
        "request_hash": request["request_hash"],
        "strategy_id": request["strategy_id"],
        "version": request["version"],
        "implementation_key": request["implementation_key"],
        "package_hash": request["package_hash"],
        "manifest_hash": request["manifest_hash"],
        "package_metadata_hash": request["package_metadata_hash"],
        "controls": _disabled_controls(),
    }
    approval["approval_hash"] = sha256_hex(approval)
    return approval


def verify_approval(
    approval_record: Mapping[str, Any],
    package_metadata: Mapping[str, Any],
    *,
    allowed_implementation_keys: Iterable[str],
) -> dict[str, Any]:
    """Verify approval integrity and reviewed implementation allowlisting."""

    approval = _plain_mapping(approval_record)
    metadata = _plain_mapping(package_metadata)
    _verify_hash_record(approval, "approval_hash")

    if approval.get("record_type") != APPROVAL_RECORD_TYPE:
        raise PackageApprovalError("Unexpected approval record type.")
    if approval.get("decision") != APPROVED_DECISION:
        raise PackageApprovalError("Package is not approved.")
    if approval.get("controls") != _disabled_controls():
        raise PackageApprovalError(
            "Approval record attempted to enable a control."
        )

    allowlist = {
        str(item).strip()
        for item in allowed_implementation_keys
        if str(item).strip()
    }
    implementation_key = _require_text(
        metadata,
        "implementation_key",
    )
    if implementation_key not in allowlist:
        raise PackageApprovalError(
            "Implementation key is not in the reviewed allowlist."
        )

    expected_pairs = {
        "strategy_id": _require_text(metadata, "strategy_id"),
        "version": _require_text(metadata, "version"),
        "implementation_key": implementation_key,
        "package_hash": _require_text(metadata, "package_hash"),
        "manifest_hash": _require_text(metadata, "manifest_hash"),
        "package_metadata_hash": package_metadata_hash(metadata),
    }
    for field, expected in expected_pairs.items():
        if str(approval.get(field) or "") != expected:
            raise PackageApprovalError(
                f"Approval does not match package field: {field}"
            )

    return {
        "valid": True,
        "approval_hash": approval["approval_hash"],
        "strategy_id": expected_pairs["strategy_id"],
        "version": expected_pairs["version"],
        "implementation_key": implementation_key,
        "package_hash": expected_pairs["package_hash"],
        "manifest_hash": expected_pairs["manifest_hash"],
        "package_metadata_hash": expected_pairs[
            "package_metadata_hash"
        ],
        "controls": _disabled_controls(),
    }
