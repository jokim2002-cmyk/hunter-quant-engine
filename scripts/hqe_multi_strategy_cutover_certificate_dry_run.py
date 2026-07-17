from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.hqe_multi_strategy_lifecycle_reconciliation_dry_run import (
    build_sandbox_bundle,
    build_selection_and_plan,
    evidence_hashes,
    write_synthetic_canonical,
)
from src.multi_strategy.cutover_certificate import (
    DisabledCutoverCertificateStatus,
    build_disabled_cutover_readiness_certificate,
)
from src.multi_strategy.cutover_certificate_view import (
    build_cutover_certificate_view,
)
from src.multi_strategy.lifecycle_adapter import DisabledLifecyclePlanStatus
from src.multi_strategy.lifecycle_reconciliation import (
    LifecycleReconciliationStatus,
    LifecycleSemanticObservation,
    ReadOnlyLifecycleReconciliation,
    reconcile_lifecycle_evidence,
)
from src.multi_strategy.lifecycle_reconciliation_view import (
    build_reconciliation_view,
)
from src.multi_strategy.lifecycle_write_sandbox import (
    GuardedLifecycleWritePermit,
    GuardedNamespacedLifecycleWriteSandbox,
)
from src.multi_strategy.migration import (
    LegacyModule131MigrationPlanner,
    LegacyModule131Paths,
)
from src.multi_strategy.one_active import DisabledOneActiveStrategySet
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot


def open_observation() -> LifecycleSemanticObservation:
    return LifecycleSemanticObservation(
        lifecycle="OPEN",
        opened_count=1,
        closed_count=0,
        unmatched_open_count=1,
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4M_CE",
        quantity=75,
        entry=100.0,
    )


def build_open_match(selected, matched):
    observation = open_observation()
    return ReadOnlyLifecycleReconciliation(
        status=LifecycleReconciliationStatus.MATCH_OPEN,
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        sandbox_bundle_hash="phase4m-open-bundle",
        canonical_plan_hash=matched.canonical_plan_hash,
        sandbox=observation,
        canonical=observation,
        canonical_evidence_hashes=matched.canonical_evidence_hashes,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve(strict=False)
    workspace.mkdir(parents=True, exist_ok=True)

    selected, initial, lifecycle_plan = build_selection_and_plan(workspace)
    one_active = DisabledOneActiveStrategySet.build(selected, (selected,))
    sandbox_bundle, _sandbox_path = build_sandbox_bundle(
        workspace,
        selected,
        initial,
        lifecycle_plan,
    )

    canonical_root = workspace / "SYNTHETIC_CANONICAL_MODULE131_READ_ONLY_EVIDENCE"
    write_synthetic_canonical(canonical_root)
    canonical_paths = LegacyModule131Paths.from_runtime_folder(canonical_root)
    before_hashes = evidence_hashes(canonical_paths)
    canonical_plan = LegacyModule131MigrationPlanner(
        canonical_paths,
        selected,
    ).build_plan()

    matched = reconcile_lifecycle_evidence(
        selection=selected,
        sandbox_bundle=sandbox_bundle,
        canonical_plan=canonical_plan,
    )
    matched_view = build_reconciliation_view(matched)
    ready = build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=one_active,
        lifecycle_plan=lifecycle_plan,
        reconciliation=matched,
        reconciliation_view=matched_view,
    )
    ready_view = build_cutover_certificate_view(ready)

    open_match = build_open_match(selected, matched)
    open_certificate = build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=one_active,
        lifecycle_plan=lifecycle_plan,
        reconciliation=open_match,
        reconciliation_view=build_reconciliation_view(open_match),
    )

    open_root = workspace / "HQE_MULTI_STRATEGY_PHASE4K_SANDBOX_PHASE4M_DIVERGED"
    open_permit = GuardedLifecycleWritePermit.issue(
        plan=lifecycle_plan,
        selection=selected,
        sandbox_root=open_root,
    )
    open_store = GuardedNamespacedLifecycleWriteSandbox(
        permit=open_permit,
        selection=selected,
    )
    open_store.initialize(initial)
    open_state = StrategyStateSnapshot.from_selection(
        selected,
        lifecycle=PositionLifecycle.OPEN,
        position={
            "option_side": "CE_BUY",
            "option_symbol": "NIFTY_PHASE4M_CE",
            "quantity": 75,
            "entry": 100.0,
        },
        last_event_id="phase4m-diverged-open",
        migration_complete=True,
    )
    open_store.apply_transition(
        before=initial,
        after=open_state,
        event_id="phase4m-diverged-open",
        event_time="2026-07-17T12:10:00+05:30",
        option_side="CE_BUY",
        option_symbol="NIFTY_PHASE4M_CE",
        quantity=75,
        price=100.0,
        reason_code="PHASE4M_DIVERGENCE_PROBE",
    )
    diverged = reconcile_lifecycle_evidence(
        selection=selected,
        sandbox_bundle=open_store.load(),
        canonical_plan=canonical_plan,
    )
    divergence_certificate = build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=one_active,
        lifecycle_plan=lifecycle_plan,
        reconciliation=diverged,
        reconciliation_view=build_reconciliation_view(diverged),
    )

    identity_view = replace(
        matched_view,
        reconciliation_hash="phase4m-invalid-reconciliation-hash",
    )
    identity_certificate = build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=one_active,
        lifecycle_plan=lifecycle_plan,
        reconciliation=matched,
        reconciliation_view=identity_view,
    )

    runtime_plan = replace(
        lifecycle_plan,
        status=DisabledLifecyclePlanStatus.BLOCKED_RUNTIME_ACTIVE,
        blockers=("canonical runtime is active",),
    )
    runtime_certificate = build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=one_active,
        lifecycle_plan=runtime_plan,
        reconciliation=matched,
        reconciliation_view=matched_view,
    )

    after_hashes = evidence_hashes(canonical_paths)
    payload = {
        "mode": "OFFLINE_DISABLED_CUTOVER_READINESS_CERTIFICATE_DRY_RUN",
        "strategy_id": selected.strategy_id,
        "strategy_version": selected.strategy_version,
        "ready_status": ready.status.value,
        "human_review_ready": ready.human_review_ready,
        "certificate_hash": ready.certificate_hash,
        "certificate_view_hash": ready_view.view_hash,
        "operator_recommendation": ready_view.recommendation,
        "open_probe_status": open_certificate.status.value,
        "divergence_probe_status": divergence_certificate.status.value,
        "identity_probe_status": identity_certificate.status.value,
        "runtime_probe_status": runtime_certificate.status.value,
        "canonical_evidence_hashes_before": before_hashes,
        "canonical_evidence_hashes_after": after_hashes,
        "canonical_evidence_unchanged": before_hashes == after_hashes,
        "certificate_file_written": False,
        "canonical_files_written_by_certificate": False,
        "sandbox_files_written_by_certificate": False,
        "activation_authorized": False,
        "strategy_switch_authorized": False,
        "lifecycle_write_authorized": False,
        "state_write_authorized": False,
        "ledger_write_authorized": False,
        "runtime_connection_authorized": False,
        "runtime_cutover_authorized": False,
        "broker_execution_performed": False,
        "real_money_used": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
