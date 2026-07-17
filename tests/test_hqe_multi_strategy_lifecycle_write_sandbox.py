from __future__ import annotations

from dataclasses import replace

import pytest

from src.multi_strategy.activation import (
    ActivationPreflightStatus,
    DisabledActivationPreflightResult,
)
from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    build_current_smc_adapter,
    current_smc_manifest,
)
from src.multi_strategy.lifecycle_adapter import (
    DisabledCanonicalLifecycleAdapter,
    DisabledLifecyclePlanStatus,
)
from src.multi_strategy.lifecycle_write_sandbox import (
    GuardedLifecycleWritePermit,
    GuardedNamespacedLifecycleWriteSandbox,
    LifecycleWriteSandboxError,
    SandboxTransitionStatus,
)
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.one_active import DisabledOneActiveStrategySet
from src.multi_strategy.recovery import OfflineRestartRecoverySnapshot
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot


class OtherStrategy:
    def generate(self, context):
        return ()


def current_selection():
    manifest = current_smc_manifest()
    registry = StrategyRegistry(
        {CURRENT_SMC_IMPLEMENTATION_KEY: build_current_smc_adapter}
    )
    selected = StrategySelectionSnapshot.from_registration(
        registry.register(manifest, source="test:reviewed-current-smc")
    )
    return manifest, selected


def other_selection():
    key = "hqe.reviewed.other_phase4k_v1"
    manifest = StrategyManifest(
        strategy_id="other_phase4k",
        display_name="Other",
        strategy_version="1.0.0",
        description="other",
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
    registry = StrategyRegistry({key: lambda parameters: OtherStrategy()})
    return manifest, StrategySelectionSnapshot.from_registration(
        registry.register(manifest)
    )


def observation():
    payload = {
        "status": "STOPPED",
        "paper_only": True,
        "broker_execution": False,
    }
    return StableRuntimeObservation(
        observed_at="2026-07-17T10:30:00+05:30",
        runtime_status="STOPPED",
        runtime_pid=None,
        first_read=payload,
        second_read=dict(payload),
    )


def plan_and_selection(tmp_path):
    manifest, selected = current_selection()
    initial = StrategyStateSnapshot.from_selection(
        selected,
        migration_complete=True,
    )
    recovery = OfflineRestartRecoverySnapshot(
        selection=selected,
        state=initial,
        ledger_rows=(),
        recovery_payload={"mode": "PHASE4K_TEST"},
        migration_payload={"mode": "PHASE4K_TEST"},
        artifact_hashes={},
        namespace_directory=str(tmp_path / "canonical-evidence"),
    )
    observed = observation()
    preflight = DisabledActivationPreflightResult(
        status=ActivationPreflightStatus.READY_DISABLED,
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        recovery_snapshot_hash=recovery.snapshot_hash,
        operator_view_hash="phase4k-test-view",
        runtime_observation_hash=observed.observation_hash,
        blockers=(),
        minimum_cycles=3,
        observed_cycles=3,
        match_count=3,
        mismatch_count=0,
    )
    plan = DisabledCanonicalLifecycleAdapter().prepare(
        manifest=manifest,
        selection=selected,
        one_active=DisabledOneActiveStrategySet.build(selected, (selected,)),
        current_state=initial,
        recovery=recovery,
        preflight=preflight,
        runtime_observation=observed,
    )
    return plan, selected, initial


def sandbox(tmp_path):
    plan, selected, initial = plan_and_selection(tmp_path)
    root = tmp_path / "HQE_MULTI_STRATEGY_PHASE4K_SANDBOX_TEST"
    permit = GuardedLifecycleWritePermit.issue(
        plan=plan,
        selection=selected,
        sandbox_root=root,
    )
    store = GuardedNamespacedLifecycleWriteSandbox(
        permit=permit,
        selection=selected,
    )
    return store, permit, selected, initial


def open_state(selected, event_id="open-1"):
    return StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position={
            "option_side": "CE_BUY",
            "option_symbol": "NIFTY_PHASE4K_CE",
            "quantity": 75,
            "entry": 100.0,
        },
        last_event_id=event_id,
        migration_complete=True,
    )


