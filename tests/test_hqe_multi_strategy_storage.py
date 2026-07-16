from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.multi_strategy.errors import (
    SelectionSwitchBlockedError,
    StrategyStorageError,
)
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import (
    LEDGER_COLUMNS,
    DisabledStrategyArtifactStore,
    PositionLifecycle,
    StrategyArtifactPaths,
    StrategyLedgerRow,
    StrategyStateSnapshot,
    assert_strategy_switch_allowed,
)


class FakeStrategy:
    def generate(self, context):
        return ()


def selection(strategy_id: str = "storage_test"):
    key = f"hqe.test.{strategy_id}_v1"
    manifest = StrategyManifest(
        strategy_id=strategy_id,
        display_name=strategy_id,
        strategy_version="1.0.0",
        description="test",
        implementation_key=key,
        supported_instruments=("TEST",),
        required_timeframe="5m",
        required_data_columns=("close",),
        warmup_bars=0,
        parameters=(),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    )
    registry = StrategyRegistry({key: lambda parameters: FakeStrategy()})
    return StrategySelectionSnapshot.from_registration(
        registry.register(manifest)
    )


def test_namespace_is_strategy_version_parameter_isolated(tmp_path):
    first = selection("storage_one")
    second = selection("storage_two")
    first_paths = StrategyArtifactPaths.from_selection(tmp_path, first)
    second_paths = StrategyArtifactPaths.from_selection(tmp_path, second)

    assert first_paths.namespace_directory != second_paths.namespace_directory
    assert first.strategy_id in str(first_paths.state)
    assert first.parameters_hash in str(first_paths.ledger)
    assert first_paths.state.name == "state.json"
    assert first_paths.reason_log.name == "reason_log.csv"


def test_offline_store_rejects_runtime_connection(tmp_path):
    with pytest.raises(StrategyStorageError, match="cannot be connected"):
        DisabledStrategyArtifactStore(tmp_path, runtime_connected=True)


def test_store_round_trips_selection_and_flat_state(tmp_path):
    selected = selection()
    store = DisabledStrategyArtifactStore(tmp_path)
    state = StrategyStateSnapshot.from_selection(
        selected, migration_complete=True
    )

    selection_path = store.write_selection(selected)
    state_path = store.write_state(selected, state)

    assert store.read_selection(selected) == selected
    assert store.read_state(selected) == state
    assert selection_path.parent == state_path.parent
    assert not (tmp_path / "MODULE_131_POSITION_STATE.json").exists()


def test_store_rejects_state_identity_mismatch(tmp_path):
    first = selection("storage_one")
    second = selection("storage_two")
    store = DisabledStrategyArtifactStore(tmp_path)
    wrong_state = StrategyStateSnapshot.from_selection(second)

    with pytest.raises(StrategyStorageError, match="does not match"):
        store.write_state(first, wrong_state)


def test_ledger_is_namespaced_append_only_and_schema_checked(tmp_path):
    selected = selection()
    store = DisabledStrategyArtifactStore(tmp_path)
    first = StrategyLedgerRow.from_selection(
        selected,
        event_id="event-1",
        event_time="2026-07-16T10:00:00+05:30",
        lifecycle=PositionLifecycle.OPEN,
        option_side="CE_BUY",
        option_symbol="NIFTY_TEST_CE",
        quantity=75,
        price=100.0,
        reason_code="TEST_OPEN",
    )
    second = StrategyLedgerRow.from_selection(
        selected,
        event_id="event-2",
        event_time="2026-07-16T10:05:00+05:30",
        lifecycle=PositionLifecycle.CLOSED,
        option_side="CE_BUY",
        option_symbol="NIFTY_TEST_CE",
        quantity=75,
        price=110.0,
        realized_pnl=750.0,
        reason_code="TEST_CLOSE",
    )

    path = store.append_ledger_row(selected, first)
    store.append_ledger_row(selected, second)
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert tuple(reader.fieldnames or ()) == LEDGER_COLUMNS
    assert [row["event_id"] for row in rows] == ["event-1", "event-2"]
    assert all(row["selection_hash"] == selected.selection_hash for row in rows)

    with pytest.raises(StrategyStorageError, match="duplicate"):
        store.append_ledger_row(selected, first)


def test_switch_same_selection_is_noop_even_before_migration():
    current = selection()
    state = StrategyStateSnapshot.from_selection(current)
    assert_strategy_switch_allowed(
        current, current, state, runtime_running=True
    )


def test_switch_blocks_running_runtime_open_position_and_migration():
    current = selection("storage_one")
    requested = selection("storage_two")
    flat_migrated = StrategyStateSnapshot.from_selection(
        current, migration_complete=True
    )
    open_state = StrategyStateSnapshot.from_selection(
        current,
        lifecycle=PositionLifecycle.OPEN,
        position={"option_symbol": "NIFTY_TEST_CE"},
        migration_complete=True,
    )
    flat_unmigrated = StrategyStateSnapshot.from_selection(current)

    with pytest.raises(SelectionSwitchBlockedError, match="runtime"):
        assert_strategy_switch_allowed(
            current, requested, flat_migrated, runtime_running=True
        )
    with pytest.raises(SelectionSwitchBlockedError, match="OPEN or HELD"):
        assert_strategy_switch_allowed(
            current, requested, open_state, runtime_running=False
        )
    with pytest.raises(SelectionSwitchBlockedError, match="migration"):
        assert_strategy_switch_allowed(
            current, requested, flat_unmigrated, runtime_running=False
        )


def test_switch_allowed_only_when_flat_stopped_and_migrated():
    current = selection("storage_one")
    requested = selection("storage_two")
    state = StrategyStateSnapshot.from_selection(
        current, migration_complete=True
    )

    assert_strategy_switch_allowed(
        current, requested, state, runtime_running=False
    )
