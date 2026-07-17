from __future__ import annotations

from dataclasses import replace

import pytest

from src.multi_strategy.activation import (
    ActivationPreflightStatus,
    DisabledActivationPreflightResult,
)
from src.multi_strategy.lifecycle_adapter import (
    DisabledCanonicalLifecycleAdapter,
    DisabledLifecyclePlanStatus,
    LifecycleAdapterError,
)
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.one_active import DisabledOneActiveStrategySet
from src.multi_strategy.recovery import (
    OfflineRestartRecoverySnapshot,
)
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot


class FakeStrategy:
    def generate(self, context):
        return ()


def manifest_and_selection(strategy_id: str = "lifecycle_test"):
    key = f"hqe.reviewed.{strategy_id}_v1"
    manifest = StrategyManifest(
        strategy_id=strategy_id,
        display_name=strategy_id,
        strategy_version="1.0.0",
        description="test lifecycle adapter",
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
    ).require_valid()
    registry = StrategyRegistry({key: lambda parameters: FakeStrategy()})
    selection = StrategySelectionSnapshot.from_registration(
        registry.register(manifest)
    )
    return manifest, selection


def observation(status: str = "STOPPED") -> StableRuntimeObservation:
    payload = {
        "status": status,
        "paper_only": True,
        "broker_execution": False,
    }
    return StableRuntimeObservation(
        observed_at="2026-07-17T10:15:00+05:30",
        runtime_status=status,
        runtime_pid=900 if status == "RUNNING" else None,
        first_read=payload,
        second_read=dict(payload),
    )


def evidence(*, status: str = "STOPPED", preflight_ready: bool = True):
    manifest, selected = manifest_and_selection()
    recovered_state = StrategyStateSnapshot.from_selection(
        selected,
        migration_complete=True,
    )
    recovery = OfflineRestartRecoverySnapshot(
        selection=selected,
        state=recovered_state,
        ledger_rows=(),
        recovery_payload={"mode": "test"},
        migration_payload={"mode": "test"},
        artifact_hashes={},
        namespace_directory="D:/offline/strategies/lifecycle_test",
    )
    runtime = observation(status)
    preflight_status = (
        ActivationPreflightStatus.READY_DISABLED
        if preflight_ready
        else ActivationPreflightStatus.BLOCKED_EVIDENCE
    )
    blockers = () if preflight_ready else ("test evidence blocker",)
    preflight = DisabledActivationPreflightResult(
        status=preflight_status,
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        recovery_snapshot_hash=recovery.snapshot_hash,
        operator_view_hash="operator-view-hash",
        runtime_observation_hash=runtime.observation_hash,
        blockers=blockers,
        minimum_cycles=3,
        observed_cycles=3,
        match_count=3,
        mismatch_count=0,
    )
    one_active = DisabledOneActiveStrategySet.build(selected, (selected,))
    return manifest, selected, recovered_state, recovery, preflight, runtime, one_active


def prepare(**kwargs):
    (
        manifest,
        selected,
        state,
        recovery,
        preflight,
        runtime,
        one_active,
    ) = evidence(
        status=kwargs.pop("status", "STOPPED"),
        preflight_ready=kwargs.pop("preflight_ready", True),
    )
    state = kwargs.pop("state", state)
    assert not kwargs
    result = DisabledCanonicalLifecycleAdapter().prepare(
        manifest=manifest,
        selection=selected,
        one_active=one_active,
        current_state=state,
        recovery=recovery,
        preflight=preflight,
        runtime_observation=runtime,
    )
    return result, selected


def position(side: str = "CE_BUY", symbol: str = "NIFTY_TEST_CE"):
    return {
        "option_side": side,
        "option_symbol": symbol,
        "quantity": 75,
        "entry": 100.0,
    }


def test_ready_plan_remains_fully_disabled():
    result, _ = prepare()

    assert result.status is DisabledLifecyclePlanStatus.READY_DISABLED
    assert result.active_strategy_count == 1
    assert result.one_active_strategy_enforced is True
    assert result.activation_authorized is False
    assert result.lifecycle_write_authorized is False
    assert result.state_write_authorized is False
    assert result.ledger_write_authorized is False
    assert result.runtime_connected is False
    assert result.runtime_cutover_authorized is False
    assert result.broker_execution_authorized is False
    assert result.real_money_authorized is False


def test_running_runtime_blocks_plan():
    result, _ = prepare(status="RUNNING")

    assert result.status is DisabledLifecyclePlanStatus.BLOCKED_RUNTIME_ACTIVE
    assert any("STOPPED or NOT_FOUND" in item for item in result.blockers)


def test_blocked_preflight_blocks_plan():
    result, _ = prepare(preflight_ready=False)

    assert result.status is DisabledLifecyclePlanStatus.BLOCKED_EVIDENCE
    assert any("preflight" in item for item in result.blockers)


