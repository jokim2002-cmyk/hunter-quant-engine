from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.multi_strategy.approval import (
    approve_review_request,
    build_review_request,
)
from src.multi_strategy.installation import (
    CatalogInstallError,
    install_approved_metadata,
    read_installed_catalog,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    workspace = Path(args.workspace)

    package = {
        "strategy_id": "offline.reviewed.demo",
        "version": "1.0.0",
        "display_name": "Offline Reviewed Demo",
        "implementation_key": "hqe.reviewed.offline_demo_v1",
        "package_hash": "1" * 64,
        "manifest_hash": "2" * 64,
        "source_code": "not installed or executed",
        "entrypoint": "not.imported:main",
    }
    quarantine = {
        "status": "QUARANTINED",
        "package_hash": package["package_hash"],
        "manifest_hash": package["manifest_hash"],
        "quarantine_id": "PHASE4I-OFFLINE-001",
    }
    request = build_review_request(
        package,
        quarantine,
        requested_by="phase4i-offline-operator",
        requested_at_utc="2026-07-17T00:00:00Z",
    )
    approval = approve_review_request(
        request,
        approved_by="phase4i-offline-reviewer",
        decided_at_utc="2026-07-17T00:01:00Z",
        review_note="Synthetic metadata-only approval.",
    )
    allowlist = {"hqe.reviewed.offline_demo_v1"}

    first = install_approved_metadata(
        workspace,
        package,
        approval,
        allowed_implementation_keys=allowlist,
        installed_at_utc="2026-07-17T00:02:00Z",
    )
    second = install_approved_metadata(
        workspace,
        package,
        approval,
        allowed_implementation_keys=allowlist,
        installed_at_utc="2026-07-17T00:03:00Z",
    )

    tampered = deepcopy(approval)
    tampered["package_hash"] = "9" * 64
    tamper_blocked = False
    try:
        install_approved_metadata(
            workspace,
            package,
            tampered,
            allowed_implementation_keys=allowlist,
            installed_at_utc="2026-07-17T00:04:00Z",
        )
    except CatalogInstallError:
        tamper_blocked = True

    catalog = read_installed_catalog(workspace)
    payload = {
        "mode": "OFFLINE_REVIEWED_METADATA_INSTALL_DRY_RUN",
        "approval_verified": True,
        "atomic_install_status": first["status"],
        "idempotent_install_status": second["status"],
        "tampered_approval_blocked": tamper_blocked,
        "catalog_entry_count": len(catalog["entries"]),
        "catalog_hash": catalog["catalog_hash"],
        "read_only": catalog["read_only"],
        "package_payload_installed": False,
        "source_code_installed": False,
        "implementation_imported": False,
        "registration_performed": False,
        "selection_performed": False,
        "activation_authorized": False,
        "canonical_runtime_connected": False,
        "broker_execution_performed": False,
        "real_money_used": False,
        "controls": catalog["controls"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))

    safe = (
        first["status"] == "INSTALLED_METADATA_ONLY"
        and second["status"] == "ALREADY_INSTALLED"
        and tamper_blocked
        and len(catalog["entries"]) == 1
        and catalog["read_only"] is True
        and all(value is False for value in catalog["controls"].values())
    )
    return 0 if safe else 1


if __name__ == "__main__":
    raise SystemExit(main())
