from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.hqe_multi_strategy_flat_copy_dry_run import (
    run_synthetic_dry_run,
)
from src.multi_strategy.errors import RestartRecoveryError
from src.multi_strategy.recovery import (
    OfflineRecoveryReadiness,
    OfflineRestartRecoveryReader,
)
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle


def build_copy(tmp_path: Path):
    payload = run_synthetic_dry_run(tmp_path / "phase4c")
    selection = StrategySelectionSnapshot.from_dict(
        payload["selection"]
    )
    target_root = Path(payload["target_root"])
    namespace = Path(payload["result"]["namespace_directory"])
    return payload, selection, target_root, namespace


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): (
            hashlib.sha256(path.read_bytes()).hexdigest()
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_offline_recovery_reader_validates_completed_flat_copy(tmp_path):
    payload, selection, target_root, namespace = build_copy(tmp_path)
    before = tree_hashes(target_root)

    snapshot = OfflineRestartRecoveryReader(target_root).read(selection)
    second = OfflineRestartRecoveryReader(target_root).read(selection)

    assert snapshot.readiness is OfflineRecoveryReadiness.READY_FLAT
    assert snapshot.state.lifecycle is PositionLifecycle.FLAT
    assert snapshot.state.migration_complete is True
    assert len(snapshot.ledger_rows) == 2
    assert snapshot.ledger_rows[-1].event_id.endswith(
        snapshot.state.last_event_id[:16]
    )
    assert snapshot.selection.selection_hash == (
        selection.selection_hash
    )
    assert snapshot.snapshot_hash == second.snapshot_hash
    assert snapshot.migration_payload["result_hash"] == (
        payload["result"]["result_hash"]
    )
    assert tree_hashes(target_root) == before
    assert Path(snapshot.namespace_directory) == namespace


def test_recovery_reader_refuses_runtime_connection(tmp_path):
    with pytest.raises(
        RestartRecoveryError,
        match="cannot connect",
    ):
        OfflineRestartRecoveryReader(
            tmp_path,
            runtime_connected=True,
        )


def test_recovery_reader_rejects_tampered_state(tmp_path):
    _, selection, target_root, namespace = build_copy(tmp_path)
    state_path = namespace / "state.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    payload["last_event_id"] = "tampered-event"
    state_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        RestartRecoveryError,
        match="last_event_id",
    ):
        OfflineRestartRecoveryReader(target_root).read(selection)


def test_recovery_reader_rejects_tampered_migration_hash(tmp_path):
    _, selection, target_root, namespace = build_copy(tmp_path)
    migration_path = namespace / "migration.json"
    payload = json.loads(
        migration_path.read_text(encoding="utf-8")
    )
    payload["converted_ledger_rows"] = 999
    migration_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        RestartRecoveryError,
        match="result_hash",
    ):
        OfflineRestartRecoveryReader(target_root).read(selection)


def test_recovery_reader_rejects_missing_legacy_archive(tmp_path):
    _, selection, target_root, namespace = build_copy(tmp_path)
    archived = next(
        path
        for path in (namespace / "legacy_source").iterdir()
        if path.is_file()
    )
    archived.unlink()

    with pytest.raises(
        RestartRecoveryError,
        match="unable to read recovery artifact",
    ):
        OfflineRestartRecoveryReader(target_root).read(selection)


def test_recovery_reader_rejects_runtime_cutover_evidence(tmp_path):
    _, selection, target_root, namespace = build_copy(tmp_path)
    recovery_path = namespace / "recovery.json"
    payload = json.loads(
        recovery_path.read_text(encoding="utf-8")
    )
    payload["runtime_cutover_performed"] = True
    recovery_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        RestartRecoveryError,
        match="runtime cutover",
    ):
        OfflineRestartRecoveryReader(target_root).read(selection)


def test_recovery_reader_rejects_wrong_expected_selection(tmp_path):
    _, selection, target_root, _ = build_copy(tmp_path)
    payload = selection.to_dict()
    payload["strategy_version"] = "9.9.9"
    payload.pop("selection_hash", None)
    wrong = StrategySelectionSnapshot.from_dict(payload)

    with pytest.raises(
        RestartRecoveryError,
        match="namespace does not exist",
    ):
        OfflineRestartRecoveryReader(target_root).read(wrong)
