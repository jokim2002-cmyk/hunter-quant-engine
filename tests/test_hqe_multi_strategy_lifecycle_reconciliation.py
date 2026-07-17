from __future__ import annotations

import csv
import json
from dataclasses import replace

import pytest

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    build_current_smc_adapter,
    current_smc_manifest,
)
from src.multi_strategy.lifecycle_journal import (
    SandboxLifecycleBundle,
    SandboxLifecycleEvent,
    state_hash,
)
from src.multi_strategy.lifecycle_reconciliation import (
    LifecycleReconciliationError,
    LifecycleReconciliationStatus,
    reconcile_lifecycle_evidence,
)
from src.multi_strategy.migration import (
    LEGACY_LEDGER_REQUIRED_COLUMNS,
    LegacyModule131MigrationPlanner,
    LegacyModule131Paths,
)
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot


def selection(parameters=None):
    manifest = current_smc_manifest()
    registry = StrategyRegistry(
        {CURRENT_SMC_IMPLEMENTATION_KEY: build_current_smc_adapter}
    )
    registration = registry.register(manifest, source="phase4l:test")
    return StrategySelectionSnapshot.from_registration(registration, parameters)


def write_canonical(
    root,
    *,
    status="FLAT",
    side="CE_BUY",
    symbol="NIFTY_PHASE4L_CE",
    quantity=75,
    entry=100.0,
    cycles=1,
    running=False,
    corrupt_state=False,
):
    root.mkdir(parents=True, exist_ok=True)
    runtime = {
        "status": "RUNNING" if running else "STOPPED",
        "running": running,
        "paper_only": True,
        "broker_execution": False,
    }
    (root / "HQE_PAPER_PRODUCT_RUNTIME.json").write_text(
        json.dumps(runtime), encoding="utf-8"
    )
    state = {
        "status": "BROKEN" if corrupt_state else status,
        "paper_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "auto_trading_allowed": False,
        "real_money_allowed": False,
    }
    if status == "OPEN" and not corrupt_state:
        state.update(
            {
                "side": side,
                "option_symbol": symbol,
                "entry": entry,
                "stop_loss": 60.0,
                "target": 220.0,
                "quantity": quantity,
                "candidate": "PHASE4L",
                "entry_time": "2026-07-17T11:01:00+05:30",
            }
        )
    (root / "MODULE_131_POSITION_STATE.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    rows = []
    for index in range(cycles):
        rows.append(
            {
                "timestamp": f"2026-07-17T11:{index * 2 + 1:02d}:00+05:30",
                "module": "131",
                "event": "POSITION_OPENED",
                "side": side,
                "option_symbol": symbol,
                "entry": str(entry),
                "stop_loss": "60.0",
                "target": "220.0",
                "exit_reason": "",
                "paper_pnl": "0.0",
                "paper_only": "true",
            }
        )
        if status != "OPEN" or index < cycles - 1:
            rows.append(
                {
                    "timestamp": f"2026-07-17T11:{index * 2 + 2:02d}:00+05:30",
                    "module": "131",
                    "event": "POSITION_CLOSED",
                    "side": side,
                    "option_symbol": symbol,
                    "entry": str(entry),
                    "stop_loss": "60.0",
                    "target": "220.0",
                    "exit_reason": "TARGET",
                    "paper_pnl": "750.0",
                    "paper_only": "true",
                }
            )
    with (root / "MODULE_131_PAPER_LEDGER.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=LEGACY_LEDGER_REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def plan(root, selected, **kwargs):
    write_canonical(root, **kwargs)
    return LegacyModule131MigrationPlanner(
        LegacyModule131Paths.from_runtime_folder(root),
        selected,
    ).build_plan()


def event(selected, before, after, event_id, transition, previous="", **kwargs):
    return SandboxLifecycleEvent(
        event_id=event_id,
        event_time="2026-07-17T11:30:00+05:30",
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        before_state_hash=state_hash(before),
        after_state=after.to_dict(),
        transition=transition,
        option_side=kwargs.get("side", "CE_BUY"),
        option_symbol=kwargs.get("symbol", "NIFTY_PHASE4L_CE"),
        quantity=kwargs.get("quantity", 75),
        price=kwargs.get("price", 100.0),
        realized_pnl=kwargs.get("realized_pnl"),
        reason_code="PHASE4L_TEST",
        previous_event_hash=previous,
    )


def open_bundle(
    selected,
    *,
    held=False,
    side="CE_BUY",
    symbol="NIFTY_PHASE4L_CE",
    quantity=75,
    entry=100.0,
):
    initial = StrategyStateSnapshot.from_selection(
        selected, migration_complete=True
    )
    opened = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position={
            "option_side": side,
            "option_symbol": symbol,
            "quantity": quantity,
            "entry": entry,
        },
        last_event_id="open-1",
        migration_complete=True,
    )
    first = event(
        selected,
        initial,
        opened,
        "open-1",
        "FLAT->OPEN",
        side=side,
        symbol=symbol,
        quantity=quantity,
        price=entry,
    )
    if not held:
        return SandboxLifecycleBundle(
            selection=selected,
            current_state=opened,
            events=(first,),
        )
    held_state = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position={**dict(opened.position), "latest_price": 105.0},
        last_event_id="held-2",
        migration_complete=True,
    )
    second = event(
        selected,
        opened,
        held_state,
        "held-2",
        "OPEN->HELD",
        previous=first.event_hash,
        side=side,
        symbol=symbol,
        quantity=quantity,
        price=105.0,
    )
    return SandboxLifecycleBundle(
        selection=selected,
        current_state=held_state,
        events=(first, second),
    )


