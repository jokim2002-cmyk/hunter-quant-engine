from __future__ import annotations

import json
from dataclasses import replace

import pytest

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    build_current_smc_adapter,
    current_smc_manifest,
)
from src.multi_strategy.lifecycle_journal import (
    LifecycleJournalError,
    SandboxLifecycleBundle,
    SandboxLifecycleEvent,
    read_bundle,
    state_hash,
    write_bundle_atomic,
)
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot


def selection():
    manifest = current_smc_manifest()
    registry = StrategyRegistry(
        {CURRENT_SMC_IMPLEMENTATION_KEY: build_current_smc_adapter}
    )
    return StrategySelectionSnapshot.from_registration(
        registry.register(manifest, source="test:reviewed-current-smc")
    )


def initial_state(selected):
    return StrategyStateSnapshot.from_selection(
        selected,
        migration_complete=True,
    )


def open_state(selected, event_id="open-1"):
    return StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position={
            "option_side": "CE_BUY",
            "option_symbol": "NIFTY_TEST_CE",
            "quantity": 75,
            "entry": 100.0,
        },
        last_event_id=event_id,
        migration_complete=True,
    )


def event(selected, before, after, *, event_id="open-1", previous=""):
    return SandboxLifecycleEvent(
        event_id=event_id,
        event_time="2026-07-17T10:30:00+05:30",
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        before_state_hash=state_hash(before),
        after_state=after.to_dict(),
        transition=f"{before.lifecycle.value}->{after.lifecycle.value}",
        option_side="CE_BUY",
        option_symbol="NIFTY_TEST_CE",
        quantity=75,
        price=100.0,
        realized_pnl=None,
        reason_code="TEST_OPEN",
        previous_event_hash=previous,
    )


def test_event_hash_is_deterministic():
    selected = selection()
    before = initial_state(selected)
    after = open_state(selected)
    first = event(selected, before, after)
    second = event(selected, before, after)
    assert first.event_hash == second.event_hash
    assert first.to_dict() == second.to_dict()


def test_event_rejects_invalid_transition():
    selected = selection()
    before = initial_state(selected)
    after = open_state(selected)
    with pytest.raises(LifecycleJournalError, match="unsupported"):
        replace(event(selected, before, after), transition="FLAT->HELD")


def test_event_requires_after_state_event_identity():
    selected = selection()
    before = initial_state(selected)
    after = open_state(selected, event_id="different")
    with pytest.raises(LifecycleJournalError, match="last_event_id"):
        event(selected, before, after, event_id="open-1")


def test_event_from_dict_blocks_tampered_event_hash():
    selected = selection()
    before = initial_state(selected)
    after = open_state(selected)
    payload = event(selected, before, after).to_dict()
    payload["event_hash"] = "0" * 64
    with pytest.raises(LifecycleJournalError, match="event_hash"):
        SandboxLifecycleEvent.from_dict(payload)


def test_empty_bundle_requires_flat_state():
    selected = selection()
    with pytest.raises(LifecycleJournalError, match="start FLAT"):
        SandboxLifecycleBundle(
            selection=selected,
            current_state=open_state(selected),
        )


def test_bundle_final_state_must_match_final_event():
    selected = selection()
    before = initial_state(selected)
    after = open_state(selected)
    item = event(selected, before, after)
    with pytest.raises(LifecycleJournalError, match="final event"):
        SandboxLifecycleBundle(
            selection=selected,
            current_state=before,
            events=(item,),
        )


def test_bundle_rejects_duplicate_event_ids():
    selected = selection()
    before = initial_state(selected)
    after = open_state(selected)
    first = event(selected, before, after)
    duplicate = replace(
        first,
        before_state_hash=first.after_state_hash,
        previous_event_hash=first.event_hash,
    )
    with pytest.raises(LifecycleJournalError, match="duplicate"):
        SandboxLifecycleBundle(
            selection=selected,
            current_state=after,
            events=(first, duplicate),
        )


def test_bundle_rejects_event_hash_chain_mismatch():
    selected = selection()
    before = initial_state(selected)
    after = open_state(selected)
    first = event(selected, before, after)
    flat = StrategyStateSnapshot.from_selection(
        selected,
        last_event_id="flat-2",
        migration_complete=True,
    )
    second = SandboxLifecycleEvent(
        event_id="flat-2",
        event_time="2026-07-17T10:35:00+05:30",
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        before_state_hash=first.after_state_hash,
        after_state=flat.to_dict(),
        transition="CLOSED->FLAT",
        option_side="NO_TRADE",
        option_symbol="",
        quantity=0,
        price=None,
        realized_pnl=None,
        reason_code="TEST",
        previous_event_hash="wrong",
    )
    with pytest.raises(LifecycleJournalError, match="hash chain"):
        SandboxLifecycleBundle(
            selection=selected,
            current_state=flat,
            events=(first, second),
        )


def test_bundle_hash_is_deterministic():
    selected = selection()
    bundle = SandboxLifecycleBundle(
        selection=selected,
        current_state=initial_state(selected),
    )
    assert bundle.bundle_hash == SandboxLifecycleBundle.from_dict(
        bundle.to_dict()
    ).bundle_hash


def test_atomic_bundle_round_trip(tmp_path):
    selected = selection()
    bundle = SandboxLifecycleBundle(
        selection=selected,
        current_state=initial_state(selected),
    )
    path = tmp_path / "bundle.json"
    write_bundle_atomic(path, bundle)
    assert read_bundle(path).to_dict() == bundle.to_dict()
    assert not list(tmp_path.glob("*.tmp"))


def test_read_bundle_blocks_tampered_bundle_hash(tmp_path):
    selected = selection()
    bundle = SandboxLifecycleBundle(
        selection=selected,
        current_state=initial_state(selected),
    )
    payload = bundle.to_dict()
    payload["bundle_hash"] = "f" * 64
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(LifecycleJournalError, match="bundle_hash"):
        read_bundle(path)


def test_bundle_rejects_canonical_execution_flags():
    selected = selection()
    with pytest.raises(LifecycleJournalError, match="canonical"):
        SandboxLifecycleBundle(
            selection=selected,
            current_state=initial_state(selected),
            canonical_runtime_connected=True,
        )
