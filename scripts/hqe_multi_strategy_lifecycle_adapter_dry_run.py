from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.multi_strategy.activation import (
    ActivationPreflightStatus,
    DisabledActivationPreflightResult,
)
from src.multi_strategy.lifecycle_adapter import DisabledCanonicalLifecycleAdapter
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.one_active import (
    DisabledOneActiveStrategySet,
    OneActiveStrategyError,
    review_disabled_strategy_switch,
)
from src.multi_strategy.recovery import OfflineRestartRecoverySnapshot
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot


class DryRunStrategy:
    def generate(self, context):
        return ()


def build_selection(strategy_id: str) -> tuple[StrategyManifest, StrategySelectionSnapshot]:
    implementation_key = f"hqe.reviewed.{strategy_id}_v1"
    manifest = StrategyManifest(
        strategy_id=strategy_id,
        display_name=strategy_id.replace("_", " ").title(),
        strategy_version="1.0.0",
        description="Synthetic reviewed lifecycle dry-run strategy.",
        implementation_key=implementation_key,
        supported_instruments=("NIFTY_INDEX_OPTION_BUY",),
        required_timeframe="5m",
        required_data_columns=("close",),
        warmup_bars=0,
        parameters=(),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    ).require_valid()
    registry = StrategyRegistry(
        {implementation_key: lambda parameters: DryRunStrategy()}
    )
    selected = StrategySelectionSnapshot.from_registration(
        registry.register(manifest, source="dry-run:reviewed")
    )
    return manifest, selected


def runtime_observation(status: str) -> StableRuntimeObservation:
    payload = {
        "status": status,
        "paper_only": True,
        "broker_execution": False,
    }
    return StableRuntimeObservation(
        observed_at="2026-07-17T10:30:00+05:30",
        runtime_status=status,
        runtime_pid=711 if status == "RUNNING" else None,
        first_read=payload,
        second_read=dict(payload),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve(strict=False)
    workspace.mkdir(parents=True, exist_ok=True)

    manifest, selected = build_selection("phase4j_current")
    _, requested = build_selection("phase4j_requested")
    one_active = DisabledOneActiveStrategySet.build(selected, (selected,))

    recovered_state = StrategyStateSnapshot.from_selection(
        selected,
        migration_complete=True,
    )
    recovery = OfflineRestartRecoverySnapshot(
        selection=selected,
        state=recovered_state,
        ledger_rows=(),
        recovery_payload={"mode": "SYNTHETIC_PHASE4J"},
        migration_payload={"mode": "SYNTHETIC_PHASE4J"},
        artifact_hashes={},
        namespace_directory=str(workspace / "strategies" / selected.strategy_id),
    )
    stopped = runtime_observation("STOPPED")
    preflight = DisabledActivationPreflightResult(
        status=ActivationPreflightStatus.READY_DISABLED,
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        recovery_snapshot_hash=recovery.snapshot_hash,
        operator_view_hash="phase4j-operator-view",
        runtime_observation_hash=stopped.observation_hash,
        blockers=(),
        minimum_cycles=3,
        observed_cycles=3,
        match_count=3,
        mismatch_count=0,
    )

    adapter = DisabledCanonicalLifecycleAdapter()
    plan = adapter.prepare(
        manifest=manifest,
        selection=selected,
        one_active=one_active,
        current_state=recovered_state,
        recovery=recovery,
        preflight=preflight,
        runtime_observation=stopped,
    )

    open_state = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position={
            "option_side": "CE_BUY",
            "option_symbol": "NIFTY_SYNTHETIC_CE",
            "quantity": 75,
            "entry": 100.0,
        },
        last_event_id="phase4j-open",
        migration_complete=True,
    )
    held_state = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position={
            "option_side": "CE_BUY",
            "option_symbol": "NIFTY_SYNTHETIC_CE",
            "quantity": 75,
            "entry": 100.0,
            "latest_price": 105.0,
        },
        last_event_id="phase4j-held",
        migration_complete=True,
    )
    closed_state = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.CLOSED,
        position={
            "option_side": "CE_BUY",
            "option_symbol": "NIFTY_SYNTHETIC_CE",
            "quantity": 75,
            "entry": 100.0,
            "exit": 110.0,
            "realized_pnl": 750.0,
        },
        last_event_id="phase4j-closed",
        migration_complete=True,
    )
    final_flat = StrategyStateSnapshot.from_selection(
        selected,
        last_event_id="phase4j-closed",
        migration_complete=True,
    )

    projections = (
        adapter.project_transition(
            selection=selected,
            before=recovered_state,
            after=open_state,
        ),
        adapter.project_transition(
            selection=selected,
            before=open_state,
            after=held_state,
        ),
        adapter.project_transition(
            selection=selected,
            before=held_state,
            after=closed_state,
        ),
        adapter.project_transition(
            selection=selected,
            before=closed_state,
            after=final_flat,
        ),
    )

    open_switch = review_disabled_strategy_switch(
        current_selection=selected,
        requested_selection=requested,
        current_state=held_state,
        runtime_observation=stopped,
    )
    flat_switch = review_disabled_strategy_switch(
        current_selection=selected,
        requested_selection=requested,
        current_state=final_flat,
        runtime_observation=stopped,
    )

    multiple_active_blocked = False
    try:
        DisabledOneActiveStrategySet.build(selected, (selected, requested))
    except OneActiveStrategyError:
        multiple_active_blocked = True

    payload = {
        "mode": "OFFLINE_DISABLED_ONE_ACTIVE_LIFECYCLE_ADAPTER_DRY_RUN",
        "plan_status": plan.status.value,
        "plan_hash": plan.plan_hash,
        "active_strategy_count": plan.active_strategy_count,
        "one_active_strategy_enforced": plan.one_active_strategy_enforced,
        "multiple_active_blocked": multiple_active_blocked,
        "canonical_lifecycle_stages": [
            "FLAT",
            "OPEN",
            "HELD",
            "CLOSED",
        ],
        "transition_projections": [
            {
                "transition": item.transition,
                "allowed": item.allowed,
                "write_authorized": item.state_write_authorized,
            }
            for item in projections
        ],
        "open_position_switch_status": open_switch.status.value,
        "open_position_switch_blocked": bool(open_switch.blockers),
        "flat_switch_review_status": flat_switch.status.value,
        "switch_authorized": flat_switch.switch_authorized,
        "activation_authorized": plan.activation_authorized,
        "selection_write_authorized": plan.selection_write_authorized,
        "lifecycle_write_authorized": plan.lifecycle_write_authorized,
        "state_write_authorized": plan.state_write_authorized,
        "ledger_write_authorized": plan.ledger_write_authorized,
        "canonical_runtime_connected": plan.runtime_connected,
        "runtime_cutover_authorized": plan.runtime_cutover_authorized,
        "broker_execution_authorized": plan.broker_execution_authorized,
        "real_money_authorized": plan.real_money_authorized,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
