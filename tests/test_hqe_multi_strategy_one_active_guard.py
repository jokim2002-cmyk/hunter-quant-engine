from __future__ import annotations

import pytest

from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.one_active import (
    DisabledOneActiveStrategySet,
    DisabledSwitchReviewStatus,
    OneActiveStrategyError,
    review_disabled_strategy_switch,
)
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot


class FakeStrategy:
    def generate(self, context):
        return ()


def selection(strategy_id: str) -> StrategySelectionSnapshot:
    key = f"hqe.reviewed.{strategy_id}_v1"
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


def observation(status: str) -> StableRuntimeObservation:
    payload = {
        "status": status,
        "paper_only": True,
        "broker_execution": False,
    }
    return StableRuntimeObservation(
        observed_at="2026-07-17T10:00:00+05:30",
        runtime_status=status,
        runtime_pid=100 if status == "RUNNING" else None,
        first_read=payload,
        second_read=dict(payload),
    )


def test_exactly_one_selection_builds_disabled_set():
    current = selection("one_active")
    active = DisabledOneActiveStrategySet.build(current, (current,))

    assert active.to_dict()["active_strategy_count"] == 1
    assert active.one_active_strategy_enforced is True
    assert active.activation_enabled is False
    assert active.runtime_connected is False


def test_zero_active_selection_is_rejected():
    current = selection("zero_active")
    with pytest.raises(OneActiveStrategyError, match="exactly one"):
        DisabledOneActiveStrategySet.build(current, ())


def test_multiple_active_selections_are_rejected():
    current = selection("multi_one")
    second = selection("multi_two")
    with pytest.raises(OneActiveStrategyError, match="exactly one"):
        DisabledOneActiveStrategySet.build(current, (current, second))


def test_active_selection_must_match_selected_strategy():
    current = selection("selected_one")
    other = selection("selected_two")
    with pytest.raises(OneActiveStrategyError, match="does not match"):
        DisabledOneActiveStrategySet.build(current, (other,))


def test_same_selection_is_disabled_noop():
    current = selection("same")
    state = StrategyStateSnapshot.from_selection(
        current,
        migration_complete=True,
    )
    result = review_disabled_strategy_switch(
        current_selection=current,
        requested_selection=current,
        current_state=state,
        runtime_observation=observation("RUNNING"),
    )

    assert result.status is DisabledSwitchReviewStatus.SAME_SELECTION_DISABLED
    assert result.blockers == ()
    assert result.switch_authorized is False


def test_flat_migrated_stopped_switch_is_review_ready_but_disabled():
    current = selection("flat_current")
    requested = selection("flat_requested")
    state = StrategyStateSnapshot.from_selection(
        current,
        migration_complete=True,
    )
    result = review_disabled_strategy_switch(
        current_selection=current,
        requested_selection=requested,
        current_state=state,
        runtime_observation=observation("STOPPED"),
    )

    assert result.status is DisabledSwitchReviewStatus.READY_FLAT_DISABLED
    assert result.blockers == ()
    assert result.switch_authorized is False
    assert result.selection_write_authorized is False


def test_running_runtime_blocks_switch():
    current = selection("running_current")
    requested = selection("running_requested")
    state = StrategyStateSnapshot.from_selection(
        current,
        migration_complete=True,
    )
    result = review_disabled_strategy_switch(
        current_selection=current,
        requested_selection=requested,
        current_state=state,
        runtime_observation=observation("RUNNING"),
    )

    assert result.status is DisabledSwitchReviewStatus.BLOCKED_RUNTIME_ACTIVE
    assert any("runtime" in item for item in result.blockers)


def test_open_position_blocks_switch():
    current = selection("open_current")
    requested = selection("open_requested")
    state = StrategyStateSnapshot.from_selection(
        current,
        lifecycle=PositionLifecycle.OPEN,
        position={
            "option_symbol": "NIFTY_TEST_CE",
            "option_side": "CE_BUY",
        },
        migration_complete=True,
    )
    result = review_disabled_strategy_switch(
        current_selection=current,
        requested_selection=requested,
        current_state=state,
        runtime_observation=observation("STOPPED"),
    )

    assert result.status is DisabledSwitchReviewStatus.BLOCKED_OPEN_POSITION
    assert any("OPEN or HELD" in item for item in result.blockers)


def test_incomplete_migration_blocks_switch():
    current = selection("migration_current")
    requested = selection("migration_requested")
    state = StrategyStateSnapshot.from_selection(current)
    result = review_disabled_strategy_switch(
        current_selection=current,
        requested_selection=requested,
        current_state=state,
        runtime_observation=observation("STOPPED"),
    )

    assert result.status is DisabledSwitchReviewStatus.BLOCKED_MIGRATION
    assert any("migration" in item for item in result.blockers)


def test_switch_review_hash_is_deterministic():
    current = selection("hash_current")
    requested = selection("hash_requested")
    state = StrategyStateSnapshot.from_selection(
        current,
        migration_complete=True,
    )
    first = review_disabled_strategy_switch(
        current_selection=current,
        requested_selection=requested,
        current_state=state,
        runtime_observation=observation("STOPPED"),
    )
    second = review_disabled_strategy_switch(
        current_selection=current,
        requested_selection=requested,
        current_state=state,
        runtime_observation=observation("STOPPED"),
    )

    assert first.to_dict() == second.to_dict()
    assert first.review_hash == second.review_hash