def test_open_current_position_blocks_plan():
    _, selected = prepare()
    open_state = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position=position(),
        migration_complete=True,
    )
    result, _ = prepare(state=open_state)

    assert result.status is DisabledLifecyclePlanStatus.BLOCKED_OPEN_POSITION
    assert any("OPEN or HELD" in item for item in result.blockers)


def test_incomplete_migration_blocks_plan():
    _, selected = prepare()
    state = StrategyStateSnapshot.from_selection(selected)
    result, _ = prepare(state=state)

    assert result.status is DisabledLifecyclePlanStatus.BLOCKED_EVIDENCE
    assert any("migration" in item for item in result.blockers)


def test_manifest_identity_mismatch_fails_closed():
    manifest, selected, state, recovery, preflight, runtime, one_active = evidence()
    changed = replace(manifest, display_name="Changed")

    with pytest.raises(LifecycleAdapterError, match="fingerprint"):
        DisabledCanonicalLifecycleAdapter().prepare(
            manifest=changed,
            selection=selected,
            one_active=one_active,
            current_state=state,
            recovery=recovery,
            preflight=preflight,
            runtime_observation=runtime,
        )


def test_plan_hash_is_deterministic():
    first, _ = prepare()
    second, _ = prepare()

    assert first.to_dict() == second.to_dict()
    assert first.plan_hash == second.plan_hash


def test_flat_to_open_projection_is_allowed_but_not_written():
    _, selected = prepare()
    before = StrategyStateSnapshot.from_selection(
        selected,
        migration_complete=True,
    )
    after = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position=position(),
        last_event_id="open-1",
        migration_complete=True,
    )
    projected = DisabledCanonicalLifecycleAdapter().project_transition(
        selection=selected,
        before=before,
        after=after,
    )

    assert projected.allowed is True
    assert projected.transition == "FLAT->OPEN"
    assert projected.state_write_authorized is False
    assert projected.ledger_write_authorized is False


def test_open_to_held_projection_preserves_position_identity():
    _, selected = prepare()
    before = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position=position(),
        last_event_id="open-1",
        migration_complete=True,
    )
    after = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position={**position(), "latest_price": 105.0},
        last_event_id="held-1",
        migration_complete=True,
    )
    projected = DisabledCanonicalLifecycleAdapter().project_transition(
        selection=selected,
        before=before,
        after=after,
    )

    assert projected.allowed is True
    assert projected.transition == "OPEN->HELD"


def test_held_to_closed_projection_is_allowed():
    _, selected = prepare()
    before = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position=position(),
        last_event_id="held-1",
        migration_complete=True,
    )
    after = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.CLOSED,
        position={**position(), "realized_pnl": 750.0},
        last_event_id="close-1",
        migration_complete=True,
    )
    projected = DisabledCanonicalLifecycleAdapter().project_transition(
        selection=selected,
        before=before,
        after=after,
    )

    assert projected.allowed is True
    assert projected.transition == "HELD->CLOSED"


def test_closed_to_flat_projection_is_allowed():
    _, selected = prepare()
    before = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.CLOSED,
        position={**position(), "realized_pnl": 750.0},
        last_event_id="close-1",
        migration_complete=True,
    )
    after = StrategyStateSnapshot.from_selection(
        selected,
        last_event_id="close-1",
        migration_complete=True,
    )
    projected = DisabledCanonicalLifecycleAdapter().project_transition(
        selection=selected,
        before=before,
        after=after,
    )

    assert projected.allowed is True
    assert projected.transition == "CLOSED->FLAT"


def test_flat_to_held_projection_is_blocked():
    _, selected = prepare()
    before = StrategyStateSnapshot.from_selection(
        selected,
        migration_complete=True,
    )
    after = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position=position(),
        migration_complete=True,
    )
    projected = DisabledCanonicalLifecycleAdapter().project_transition(
        selection=selected,
        before=before,
        after=after,
    )

    assert projected.allowed is False
    assert any("FLAT->HELD" in item for item in projected.blockers)


def test_open_position_symbol_change_is_blocked():
    _, selected = prepare()
    before = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position=position(),
        migration_complete=True,
    )
    after = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position=position(symbol="NIFTY_OTHER_CE"),
        migration_complete=True,
    )
    projected = DisabledCanonicalLifecycleAdapter().project_transition(
        selection=selected,
        before=before,
        after=after,
    )

    assert projected.allowed is False
    assert any("option_symbol" in item for item in projected.blockers)


def test_transition_state_identity_mismatch_fails_closed():
    _, selected = prepare()
    _, other = manifest_and_selection("other_lifecycle")
    before = StrategyStateSnapshot.from_selection(
        selected,
        migration_complete=True,
    )
    after = StrategyStateSnapshot.from_selection(
        other,
        migration_complete=True,
    )

    with pytest.raises(LifecycleAdapterError, match="after state"):
        DisabledCanonicalLifecycleAdapter().project_transition(
            selection=selected,
            before=before,
            after=after,
        )