def apply_open(store, selected, initial, event_id="open-1"):
    return store.apply_transition(
        before=initial,
        after=open_state(selected, event_id),
        event_id=event_id,
        event_time="2026-07-17T10:35:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4K_CE",
        quantity=75,
        price=100.0,
        reason_code="PHASE4K_OPEN",
    )


def test_permit_issued_for_reviewed_current_smc(tmp_path):
    plan, selected, _ = plan_and_selection(tmp_path)
    permit = GuardedLifecycleWritePermit.issue(
        plan=plan,
        selection=selected,
        sandbox_root=tmp_path / "HQE_MULTI_STRATEGY_PHASE4K_SANDBOX_A",
    )
    assert permit.sandbox_write_authorized is True
    assert permit.canonical_state_write_authorized is False
    assert permit.runtime_cutover_authorized is False


def test_permit_rejects_non_phase4k_root(tmp_path):
    plan, selected, _ = plan_and_selection(tmp_path)
    with pytest.raises(LifecycleWriteSandboxError, match="prefix"):
        GuardedLifecycleWritePermit.issue(
            plan=plan,
            selection=selected,
            sandbox_root=tmp_path / "unsafe-root",
        )


def test_permit_rejects_non_current_smc_selection(tmp_path):
    plan, _, _ = plan_and_selection(tmp_path)
    _, other = other_selection()
    mismatched_plan = replace(
        plan,
        strategy_id=other.strategy_id,
        strategy_version=other.strategy_version,
        implementation_key=other.implementation_key,
        selection_hash=other.selection_hash,
        manifest_fingerprint=other.manifest_fingerprint,
    )
    with pytest.raises(LifecycleWriteSandboxError, match="current SMC"):
        GuardedLifecycleWritePermit.issue(
            plan=mismatched_plan,
            selection=other,
            sandbox_root=tmp_path / "HQE_MULTI_STRATEGY_PHASE4K_SANDBOX_B",
        )


def test_permit_rejects_blocked_plan(tmp_path):
    plan, selected, _ = plan_and_selection(tmp_path)
    blocked = replace(
        plan,
        status=DisabledLifecyclePlanStatus.BLOCKED_EVIDENCE,
        blockers=("blocked",),
    )
    with pytest.raises(LifecycleWriteSandboxError, match="READY_DISABLED"):
        GuardedLifecycleWritePermit.issue(
            plan=blocked,
            selection=selected,
            sandbox_root=tmp_path / "HQE_MULTI_STRATEGY_PHASE4K_SANDBOX_C",
        )


def test_initialize_writes_only_namespaced_sandbox_files(tmp_path):
    store, _, _, initial = sandbox(tmp_path)
    bundle = store.initialize(initial)
    assert bundle.current_state.lifecycle is PositionLifecycle.FLAT
    assert store.bundle_path.exists()
    assert store.paths.selection.exists()
    assert store.paths.state.exists()
    assert store.paths.ledger.exists()
    assert set(path.name for path in store.paths.namespace_directory.iterdir()) == {
        "lifecycle_bundle.json",
        "selection.json",
        "state.json",
        "ledger.csv",
    }


def test_initialize_is_idempotent(tmp_path):
    store, _, _, initial = sandbox(tmp_path)
    first = store.initialize(initial)
    second = store.initialize(initial)
    assert first.bundle_hash == second.bundle_hash


