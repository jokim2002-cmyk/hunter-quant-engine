from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from .approval import (
    PackageApprovalError,
    canonical_json,
    sha256_hex,
    verify_approval,
)

CATALOG_SCHEMA_VERSION = "1.0"
CATALOG_RELATIVE_PATH = Path(
    "HQE_MULTI_STRATEGY_CATALOG"
) / "installed_metadata_catalog.json"
LOCK_RELATIVE_PATH = Path(
    "HQE_MULTI_STRATEGY_CATALOG"
) / ".metadata_install.lock"

_DISABLED_CONTROLS = {
    "activation_enabled": False,
    "broker_execution_enabled": False,
    "import_enabled": False,
    "real_money_enabled": False,
    "registration_enabled": False,
    "runtime_control_enabled": False,
    "selection_enabled": False,
}


class CatalogInstallError(RuntimeError):
    """Raised when metadata-only catalog installation is unsafe."""


def _disabled_controls() -> dict[str, bool]:
    return dict(_DISABLED_CONTROLS)


def _catalog_material(catalog: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in catalog.items()
        if key != "catalog_hash"
    }


def _empty_catalog() -> dict[str, Any]:
    catalog = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "catalog_type": "HQE_INSTALLED_METADATA_ONLY_CATALOG",
        "read_only": True,
        "revision": 0,
        "entries": [],
        "controls": _disabled_controls(),
    }
    catalog["catalog_hash"] = sha256_hex(_catalog_material(catalog))
    return catalog


def _verify_catalog(catalog: Mapping[str, Any]) -> dict[str, Any]:
    observed = deepcopy(dict(catalog))
    if observed.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise CatalogInstallError("Unsupported catalog schema.")
    if (
        observed.get("catalog_type")
        != "HQE_INSTALLED_METADATA_ONLY_CATALOG"
    ):
        raise CatalogInstallError("Unexpected catalog type.")
    if observed.get("read_only") is not True:
        raise CatalogInstallError("Catalog is not read-only.")
    if observed.get("controls") != _disabled_controls():
        raise CatalogInstallError(
            "Catalog attempted to enable a control."
        )
    if not isinstance(observed.get("entries"), list):
        raise CatalogInstallError("Catalog entries are invalid.")

    expected = sha256_hex(_catalog_material(observed))
    if observed.get("catalog_hash") != expected:
        raise CatalogInstallError(
            "Installed catalog hash verification failed."
        )
    return observed


def read_installed_catalog(workspace: Path | str) -> dict[str, Any]:
    path = Path(workspace) / CATALOG_RELATIVE_PATH
    if not path.exists():
        return _empty_catalog()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogInstallError(
            "Installed catalog could not be read."
        ) from exc
    return _verify_catalog(payload)


def _safe_entry(
    package_metadata: Mapping[str, Any],
    verified: Mapping[str, Any],
    *,
    installed_at_utc: str,
) -> dict[str, Any]:
    metadata = dict(package_metadata)
    display_name = str(metadata.get("display_name") or "").strip()
    if not display_name:
        raise CatalogInstallError("display_name is required.")

    return {
        "strategy_id": verified["strategy_id"],
        "version": verified["version"],
        "display_name": display_name,
        "implementation_key": verified["implementation_key"],
        "package_hash": verified["package_hash"],
        "manifest_hash": verified["manifest_hash"],
        "package_metadata_hash": verified["package_metadata_hash"],
        "approval_hash": verified["approval_hash"],
        "installation_status": "INSTALLED_METADATA_ONLY",
        "installed_at_utc": installed_at_utc,
        "payload_installed": False,
        "source_code_installed": False,
        "implementation_imported": False,
        "registered": False,
        "selected": False,
        "activated": False,
        "runtime_connected": False,
        "controls": _disabled_controls(),
    }


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        serialized = (
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        )
        with temporary.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(serialized)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def install_approved_metadata(
    workspace: Path | str,
    package_metadata: Mapping[str, Any],
    approval_record: Mapping[str, Any],
    *,
    allowed_implementation_keys: Iterable[str],
    installed_at_utc: str,
) -> dict[str, Any]:
    """Atomically install approved metadata; never import package code."""

    root = Path(workspace)
    timestamp = installed_at_utc.strip()
    if not timestamp:
        raise CatalogInstallError("installed_at_utc is required.")

    try:
        verified = verify_approval(
            approval_record,
            package_metadata,
            allowed_implementation_keys=allowed_implementation_keys,
        )
    except PackageApprovalError as exc:
        raise CatalogInstallError(str(exc)) from exc

    catalog_path = root / CATALOG_RELATIVE_PATH
    lock_path = root / LOCK_RELATIVE_PATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock_fd: int | None = None
    try:
        try:
            lock_fd = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            os.write(
                lock_fd,
                verified["approval_hash"].encode("ascii"),
            )
            os.fsync(lock_fd)
        except FileExistsError as exc:
            raise CatalogInstallError(
                "Another metadata installation is in progress."
            ) from exc

        before = read_installed_catalog(root)
        identity = (
            verified["strategy_id"],
            verified["version"],
        )
        existing = None
        for entry in before["entries"]:
            if (
                entry.get("strategy_id"),
                entry.get("version"),
            ) == identity:
                existing = entry
                break

        if existing is not None:
            same_install = all(
                existing.get(field) == verified[field]
                for field in (
                    "implementation_key",
                    "package_hash",
                    "manifest_hash",
                    "package_metadata_hash",
                    "approval_hash",
                )
            )
            if not same_install:
                raise CatalogInstallError(
                    "Strategy/version catalog collision detected."
                )
            return {
                "status": "ALREADY_INSTALLED",
                "changed": False,
                "catalog_path": str(catalog_path),
                "catalog_hash_before": before["catalog_hash"],
                "catalog_hash_after": before["catalog_hash"],
                "entry": deepcopy(existing),
                "controls": _disabled_controls(),
            }

        entry = _safe_entry(
            package_metadata,
            verified,
            installed_at_utc=timestamp,
        )
        entries = [deepcopy(item) for item in before["entries"]]
        entries.append(entry)
        entries.sort(
            key=lambda item: (
                str(item.get("strategy_id") or ""),
                str(item.get("version") or ""),
            )
        )

        after = {
            "schema_version": CATALOG_SCHEMA_VERSION,
            "catalog_type": "HQE_INSTALLED_METADATA_ONLY_CATALOG",
            "read_only": True,
            "revision": int(before.get("revision") or 0) + 1,
            "entries": entries,
            "controls": _disabled_controls(),
        }
        after["catalog_hash"] = sha256_hex(_catalog_material(after))
        _atomic_write(catalog_path, after)

        verified_after = read_installed_catalog(root)
        if verified_after["catalog_hash"] != after["catalog_hash"]:
            raise CatalogInstallError(
                "Atomic catalog post-write verification failed."
            )

        return {
            "status": "INSTALLED_METADATA_ONLY",
            "changed": True,
            "catalog_path": str(catalog_path),
            "catalog_hash_before": before["catalog_hash"],
            "catalog_hash_after": verified_after["catalog_hash"],
            "entry": deepcopy(entry),
            "controls": _disabled_controls(),
        }
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
            if lock_path.exists():
                lock_path.unlink()
