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
from src.multi_strategy.lifecycle_reconciliation import (
    LifecycleReconciliationStatus,
    reconcile_lifecycle_evidence,
)
from src.multi_strategy.lifecycle_reconciliation_view import build_reconciliation_view
from src.multi_strategy.lifecycle_write_sandbox import (
    GuardedLifecycleWritePermit,
    GuardedNamespacedLifecycleWriteSandbox,
)
from src.multi_strategy.migration import (
    LEGACY_LEDGER_REQUIRED_COLUMNS,
    LegacyModule131MigrationPlanner,
    LegacyModule131Paths,
)
from src.multi_strategy.one_active import DisabledOneActiveStrategySet
from src.multi_strategy.recovery import OfflineRestartRecoverySnapshot
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot


def build_selection_and_plan(workspace: Path):
    manifest = current_smc_manifest()
    registry = StrategyRegistry(
        {CURRENT_SMC_IMPLEMENTATION_KEY: build_current_smc_adapter}
    )
    selected = StrategySelectionSnapshot.from_registration(
        registry.register(manifest, source="phase4l:reviewed-current-smc")
    )
    initial = StrategyStateSnapshot.from_selection(
        selected, migration_complete=True
    )
    recovery = OfflineRestartRecoverySnapshot(
        selection=selected,
        state=initial,
        ledger_rows=(),
        recovery_payload={"mode": "SYNTHETIC_PHASE4L"},
        migration_payload={"mode": "SYNTHETIC_PHASE4L"},
        artifact_hashes={},
        namespace_directory=str(workspace / "canonical-read-only-evidence"),
    )
    runtime_payload = {
        "status": "STOPPED",
        "paper_only": True,
        "broker_execution": False,
    }
    observation = StableRuntimeObservation(
        observed_at="2026-07-17T11:30:00+05:30",
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
        operator_view_hash="phase4l-dry-run-view",
        runtime_observation_hash=observation.observation_hash,
        blockers=(),
        minimum_cycles=3,
        observed_cycles=3,
        match_count=3,
        mismatch_count=0,
    )
    lifecycle_plan = DisabledCanonicalLifecycleAdapter().prepare(
        manifest=manifest,
        selection=selected,
        one_active=DisabledOneActiveStrategySet.build(selected, (selected,)),
        current_state=initial,
        recovery=recovery,
        preflight=preflight,
        runtime_observation=observation,
    )
    return selected, initial, lifecycle_plan


def build_sandbox_bundle(workspace: Path, selected, initial, lifecycle_plan):
    sandbox_root = workspace / "HQE_MULTI_STRATEGY_PHASE4K_SANDBOX_PHASE4L_INPUT"
    permit = GuardedLifecycleWritePermit.issue(
        plan=lifecycle_plan,
        selection=selected,
        sandbox_root=sandbox_root,
    )
    store = GuardedNamespacedLifecycleWriteSandbox(
        permit=permit,
        selection=selected,
    )
    store.initialize(initial)
    opened = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position={
            "option_side": "CE_BUY",
            "option_symbol": "NIFTY_PHASE4L_CE",
            "quantity": 75,
            "entry": 100.0,
        },
        last_event_id="phase4l-open-1",
        migration_complete=True,
    )
    store.apply_transition(
        before=initial,
        after=opened,
        event_id="phase4l-open-1",
        event_time="2026-07-17T11:31:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4L_CE",
        quantity=75,
        price=100.0,
        reason_code="PHASE4L_OPEN",
    )
    held = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.HELD,
        position={**dict(opened.position), "latest_price": 105.0},
        last_event_id="phase4l-held-2",
        migration_complete=True,
    )
    store.apply_transition(
        before=opened,
        after=held,
        event_id="phase4l-held-2",
        event_time="2026-07-17T11:32:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4L_CE",
        quantity=75,
        price=105.0,
        reason_code="PHASE4L_HELD",
    )
    closed = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.CLOSED,
        position={**dict(held.position), "exit": 110.0, "realized_pnl": 750.0},
        last_event_id="phase4l-closed-3",
        migration_complete=True,
    )
    store.apply_transition(
        before=held,
        after=closed,
        event_id="phase4l-closed-3",
        event_time="2026-07-17T11:33:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4L_CE",
        quantity=75,
        price=110.0,
        realized_pnl=750.0,
        reason_code="PHASE4L_CLOSED",
    )
    final = StrategyStateSnapshot.from_selection(
        selected,
        last_event_id="phase4l-flat-4",
        migration_complete=True,
    )
    store.apply_transition(
        before=closed,
        after=final,
        event_id="phase4l-flat-4",
        event_time="2026-07-17T11:34:00+05:30",
        option_side="NO_TRADE",
        quantity=0,
        reason_code="PHASE4L_FLAT",
    )
    return store.load(), store.bundle_path


