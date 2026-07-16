from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.multi_strategy.errors import (
    LegacyRecoveryError,
    MigrationExecutionDisabledError,
)
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.migration import (
    LEGACY_LEDGER_REQUIRED_COLUMNS,
    LegacyModule131MigrationPlanner,
    LegacyModule131Paths,
    MigrationReadiness,
    assert_migration_execution_allowed,
    build_recovery_compatibility_snapshot,
)
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle


class FakeStrategy:
    def generate(self, context):
        return ()


def selection(strategy_id: str = "migration_test"):
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


def paths(tmp_path: Path) -> LegacyModule131Paths:
    return LegacyModule131Paths.from_runtime_folder(tmp_path)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def flat_state() -> dict:
    return {
        "status": "FLAT",
        "paper_only": True,
        "module": 131,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "auto_trading_allowed": False,
        "real_money_allowed": False,
    }


def open_state() -> dict:
    return {
        "status": "OPEN",
        "paper_only": True,
        "module": 131,
        "side": "CE_BUY",
        "option_symbol": "NIFTY_TEST_CE",
        "candidate": "SMC_BIDIRECTIONAL_TEST",
        "entry_time": "2026-07-16T10:00:00",
        "entry": 100.0,
        "stop_loss": 60.0,
        "target": 220.0,
        "quantity": 1,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "auto_trading_allowed": False,
        "real_money_allowed": False,
    }


def ledger_row(event: str, side: str = "CE_BUY") -> dict[str, str]:
    return {
        "timestamp": "2026-07-16T10:00:00",
        "module": "131",
        "event": event,
        "side": side,
        "option_symbol": "NIFTY_TEST_CE",
        "entry": "100.0",
        "stop_loss": "60.0",
        "target": "220.0",
        "exit_reason": "" if event == "POSITION_OPENED" else "TARGET_HIT",
        "paper_pnl": "0.0" if event == "POSITION_OPENED" else "120.0",
        "paper_only": "True",
    }


def write_ledger(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(LEGACY_LEDGER_REQUIRED_COLUMNS),
        )
        writer.writeheader()
        writer.writerows(rows)


def test_no_legacy_data_is_non_executable(tmp_path):
    selected = selection()
    plan = LegacyModule131MigrationPlanner(
        paths(tmp_path), selected
    ).build_plan()

    assert plan.readiness is MigrationReadiness.NO_LEGACY_DATA
    assert plan.migration_ready is False
    assert plan.execution_authorized is False
    assert plan.proposed_state.lifecycle is PositionLifecycle.FLAT
    with pytest.raises(MigrationExecutionDisabledError):
        assert_migration_execution_allowed(plan)


def test_flat_consistent_legacy_state_is_ready_for_future_copy(tmp_path):
    selected = selection()
    legacy = paths(tmp_path)
    write_json(legacy.state, flat_state())
    write_ledger(
        legacy.ledger,
        [ledger_row("POSITION_OPENED"), ledger_row("POSITION_CLOSED")],
    )

    before_state = legacy.state.read_bytes()
    before_ledger = legacy.ledger.read_bytes()
    first = LegacyModule131MigrationPlanner(
        legacy, selected
    ).build_plan()
    second = LegacyModule131MigrationPlanner(
        legacy, selected
    ).build_plan()

    assert first.readiness is MigrationReadiness.READY_FLAT
    assert first.migration_ready is True
    assert first.proposed_state.lifecycle is PositionLifecycle.FLAT
    assert first.proposed_state.migration_complete is False
    assert first.plan_hash == second.plan_hash
    assert legacy.state.read_bytes() == before_state
    assert legacy.ledger.read_bytes() == before_ledger


def test_open_position_is_preserved_and_blocks_migration(tmp_path):
    selected = selection()
    legacy = paths(tmp_path)
    write_json(legacy.state, open_state())
    write_ledger(legacy.ledger, [ledger_row("POSITION_OPENED")])

    plan = LegacyModule131MigrationPlanner(
        legacy, selected
    ).build_plan()
    recovery = build_recovery_compatibility_snapshot(
        plan, selected
    )

    assert plan.readiness is MigrationReadiness.BLOCKED_OPEN_POSITION
    assert plan.proposed_state.lifecycle is PositionLifecycle.OPEN
    assert plan.proposed_state.position["option_symbol"] == "NIFTY_TEST_CE"
    assert plan.proposed_state.position["entry"] == 100.0
    assert recovery.state == plan.proposed_state
    assert recovery.migration_complete is False
    assert recovery.runtime_connected is False
    assert recovery.source_state_sha256
    assert recovery.source_ledger_sha256


