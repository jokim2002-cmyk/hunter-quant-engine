from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

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
    strategy_id: str = "phase6_reviewed_demo",
    version: str = "1.0.0",
    implementation_key: str = CURRENT_SMC_IMPLEMENTATION_KEY,
    display_name: str = "Phase 6 Reviewed Demo",
) -> Path:
    root.mkdir(parents=True)
    manifest = StrategyManifest(
        strategy_id=strategy_id,
        display_name=display_name,
        strategy_version=version,
        description="Synthetic reviewed import workflow package.",
        implementation_key=implementation_key,
        supported_instruments=("NIFTY_INDEX_OPTION_BUY",),
        required_timeframe="5m",
        required_data_columns=(
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
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
    readme_path.write_text("# Phase 6 reviewed package\n", encoding="utf-8")
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
        )
        + "\n",
        encoding="utf-8",
    )
    return root


def begin(tmp_path: Path, **kwargs):
    source = write_package(tmp_path / "source", **kwargs)
    workspace = tmp_path / "workspace"
    snapshot = begin_reviewed_import(
        source,
        workspace,
        requested_by="phase6-operator",
        requested_at_utc="2026-07-17T10:00:00Z",
    )
    return source, workspace, snapshot


def approve(workspace: Path):
    return approve_reviewed_import(
        workspace,
        approval_phrase=APPROVAL_PHRASE,
        approved_by="phase6-reviewer",
        decided_at_utc="2026-07-17T10:01:00Z",
        review_note="Reviewed local implementation reference only.",
    )


def test_guard_permanently_blocks_execution_authority():
    payload = guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["metadata_catalog_install_only"] is True
    for key in (
        "source_code_import_allowed",
        "package_payload_install_allowed",
        "registration_allowed",
        "selection_allowed",
        "canonical_activation_allowed",
        "human_cutover_gate_creation_allowed",
        "runtime_control_allowed",
        "lifecycle_write_allowed",
        "state_write_allowed",
        "ledger_write_allowed",
        "real_orders_allowed",
        "broker_execution_allowed",
        "auto_trading_allowed",
        "real_money_allowed",
        "option_selling_allowed",
    ):
        assert payload[key] is False


def test_empty_snapshot_is_safe(tmp_path):
    payload = workflow_snapshot(tmp_path)
    assert payload["exists"] is False
    assert payload["state"] == "NO_WORKFLOW"
    assert payload["controls"]["approve_enabled"] is False
    assert payload["controls"]["install_metadata_enabled"] is False


def test_reviewed_package_enters_stable_quarantine_and_pending_review(tmp_path):
    source, _, snapshot = begin(tmp_path)
    assert snapshot["state"] == "PENDING_REVIEW"
    assert snapshot["reviewed_implementation_available"] is True
    assert snapshot["blockers"] == []
    assert snapshot["controls"]["approve_enabled"] is True
    assert Path(snapshot["quarantine_directory"]).is_dir()
    assert sha(source / "manifest.json") == sha(
        Path(snapshot["quarantine_directory"]) / "manifest.json"
    )
    assert snapshot["source_code_import_allowed"] is False


def test_unreviewed_implementation_is_quarantined_but_review_blocked(tmp_path):
    _, _, snapshot = begin(
        tmp_path,
        implementation_key="hqe.unreviewed.phase6_demo_v1",
    )
    assert snapshot["state"] == "REVIEW_BLOCKED"
    assert snapshot["reviewed_implementation_available"] is False
    assert snapshot["controls"]["approve_enabled"] is False
    assert any("reviewed" in blocker.lower() for blocker in snapshot["blockers"])


def test_wrong_approval_phrase_fails_closed(tmp_path):
    _, workspace, _ = begin(tmp_path)
    with pytest.raises(ReviewedImportWorkflowError, match="Exact"):
        approve_reviewed_import(
            workspace,
            approval_phrase="approve",
            approved_by="reviewer",
        )
    assert workflow_snapshot(workspace)["state"] == "PENDING_REVIEW"


def test_explicit_approval_is_tamper_evident_and_non_activating(tmp_path):
    _, workspace, _ = begin(tmp_path)
    snapshot = approve(workspace)
    assert snapshot["state"] == "APPROVED_METADATA_ONLY"
    assert snapshot["controls"]["install_metadata_enabled"] is True
    assert Path(snapshot["approval_path"]).is_file()
    assert snapshot["canonical_activation_allowed"] is False
    assert snapshot["selection_allowed"] is False


def test_atomic_install_writes_metadata_only_catalog(tmp_path):
    _, workspace, _ = begin(tmp_path)
    approve(workspace)
    snapshot = install_reviewed_metadata(
        workspace,
        installed_at_utc="2026-07-17T10:02:00Z",
    )
    catalog = read_installed_catalog(workspace)
    assert snapshot["state"] == "INSTALLED_METADATA_ONLY"
    assert len(catalog["entries"]) == 1
    entry = catalog["entries"][0]
    assert entry["installation_status"] == "INSTALLED_METADATA_ONLY"
    assert entry["payload_installed"] is False
    assert entry["source_code_installed"] is False
    assert entry["registered"] is False
    assert entry["selected"] is False
    assert entry["activated"] is False
    assert entry["runtime_connected"] is False


def test_repeated_identical_install_is_idempotent(tmp_path):
    _, workspace, _ = begin(tmp_path)
    approve(workspace)
    first = install_reviewed_metadata(workspace, installed_at_utc="2026-07-17T10:02:00Z")
    second = install_reviewed_metadata(workspace, installed_at_utc="2026-07-17T10:03:00Z")
    assert first["catalog_hash"] == second["catalog_hash"]
    assert len(read_installed_catalog(workspace)["entries"]) == 1


def test_same_id_version_with_different_package_is_collision_blocked(tmp_path):
    workspace = tmp_path / "workspace"
    first = write_package(tmp_path / "first")
    begin_reviewed_import(first, workspace, requested_by="operator")
    approve(workspace)
    install_reviewed_metadata(workspace)

    second = write_package(
        tmp_path / "second",
        display_name="Different package evidence",
    )
    begin_reviewed_import(second, workspace, requested_by="operator")
    approve(workspace)
    with pytest.raises(ReviewedImportWorkflowError, match="collision"):
        install_reviewed_metadata(workspace)
    assert len(read_installed_catalog(workspace)["entries"]) == 1


def test_tampered_workflow_record_is_rejected(tmp_path):
    _, workspace, snapshot = begin(tmp_path)
    path = Path(snapshot["workflow_path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"] = "APPROVED_METADATA_ONLY"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ReviewedImportWorkflowError, match="hash"):
        workflow_snapshot(workspace)


def test_tampered_approval_cannot_install(tmp_path):
    _, workspace, _ = begin(tmp_path)
    snapshot = approve(workspace)
    path = Path(snapshot["approval_path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["approved_by"] = "attacker"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ReviewedImportWorkflowError, match="approval_hash"):
        install_reviewed_metadata(workspace)
    assert read_installed_catalog(workspace)["entries"] == []


def test_evidence_audit_and_latest_pointer_are_written(tmp_path):
    _, workspace, snapshot = begin(tmp_path)
    approve(workspace)
    final = install_reviewed_metadata(workspace)
    directory = Path(final["workflow_path"]).parent
    events = [
        json.loads(line)["event"]
        for line in (directory / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert events == [
        "QUARANTINED_AND_REVIEW_REQUESTED",
        "EXPLICITLY_APPROVED_METADATA_ONLY",
        "ATOMIC_METADATA_INSTALL",
    ]
    assert workflow_snapshot(workspace)["workflow_hash"] == final["workflow_hash"]
