"""Isolated complete Phase 6 reviewed import workflow rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.multi_strategy.adapters.current_smc import CURRENT_SMC_IMPLEMENTATION_KEY
from src.multi_strategy.import_workflow import (
    APPROVAL_PHRASE,
    ReviewedImportWorkflowError,
    approve_reviewed_import,
    begin_reviewed_import,
    guard_payload,
    install_reviewed_metadata,
    workflow_snapshot,
)
from src.multi_strategy.installation import read_installed_catalog
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_package(
    root: Path,
    *,
    strategy_id: str,
    implementation_key: str,
) -> None:
    root.mkdir(parents=True, exist_ok=False)
    manifest = StrategyManifest(
        strategy_id=strategy_id,
        display_name=f"Rehearsal {strategy_id}",
        strategy_version="1.0.0",
        description="Phase 6 isolated reviewed import rehearsal.",
        implementation_key=implementation_key,
        supported_instruments=("NIFTY_INDEX_OPTION_BUY",),
        required_timeframe="5m",
        required_data_columns=(
            "timestamp", "open", "high", "low", "close", "volume"
        ),
        warmup_bars=20,
        parameters=(),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    )
    manifest_path = root / "manifest.json"
    readme_path = root / "README.md"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    readme_path.write_text("# Phase 6 rehearsal\n", encoding="utf-8")
    (root / "checksums.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "files": {
                    "README.md": sha(readme_path),
                    "manifest.json": sha(manifest_path),
                },
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run(workspace: Path) -> dict:
    if workspace.exists():
        raise RuntimeError(f"workspace already exists: {workspace}")
    workspace.mkdir(parents=True)
    sources = workspace / "source_packages"
    reviewed_source = sources / "reviewed"
    unreviewed_source = sources / "unreviewed"
    write_package(
        reviewed_source,
        strategy_id="phase6_rehearsal_reviewed",
        implementation_key=CURRENT_SMC_IMPLEMENTATION_KEY,
    )
    write_package(
        unreviewed_source,
        strategy_id="phase6_rehearsal_unreviewed",
        implementation_key="hqe.unreviewed.phase6_rehearsal_v1",
    )
    source_before = {
        "reviewed": tree_hashes(reviewed_source),
        "unreviewed": tree_hashes(unreviewed_source),
    }

    reviewed = begin_reviewed_import(
        reviewed_source,
        workspace,
        requested_by="phase6-rehearsal-operator",
        requested_at_utc="2026-07-17T10:00:00Z",
    )
    wrong_phrase_blocked = False
    try:
        approve_reviewed_import(
            workspace,
            approval_phrase="approve",
            approved_by="phase6-rehearsal-reviewer",
        )
    except ReviewedImportWorkflowError:
        wrong_phrase_blocked = True

    approved = approve_reviewed_import(
        workspace,
        approval_phrase=APPROVAL_PHRASE,
        approved_by="phase6-rehearsal-reviewer",
        decided_at_utc="2026-07-17T10:01:00Z",
        review_note="Reviewed reference and metadata only.",
    )
    installed = install_reviewed_metadata(
        workspace,
        installed_at_utc="2026-07-17T10:02:00Z",
    )
    repeated = install_reviewed_metadata(
        workspace,
        installed_at_utc="2026-07-17T10:03:00Z",
    )

    unreviewed = begin_reviewed_import(
        unreviewed_source,
        workspace,
        requested_by="phase6-rehearsal-operator",
        requested_at_utc="2026-07-17T10:04:00Z",
    )
    unreviewed_approval_blocked = False
    try:
        approve_reviewed_import(
            workspace,
            approval_phrase=APPROVAL_PHRASE,
            approved_by="phase6-rehearsal-reviewer",
        )
    except ReviewedImportWorkflowError:
        unreviewed_approval_blocked = True

    source_after = {
        "reviewed": tree_hashes(reviewed_source),
        "unreviewed": tree_hashes(unreviewed_source),
    }
    catalog = read_installed_catalog(workspace)
    payload = {
        "mode": "PHASE6_COMPLETE_REVIEWED_IMPORT_REHEARSAL",
        "status": "PASS",
        "reviewed_begin_state": reviewed["state"],
        "wrong_phrase_blocked": wrong_phrase_blocked,
        "approved_state": approved["state"],
        "installed_state": installed["state"],
        "repeat_install_idempotent": (
            repeated["catalog_hash"] == installed["catalog_hash"]
        ),
        "installed_metadata_count": len(catalog["entries"]),
        "unreviewed_state": unreviewed["state"],
        "unreviewed_approval_blocked": unreviewed_approval_blocked,
        "source_packages_unchanged": source_before == source_after,
        "latest_state": workflow_snapshot(workspace)["state"],
        "source_code_imported": False,
        "package_payload_installed": False,
        "strategy_registered": False,
        "strategy_selected": False,
        "canonical_activation_performed": False,
        "human_cutover_gate_created": False,
        "runtime_control_performed": False,
        "lifecycle_state_ledger_written": False,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "real_money_allowed": False,
        "guard": guard_payload(),
    }
    required_true = (
        payload["wrong_phrase_blocked"],
        payload["repeat_install_idempotent"],
        payload["unreviewed_approval_blocked"],
        payload["source_packages_unchanged"],
    )
    if not all(required_true):
        raise RuntimeError("Phase 6 rehearsal safety assertion failed")
    if reviewed["state"] != "PENDING_REVIEW":
        raise RuntimeError("Reviewed package did not enter pending review")
    if approved["state"] != "APPROVED_METADATA_ONLY":
        raise RuntimeError("Reviewed package approval state failed")
    if installed["state"] != "INSTALLED_METADATA_ONLY":
        raise RuntimeError("Metadata installation state failed")
    if unreviewed["state"] != "REVIEW_BLOCKED":
        raise RuntimeError("Unreviewed package was not blocked")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    print(json.dumps(run(Path(args.workspace)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