def flat_bundle(selected):
    initial = StrategyStateSnapshot.from_selection(
        selected, migration_complete=True
    )
    opened_bundle = open_bundle(selected)
    opened = opened_bundle.current_state
    first = opened_bundle.events[0]
    held = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position={**dict(opened.position), "latest_price": 105.0},
        last_event_id="held-2",
        migration_complete=True,
    )
    second = event(
        selected,
        opened,
        held,
        "held-2",
        "OPEN->HELD",
        previous=first.event_hash,
        price=105.0,
    )
    closed = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.CLOSED,
        position={**dict(held.position), "exit": 110.0, "realized_pnl": 750.0},
        last_event_id="closed-3",
        migration_complete=True,
    )
    third = event(
        selected,
        held,
        closed,
        "closed-3",
        "HELD->CLOSED",
        previous=second.event_hash,
        price=110.0,
        realized_pnl=750.0,
    )
    final = StrategyStateSnapshot.from_selection(
        selected,
        last_event_id="flat-4",
        migration_complete=True,
    )
    fourth = event(
        selected,
        closed,
        final,
        "flat-4",
        "CLOSED->FLAT",
        previous=third.event_hash,
        side="NO_TRADE",
        symbol="",
        quantity=0,
        price=None,
    )
    return SandboxLifecycleBundle(
        selection=selected,
        current_state=final,
        events=(first, second, third, fourth),
    )


def reconcile(selected, bundle, canonical):
    return reconcile_lifecycle_evidence(
        selection=selected,
        sandbox_bundle=bundle,
        canonical_plan=canonical,
    )


def test_flat_lifecycle_matches(tmp_path):
    selected = selection()
    result = reconcile(selected, flat_bundle(selected), plan(tmp_path, selected))
    assert result.status is LifecycleReconciliationStatus.MATCH_FLAT
    assert result.matched is True


def test_open_lifecycle_matches(tmp_path):
    selected = selection()
    result = reconcile(
        selected,
        open_bundle(selected),
        plan(tmp_path, selected, status="OPEN"),
    )
    assert result.status is LifecycleReconciliationStatus.MATCH_OPEN


def test_held_sandbox_semantically_matches_canonical_open(tmp_path):
    selected = selection()
    result = reconcile(
        selected,
        open_bundle(selected, held=True),
        plan(tmp_path, selected, status="OPEN"),
    )
    assert result.status is LifecycleReconciliationStatus.MATCH_OPEN
    assert result.sandbox.lifecycle == "OPEN"