def test_running_runtime_blocks_flat_plan(tmp_path):
    selected = selection()
    legacy = paths(tmp_path)
    write_json(legacy.state, flat_state())
    write_json(
        legacy.runtime,
        {"status": "RUNNING_MARKET_WATCH", "pid": 1234},
    )

    plan = LegacyModule131MigrationPlanner(
        legacy, selected
    ).build_plan()
    assert plan.readiness is MigrationReadiness.BLOCKED_RUNTIME_RUNNING


def test_explicit_stop_confirmation_is_recorded_but_does_not_execute(tmp_path):
    selected = selection()
    legacy = paths(tmp_path)
    write_json(legacy.state, flat_state())
    write_json(
        legacy.runtime,
        {"status": "RUNNING_MARKET_WATCH", "pid": 1234},
    )

    plan = LegacyModule131MigrationPlanner(
        legacy,
        selected,
        runtime_confirmed_stopped=True,
    ).build_plan()

    assert plan.readiness is MigrationReadiness.READY_FLAT
    assert any("confirmed" in warning for warning in plan.warnings)
    with pytest.raises(MigrationExecutionDisabledError):
        assert_migration_execution_allowed(plan)


def test_corrupt_state_fails_closed(tmp_path):
    selected = selection()
    legacy = paths(tmp_path)
    legacy.state.write_text("{not-json", encoding="utf-8")

    plan = LegacyModule131MigrationPlanner(
        legacy, selected
    ).build_plan()
    assert plan.readiness is MigrationReadiness.BLOCKED_CORRUPT_STATE
    assert plan.issues


def test_flat_state_with_unmatched_open_ledger_is_blocked(tmp_path):
    selected = selection()
    legacy = paths(tmp_path)
    write_json(legacy.state, flat_state())
    write_ledger(legacy.ledger, [ledger_row("POSITION_OPENED")])

    plan = LegacyModule131MigrationPlanner(
        legacy, selected
    ).build_plan()
    assert (
        plan.readiness
        is MigrationReadiness.BLOCKED_LEDGER_INCONSISTENT
    )


def test_close_before_open_is_blocked(tmp_path):
    selected = selection()
    legacy = paths(tmp_path)
    write_json(legacy.state, flat_state())
    write_ledger(legacy.ledger, [ledger_row("POSITION_CLOSED")])

    plan = LegacyModule131MigrationPlanner(
        legacy, selected
    ).build_plan()
    assert (
        plan.readiness
        is MigrationReadiness.BLOCKED_LEDGER_INCONSISTENT
    )


def test_unsafe_capability_is_blocked(tmp_path):
    selected = selection()
    legacy = paths(tmp_path)
    payload = flat_state()
    payload["real_orders_allowed"] = True
    write_json(legacy.state, payload)

    plan = LegacyModule131MigrationPlanner(
        legacy, selected
    ).build_plan()
    assert plan.readiness is MigrationReadiness.BLOCKED_SAFETY_VIOLATION


def test_missing_ledger_columns_are_blocked(tmp_path):
    selected = selection()
    legacy = paths(tmp_path)
    write_json(legacy.state, flat_state())
    legacy.ledger.write_text(
        "timestamp,event\n2026-07-16T10:00:00,POSITION_OPENED\n",
        encoding="utf-8",
    )

    plan = LegacyModule131MigrationPlanner(
        legacy, selected
    ).build_plan()
    assert (
        plan.readiness
        is MigrationReadiness.BLOCKED_LEDGER_INCONSISTENT
    )


def test_plan_and_recovery_are_json_serializable(tmp_path):
    selected = selection()
    legacy = paths(tmp_path)
    write_json(legacy.state, flat_state())

    plan = LegacyModule131MigrationPlanner(
        legacy, selected
    ).build_plan()
    recovery = build_recovery_compatibility_snapshot(
        plan, selected
    )

    json.dumps(plan.to_dict(), sort_keys=True)
    json.dumps(recovery.to_dict(), sort_keys=True)
    assert recovery.recovery_hash


def test_recovery_rejects_different_selection(tmp_path):
    first = selection("migration_one")
    second = selection("migration_two")
    legacy = paths(tmp_path)
    write_json(legacy.state, flat_state())
    plan = LegacyModule131MigrationPlanner(
        legacy, first
    ).build_plan()

    with pytest.raises(LegacyRecoveryError, match="does not match"):
        build_recovery_compatibility_snapshot(plan, second)



def test_read_only_cli_payload_never_enables_migration(tmp_path):
    from scripts.hqe_multi_strategy_legacy_migration_audit import (
        build_audit_payload,
    )

    legacy = paths(tmp_path)
    write_json(legacy.state, flat_state())
    payload = build_audit_payload(tmp_path)

    assert payload["mode"] == "READ_ONLY"
    assert payload["runtime_connected"] is False
    assert payload["migration_execution_enabled"] is False
    assert payload["plan"]["readiness"] == "READY_FLAT"
    assert payload["recovery"]["migration_complete"] is False