def write_synthetic_canonical(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "HQE_PAPER_PRODUCT_RUNTIME.json").write_text(
        json.dumps(
            {
                "status": "STOPPED",
                "running": False,
                "paper_only": True,
                "broker_execution": False,
            }
        ),
        encoding="utf-8",
    )
    (root / "MODULE_131_POSITION_STATE.json").write_text(
        json.dumps(
            {
                "status": "FLAT",
                "paper_only": True,
                "broker_execution_allowed": False,
                "real_orders_allowed": False,
                "auto_trading_allowed": False,
                "real_money_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    rows = [
        {
            "timestamp": "2026-07-17T11:31:00+05:30",
            "module": "131",
            "event": "POSITION_OPENED",
            "side": "CE_BUY",
            "option_symbol": "NIFTY_PHASE4L_CE",
            "entry": "100.0",
            "stop_loss": "60.0",
            "target": "220.0",
            "exit_reason": "",
            "paper_pnl": "0.0",
            "paper_only": "true",
        },
        {
            "timestamp": "2026-07-17T11:33:00+05:30",
            "module": "131",
            "event": "POSITION_CLOSED",
            "side": "CE_BUY",
            "option_symbol": "NIFTY_PHASE4L_CE",
            "entry": "100.0",
            "stop_loss": "60.0",
            "target": "220.0",
            "exit_reason": "TARGET",
            "paper_pnl": "750.0",
            "paper_only": "true",
        },
    ]
    with (root / "MODULE_131_PAPER_LEDGER.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=LEGACY_LEDGER_REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def evidence_hashes(paths: LegacyModule131Paths):
    return {
        name: item.sha256
        for name, item in sorted(paths.evidence().items())
        if item.exists
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve(strict=False)
    workspace.mkdir(parents=True, exist_ok=True)

    selected, initial, lifecycle_plan = build_selection_and_plan(workspace)
    sandbox_bundle, sandbox_bundle_path = build_sandbox_bundle(
        workspace, selected, initial, lifecycle_plan
    )
    canonical_root = workspace / "SYNTHETIC_CANONICAL_MODULE131_READ_ONLY_EVIDENCE"
    write_synthetic_canonical(canonical_root)
    canonical_paths = LegacyModule131Paths.from_runtime_folder(canonical_root)
    before_hashes = evidence_hashes(canonical_paths)
    canonical_plan = LegacyModule131MigrationPlanner(
        canonical_paths, selected
    ).build_plan()

    matched = reconcile_lifecycle_evidence(
        selection=selected,
        sandbox_bundle=sandbox_bundle,
        canonical_plan=canonical_plan,
    )
    matched_view = build_reconciliation_view(matched)

    open_root = workspace / "HQE_MULTI_STRATEGY_PHASE4K_SANDBOX_PHASE4L_DIVERGED"
    open_permit = GuardedLifecycleWritePermit.issue(
        plan=lifecycle_plan,
        selection=selected,
        sandbox_root=open_root,
    )
    open_store = GuardedNamespacedLifecycleWriteSandbox(
        permit=open_permit, selection=selected
    )
    open_store.initialize(initial)
    open_state = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position={
            "option_side": "CE_BUY",
            "option_symbol": "NIFTY_PHASE4L_CE",
            "quantity": 75,
            "entry": 100.0,
        },
        last_event_id="phase4l-diverged-open",
        migration_complete=True,
    )
    open_store.apply_transition(
        before=initial,
        after=open_state,
        event_id="phase4l-diverged-open",
        event_time="2026-07-17T11:35:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4L_CE",
        quantity=75,
        price=100.0,
        reason_code="PHASE4L_DIVERGENCE_PROBE",
    )
    diverged = reconcile_lifecycle_evidence(
        selection=selected,
        sandbox_bundle=open_store.load(),
        canonical_plan=canonical_plan,
    )
    after_hashes = evidence_hashes(canonical_paths)

    payload = {
        "mode": "OFFLINE_READ_ONLY_LIFECYCLE_RECONCILIATION_DRY_RUN",
        "strategy_id": selected.strategy_id,
        "strategy_version": selected.strategy_version,
        "sandbox_bundle_path": str(sandbox_bundle_path),
        "sandbox_bundle_hash": sandbox_bundle.bundle_hash,
        "canonical_plan_hash": canonical_plan.plan_hash,
        "canonical_evidence_hashes_before": before_hashes,
        "canonical_evidence_hashes_after": after_hashes,
        "canonical_evidence_unchanged": before_hashes == after_hashes,
        "match_status": matched.status.value,
        "match_verified": matched.status is LifecycleReconciliationStatus.MATCH_FLAT,
        "match_reconciliation_hash": matched.reconciliation_hash,
        "operator_view_hash": matched_view.view_hash,
        "operator_recommendation": matched_view.recommendation,
        "divergence_status": diverged.status.value,
        "divergence_detected": diverged.status
        is LifecycleReconciliationStatus.DIVERGED_LIFECYCLE,
        "sandbox_files_written_by_reconciliation": False,
        "canonical_files_written_by_reconciliation": False,
        "strategy_switch_enabled": False,
        "lifecycle_write_enabled": False,
        "runtime_cutover_enabled": False,
        "broker_execution_performed": False,
        "real_money_used": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