def test_four_transition_cycle_is_applied_in_sandbox(tmp_path):
    store, _, selected, initial = sandbox(tmp_path)
    store.initialize(initial)
    opened = open_state(selected)
    first = apply_open(store, selected, initial)
    held = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position={**dict(opened.position), "latest_price": 105.0},
        last_event_id="held-2",
        migration_complete=True,
    )
    second = store.apply_transition(
        before=opened,
        after=held,
        event_id="held-2",
        event_time="2026-07-17T10:40:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4K_CE",
        quantity=75,
        price=105.0,
        reason_code="PHASE4K_HELD",
    )
    closed = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.CLOSED,
        position={**dict(held.position), "exit": 110.0, "realized_pnl": 750.0},
        last_event_id="closed-3",
        migration_complete=True,
    )
    third = store.apply_transition(
        before=held,
        after=closed,
        event_id="closed-3",
        event_time="2026-07-17T10:45:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4K_CE",
        quantity=75,
        price=110.0,
        realized_pnl=750.0,
        reason_code="PHASE4K_CLOSED",
    )
    final = StrategyStateSnapshot.from_selection(
        selected,
        last_event_id="flat-4",
        migration_complete=True,
    )
    fourth = store.apply_transition(
        before=closed,
        after=final,
        event_id="flat-4",
        event_time="2026-07-17T10:46:00+05:30",
        option_side="NO_TRADE",
        quantity=0,
        reason_code="PHASE4K_FLAT",
    )
    assert [first.status, second.status, third.status, fourth.status] == [
        SandboxTransitionStatus.APPLIED_SANDBOX,
    ] * 4
    bundle = store.load()
    assert bundle.current_state.lifecycle is PositionLifecycle.FLAT
    assert len(bundle.events) == 4
    assert [item.transition for item in bundle.events] == [
        "FLAT->OPEN",
        "OPEN->HELD",
        "HELD->CLOSED",
        "CLOSED->FLAT",
    ]


def test_stale_before_state_is_blocked(tmp_path):
    store, _, selected, initial = sandbox(tmp_path)
    store.initialize(initial)
    apply_open(store, selected, initial)
    with pytest.raises(LifecycleWriteSandboxError, match="stale"):
        apply_open(store, selected, initial, event_id="open-2")


def test_duplicate_event_id_is_blocked(tmp_path):
    store, _, selected, initial = sandbox(tmp_path)
    store.initialize(initial)
    opened = open_state(selected)
    apply_open(store, selected, initial)
    held = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position=dict(opened.position),
        last_event_id="open-1",
        migration_complete=True,
    )
    with pytest.raises(LifecycleWriteSandboxError, match="duplicate"):
        store.apply_transition(
            before=opened,
            after=held,
            event_id="open-1",
            event_time="2026-07-17T10:40:00+05:30",
            option_side="CE_BUY",
            option_symbol="NIFTY_PHASE4K_CE",
            quantity=75,
        )


def test_active_lock_blocks_concurrent_writer(tmp_path):
    store, _, selected, initial = sandbox(tmp_path)
    store.initialize(initial)
    store.lock_path.write_text("other", encoding="utf-8")
    with pytest.raises(LifecycleWriteSandboxError, match="lock"):
        apply_open(store, selected, initial)


def test_open_position_symbol_change_is_blocked(tmp_path):
    store, _, selected, initial = sandbox(tmp_path)
    store.initialize(initial)
    opened = open_state(selected)
    apply_open(store, selected, initial)
    held = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position={**dict(opened.position), "option_symbol": "CHANGED_CE"},
        last_event_id="held-2",
        migration_complete=True,
    )
    with pytest.raises(LifecycleWriteSandboxError, match="option_symbol"):
        store.apply_transition(
            before=opened,
            after=held,
            event_id="held-2",
            event_time="2026-07-17T10:40:00+05:30",
            option_side="CE_BUY",
            option_symbol="CHANGED_CE",
            quantity=75,
        )


def test_projection_failure_rolls_back_transaction(tmp_path, monkeypatch):
    store, _, selected, initial = sandbox(tmp_path)
    original = store.initialize(initial)

    def fail_projection(bundle):
        raise OSError("synthetic projection failure")

    monkeypatch.setattr(store, "_write_projection_files", fail_projection)
    with pytest.raises(LifecycleWriteSandboxError, match="rolled back"):
        apply_open(store, selected, initial)
    recovered = store.load()
    assert recovered.bundle_hash == original.bundle_hash
    assert recovered.current_state.lifecycle is PositionLifecycle.FLAT