def test_lifecycle_divergence_is_detected(tmp_path):
    selected = selection()
    result = reconcile(selected, open_bundle(selected), plan(tmp_path, selected))
    assert result.status is LifecycleReconciliationStatus.DIVERGED_LIFECYCLE


def test_option_side_divergence_is_detected(tmp_path):
    selected = selection()
    result = reconcile(
        selected,
        open_bundle(selected, side="PE_BUY"),
        plan(tmp_path, selected, status="OPEN"),
    )
    assert result.status is LifecycleReconciliationStatus.DIVERGED_POSITION
    assert "option_side" in result.differences[0]


def test_option_symbol_divergence_is_detected(tmp_path):
    selected = selection()
    result = reconcile(
        selected,
        open_bundle(selected, symbol="OTHER_CE"),
        plan(tmp_path, selected, status="OPEN"),
    )
    assert result.status is LifecycleReconciliationStatus.DIVERGED_POSITION


def test_quantity_divergence_is_detected(tmp_path):
    selected = selection()
    result = reconcile(
        selected,
        open_bundle(selected, quantity=150),
        plan(tmp_path, selected, status="OPEN"),
    )
    assert result.status is LifecycleReconciliationStatus.DIVERGED_POSITION


def test_entry_divergence_is_detected(tmp_path):
    selected = selection()
    result = reconcile(
        selected,
        open_bundle(selected, entry=101.0),
        plan(tmp_path, selected, status="OPEN"),
    )
    assert result.status is LifecycleReconciliationStatus.DIVERGED_POSITION


def test_ledger_balance_divergence_is_detected(tmp_path):
    selected = selection()
    result = reconcile(
        selected,
        flat_bundle(selected),
        plan(tmp_path, selected, cycles=2),
    )
    assert result.status is LifecycleReconciliationStatus.DIVERGED_LEDGER


def test_running_runtime_blocks_reconciliation(tmp_path):
    selected = selection()
    result = reconcile(
        selected,
        flat_bundle(selected),
        plan(tmp_path, selected, running=True),
    )
    assert result.status is LifecycleReconciliationStatus.BLOCKED_RUNTIME_RUNNING
    assert result.canonical is None


def test_missing_canonical_evidence_is_reported(tmp_path):
    selected = selection()
    canonical = LegacyModule131MigrationPlanner(
        LegacyModule131Paths.from_runtime_folder(tmp_path), selected
    ).build_plan()
    result = reconcile(selected, flat_bundle(selected), canonical)
    assert result.status is LifecycleReconciliationStatus.NO_CANONICAL_EVIDENCE


def test_corrupt_canonical_evidence_is_blocked(tmp_path):
    selected = selection()
    result = reconcile(
        selected,
        flat_bundle(selected),
        plan(tmp_path, selected, corrupt_state=True),
    )
    assert result.status is LifecycleReconciliationStatus.BLOCKED_CANONICAL_EVIDENCE


def test_canonical_plan_selection_mismatch_is_blocked(tmp_path):
    selected = selection()
    other = selection({"minimum_dte": 2})
    canonical = plan(tmp_path, other)
    with pytest.raises(LifecycleReconciliationError, match="canonical plan"):
        reconcile(selected, flat_bundle(selected), canonical)


def test_sandbox_bundle_selection_mismatch_is_blocked(tmp_path):
    selected = selection()
    other = selection({"minimum_dte": 2})
    with pytest.raises(LifecycleReconciliationError, match="sandbox bundle"):
        reconcile(selected, flat_bundle(other), plan(tmp_path, selected))


def test_reconciliation_hash_is_deterministic(tmp_path):
    selected = selection()
    canonical = plan(tmp_path, selected)
    first = reconcile(selected, flat_bundle(selected), canonical)
    second = reconcile(selected, flat_bundle(selected), canonical)
    assert first.reconciliation_hash == second.reconciliation_hash
    assert first.to_dict()["reconciliation_hash"] == first.reconciliation_hash
