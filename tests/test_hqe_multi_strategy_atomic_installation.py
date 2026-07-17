from __future__ import annotations

import json
from copy import deepcopy

import pytest

from src.multi_strategy.approval import (
    approve_review_request,
    build_review_request,
)
from src.multi_strategy.installation import (
    CATALOG_RELATIVE_PATH,
    LOCK_RELATIVE_PATH,
    CatalogInstallError,
    install_approved_metadata,
    read_installed_catalog,
)


def metadata() -> dict:
    return {
        "strategy_id": "demo.smc",
        "version": "1.0.0",
        "display_name": "Demo SMC",
        "implementation_key": "hqe.reviewed.demo_smc_v1",
        "package_hash": "a" * 64,
        "manifest_hash": "b" * 64,
        "source_code": "print('never run')",
        "entrypoint": "unsafe.module:main",
        "files": ["strategy.py"],
    }


def approved_record(package: dict | None = None) -> dict:
    package = metadata() if package is None else package
    request = build_review_request(
        package,
        {
            "status": "QUARANTINED",
            "package_hash": package["package_hash"],
            "manifest_hash": package["manifest_hash"],
        },
        requested_by="operator",
        requested_at_utc="2026-07-17T00:00:00Z",
    )
    return approve_review_request(
        request,
        approved_by="reviewer",
        decided_at_utc="2026-07-17T00:01:00Z",
    )


def install(tmp_path, package: dict | None = None):
    package = metadata() if package is None else package
    return install_approved_metadata(
        tmp_path,
        package,
        approved_record(package),
        allowed_implementation_keys={
            "hqe.reviewed.demo_smc_v1"
        },
        installed_at_utc="2026-07-17T00:02:00Z",
    )


def test_atomic_metadata_install_creates_verified_catalog(tmp_path):
    result = install(tmp_path)
    catalog = read_installed_catalog(tmp_path)

    assert result["status"] == "INSTALLED_METADATA_ONLY"
    assert result["changed"] is True
    assert catalog["revision"] == 1
    assert len(catalog["entries"]) == 1
    assert catalog["read_only"] is True
    assert all(value is False for value in catalog["controls"].values())


def test_repeated_install_is_idempotent(tmp_path):
    first = install(tmp_path)
    second = install(tmp_path)

    assert first["changed"] is True
    assert second["status"] == "ALREADY_INSTALLED"
    assert second["changed"] is False
    assert second["catalog_hash_before"] == second["catalog_hash_after"]


def test_collision_is_rejected_and_catalog_is_unchanged(tmp_path):
    install(tmp_path)
    before = (tmp_path / CATALOG_RELATIVE_PATH).read_bytes()

    changed = metadata()
    changed["package_hash"] = "c" * 64
    with pytest.raises(CatalogInstallError, match="collision"):
        install(tmp_path, changed)

    assert (tmp_path / CATALOG_RELATIVE_PATH).read_bytes() == before


def test_tampered_approval_does_not_create_catalog(tmp_path):
    package = metadata()
    approval = approved_record(package)
    approval["package_hash"] = "f" * 64

    with pytest.raises(CatalogInstallError, match="approval_hash"):
        install_approved_metadata(
            tmp_path,
            package,
            approval,
            allowed_implementation_keys={
                "hqe.reviewed.demo_smc_v1"
            },
            installed_at_utc="2026-07-17T00:02:00Z",
        )

    assert not (tmp_path / CATALOG_RELATIVE_PATH).exists()


def test_catalog_projection_excludes_code_and_entrypoints(tmp_path):
    install(tmp_path)
    entry = read_installed_catalog(tmp_path)["entries"][0]
    serialized = json.dumps(entry, sort_keys=True)

    assert "source_code" not in entry
    assert "entrypoint" not in entry
    assert "files" not in entry
    assert "never run" not in serialized
    assert entry["source_code_installed"] is False
    assert entry["implementation_imported"] is False


def test_lock_and_temporary_files_are_removed(tmp_path):
    install(tmp_path)
    assert not (tmp_path / LOCK_RELATIVE_PATH).exists()
    catalog_dir = (tmp_path / CATALOG_RELATIVE_PATH).parent
    assert not list(catalog_dir.glob("*.tmp"))
    assert not list(catalog_dir.glob(".*.tmp"))


def test_tampered_catalog_is_rejected(tmp_path):
    install(tmp_path)
    path = tmp_path / CATALOG_RELATIVE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["revision"] = 99
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CatalogInstallError, match="hash"):
        read_installed_catalog(tmp_path)

def test_existing_lock_blocks_without_removing_other_lock(tmp_path):
    lock_path = tmp_path / LOCK_RELATIVE_PATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("other-installer", encoding="utf-8")

    with pytest.raises(CatalogInstallError, match="in progress"):
        install(tmp_path)

    assert lock_path.read_text(encoding="utf-8") == "other-installer"
    assert not (tmp_path / CATALOG_RELATIVE_PATH).exists()
