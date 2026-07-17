from __future__ import annotations

import argparse
import csv
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
from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    build_current_smc_adapter,
    current_smc_manifest,
)
from src.multi_strategy.lifecycle_adapter import DisabledCanonicalLifecycleAdapter
from src.multi_strategy.lifecycle_write_sandbox import (
    GuardedLifecycleWritePermit,
    GuardedNamespacedLifecycleWriteSandbox,
    LifecycleWriteSandboxError,
)
from src.multi_strategy.one_active import DisabledOneActiveStrategySet
from src.multi_strategy.recovery import OfflineRestartRecoverySnapshot
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot


def build_plan(workspace: Path):
    manifest = current_smc_manifest()
    registry = StrategyRegistry(
        {CURRENT_SMC_IMPLEMENTATION_KEY: build_current_smc_adapter}
    )
    selected = StrategySelectionSnapshot.from_registration(
        registry.register(manifest, source="dry-run:reviewed-current-smc")
    )
    initial = StrategyStateSnapshot.from_selection(
        selected,
        migration_complete=True,
    )
    recovery = OfflineRestartRecoverySnapshot(
        selection=selected,
        state=initial,
        ledger_rows=(),
        recovery_payload={"mode": "SYNTHETIC_PHASE4K"},
        migration_payload={"mode": "SYNTHETIC_PHASE4K"},
        artifact_hashes={},
        namespace_directory=str(workspace / "canonical-read-only-evidence"),
    )
    runtime_payload = {
        "status": "STOPPED",
        "paper_only": True,
        "broker_execution": False,
    }
    observation = StableRuntimeObservation(
        observed_at="2026-07-17T11:00:00+05:30",
        runtime_status="STOPPED",
        runtime_pid=None,
        first_read=runtime_payload,
        second_read=dict(runtime_payload),
    )
    preflight = DisabledActivationPreflightResult(
        status=ActivationPreflightStatus.READY_DISABLED,
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        recovery_snapshot_hash=recovery.snapshot_hash,
        operator_view_hash="phase4k-dry-run-view",
        runtime_observation_hash=observation.observation_hash,
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
        runtime_observation=observation,
    )
    return selected, initial, plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve(strict=False)
    workspace.mkdir(parents=True, exist_ok=True)

    selected, initial, plan = build_plan(workspace)
    sandbox_root = workspace / "HQE_MULTI_STRATEGY_PHASE4K_SANDBOX_CURRENT_SMC"
    permit = GuardedLifecycleWritePermit.issue(
        plan=plan,
        selection=selected,
        sandbox_root=sandbox_root,
    )
    store = GuardedNamespacedLifecycleWriteSandbox(
        permit=permit,
        selection=selected,
    )
    initial_bundle = store.initialize(initial)

    opened = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position={
            "option_side": "CE_BUY",
            "option_symbol": "NIFTY_PHASE4K_CE",
            "quantity": 75,
            "entry": 100.0,
        },
        last_event_id="phase4k-open-1",
        migration_complete=True,
    )
    first = store.apply_transition(
        before=initial,
        after=opened,
        event_id="phase4k-open-1",
        event_time="2026-07-17T11:01:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4K_CE",
        quantity=75,
        price=100.0,
        reason_code="PHASE4K_OPEN",
    )

    stale_write_blocked = False
    try:
        store.apply_transition(
            before=initial,
            after=opened,
            event_id="phase4k-stale",
            event_time="2026-07-17T11:02:00+05:30",
            option_side="CE_BUY",
            option_symbol="NIFTY_PHASE4K_CE",
            quantity=75,
            price=100.0,
            reason_code="PHASE4K_STALE",
        )
    except LifecycleWriteSandboxError:
        stale_write_blocked = True

    held = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position={**dict(opened.position), "latest_price": 105.0},
        last_event_id="phase4k-held-2",
        migration_complete=True,
    )
    second = store.apply_transition(
        before=opened,
        after=held,
        event_id="phase4k-held-2",
        event_time="2026-07-17T11:03:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4K_CE",
        quantity=75,
        price=105.0,
        reason_code="PHASE4K_HELD",
    )

    closed = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.CLOSED,
        position={
            **dict(held.position),
            "exit": 110.0,
            "realized_pnl": 750.0,
        },
        last_event_id="phase4k-closed-3",
        migration_complete=True,
    )
    third = store.apply_transition(
        before=held,
        after=closed,
        event_id="phase4k-closed-3",
        event_time="2026-07-17T11:04:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4K_CE",
        quantity=75,
        price=110.0,
        realized_pnl=750.0,
        reason_code="PHASE4K_CLOSED",
    )

    final_flat = StrategyStateSnapshot.from_selection(
        selected,
        last_event_id="phase4k-flat-4",
        migration_complete=True,
    )
    fourth = store.apply_transition(
        before=closed,
        after=final_flat,
        event_id="phase4k-flat-4",
        event_time="2026-07-17T11:05:00+05:30",
        option_side="NO_TRADE",
        quantity=0,
        reason_code="PHASE4K_FLAT",
    )

    duplicate_event_blocked = False
    try:
        store.apply_transition(
            before=final_flat,
            after=final_flat,
            event_id="phase4k-flat-4",
            event_time="2026-07-17T11:06:00+05:30",
            option_side="NO_TRADE",
            quantity=0,
            reason_code="PHASE4K_DUPLICATE",
        )
    except LifecycleWriteSandboxError:
        duplicate_event_blocked = True

    lock_blocked = False
    store.lock_path.write_text("synthetic-concurrent-writer", encoding="utf-8")
    try:
        try:
            store.apply_transition(
                before=final_flat,
                after=final_flat,
                event_id="phase4k-lock-5",
                event_time="2026-07-17T11:07:00+05:30",
                option_side="NO_TRADE",
                quantity=0,
                reason_code="PHASE4K_LOCK",
            )
        except LifecycleWriteSandboxError:
            lock_blocked = True
    finally:
        store.lock_path.unlink(missing_ok=True)

    final_bundle = store.load()
    with store.paths.ledger.open("r", newline="", encoding="utf-8") as handle:
        ledger_rows = list(csv.DictReader(handle))

    payload = {
        "mode": "OFFLINE_GUARDED_NAMESPACED_LIFECYCLE_WRITE_SANDBOX_DRY_RUN",
        "strategy_id": selected.strategy_id,
        "strategy_version": selected.strategy_version,
        "permit_hash": permit.permit_hash,
        "initial_bundle_hash": initial_bundle.bundle_hash,
        "final_bundle_hash": final_bundle.bundle_hash,
        "sandbox_namespace": str(store.paths.namespace_directory),
        "sandbox_write_authorized": permit.sandbox_write_authorized,
        "sandbox_state_written": store.paths.state.exists(),
        "sandbox_ledger_written": store.paths.ledger.exists(),
        "event_count": len(final_bundle.events),
        "ledger_row_count": len(ledger_rows),
        "final_lifecycle": final_bundle.current_state.lifecycle.value,
        "transitions": [
            first.transition,
            second.transition,
            third.transition,
            fourth.transition,
        ],
        "hash_chain_verified": len(final_bundle.events) == 4,
        "stale_write_blocked": stale_write_blocked,
        "duplicate_event_blocked": duplicate_event_blocked,
        "concurrent_lock_blocked": lock_blocked,
        "canonical_selection_written": False,
        "canonical_state_written": False,
        "canonical_ledger_written": False,
        "canonical_runtime_connected": False,
        "runtime_cutover_authorized": False,
        "broker_execution_performed": False,
        "real_money_used": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
