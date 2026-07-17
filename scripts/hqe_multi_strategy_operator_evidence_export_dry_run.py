from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.hqe_multi_strategy_cutover_certificate_dry_run import (
    build_selection_and_plan,
    build_sandbox_bundle,
    evidence_hashes,
    write_synthetic_canonical,
)
from src.multi_strategy.cutover_certificate import (
    build_disabled_cutover_readiness_certificate,
)
from src.multi_strategy.cutover_certificate_view import (
    build_cutover_certificate_view,
)
from src.multi_strategy.evidence_bundle_export import (
    EvidenceBundleExportError,
    export_operator_evidence_bundle,
    verify_operator_evidence_bundle,
)
from src.multi_strategy.lifecycle_reconciliation import (
    LifecycleReconciliationStatus,
    ReadOnlyLifecycleReconciliation,
    reconcile_lifecycle_evidence,
)
from src.multi_strategy.lifecycle_reconciliation_view import (
    build_reconciliation_view,
)
from src.multi_strategy.migration import (
    LegacyModule131MigrationPlanner,
    LegacyModule131Paths,
)
from src.multi_strategy.one_active import DisabledOneActiveStrategySet
from src.multi_strategy.operator_cutover_checklist import (
    build_operator_cutover_checklist,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve(strict=False)
    workspace.mkdir(parents=True, exist_ok=True)

    selected, initial, lifecycle_plan = build_selection_and_plan(workspace)
    one_active = DisabledOneActiveStrategySet.build(selected, (selected,))
    sandbox_bundle, _ = build_sandbox_bundle(
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
    reconciliation = reconcile_lifecycle_evidence(
        selection=selected,
        sandbox_bundle=sandbox_bundle,
        canonical_plan=canonical_plan,
    )
    reconciliation_view = build_reconciliation_view(reconciliation)
    certificate = build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=one_active,
        lifecycle_plan=lifecycle_plan,
        reconciliation=reconciliation,
        reconciliation_view=reconciliation_view,
    )
    certificate_view = build_cutover_certificate_view(certificate)
    checklist = build_operator_cutover_checklist(certificate, certificate_view)

    export_root = workspace / "HQE_MULTI_STRATEGY_PHASE4N_REVIEW_EXPORT"
    manifest, bundle_path = export_operator_evidence_bundle(
        output_root=export_root,
        export_id="current-smc-flat-review",
        certificate=certificate,
        view=certificate_view,
        checklist=checklist,
    )
    repeated, repeated_path = export_operator_evidence_bundle(
        output_root=export_root,
        export_id="current-smc-flat-review",
        certificate=certificate,
        view=certificate_view,
        checklist=checklist,
    )
    verified = verify_operator_evidence_bundle(bundle_path)

    tamper_path = export_root / "tamper-probe"
    shutil.copytree(bundle_path, tamper_path)
    certificate_file = tamper_path / "cutover_certificate.json"
    certificate_file.write_text("{}\n", encoding="utf-8")
    tamper_blocked = False
    try:
        verify_operator_evidence_bundle(tamper_path)
    except EvidenceBundleExportError:
        tamper_blocked = True

    blocked_reconciliation = ReadOnlyLifecycleReconciliation(
        status=LifecycleReconciliationStatus.DIVERGED_LIFECYCLE,
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        selection_hash=selected.selection_hash,
        sandbox_bundle_hash=reconciliation.sandbox_bundle_hash,
        canonical_plan_hash=reconciliation.canonical_plan_hash,
        sandbox=reconciliation.sandbox,
        canonical=reconciliation.canonical,
        canonical_evidence_hashes=reconciliation.canonical_evidence_hashes,
        differences=("phase4n deliberate divergence",),
    )
    blocked_certificate = build_disabled_cutover_readiness_certificate(
        selection=selected,
        one_active=one_active,
        lifecycle_plan=lifecycle_plan,
        reconciliation=blocked_reconciliation,
        reconciliation_view=build_reconciliation_view(blocked_reconciliation),
    )
    blocked_view = build_cutover_certificate_view(blocked_certificate)
    blocked_checklist = build_operator_cutover_checklist(
        blocked_certificate,
        blocked_view,
    )
    blocked_export_rejected = False
    try:
        export_operator_evidence_bundle(
            output_root=export_root,
            export_id="blocked-review",
            certificate=blocked_certificate,
            view=blocked_view,
            checklist=blocked_checklist,
        )
    except EvidenceBundleExportError:
        blocked_export_rejected = True

    unsafe_path_blocked = False
    try:
        export_operator_evidence_bundle(
            output_root=workspace / "UNSAFE_EXPORT_PATH",
            export_id="unsafe-review",
            certificate=certificate,
            view=certificate_view,
            checklist=checklist,
        )
    except EvidenceBundleExportError:
        unsafe_path_blocked = True

    after_hashes = evidence_hashes(canonical_paths)
    payload = {
        "mode": "OFFLINE_READ_ONLY_OPERATOR_CHECKLIST_EVIDENCE_EXPORT_DRY_RUN",
        "strategy_id": selected.strategy_id,
        "strategy_version": selected.strategy_version,
        "checklist_status": checklist.status.value,
        "checklist_hash": checklist.checklist_hash,
        "checklist_item_count": len(checklist.items),
        "all_checklist_items_passed": all(item.passed for item in checklist.items),
        "export_status": manifest.status.value,
        "repeated_export_status": repeated.status.value,
        "manifest_hash": manifest.manifest_hash,
        "verified_manifest_hash": verified.manifest_hash,
        "bundle_path": str(bundle_path),
        "repeated_bundle_path_matches": repeated_path == bundle_path,
        "exported_file_count": len(manifest.file_hashes) + 1,
        "tampered_bundle_blocked": tamper_blocked,
        "blocked_certificate_export_rejected": blocked_export_rejected,
        "unsafe_export_path_blocked": unsafe_path_blocked,
        "canonical_evidence_hashes_before": before_hashes,
        "canonical_evidence_hashes_after": after_hashes,
        "canonical_evidence_unchanged": before_hashes == after_hashes,
        "canonical_files_copied": False,
        "canonical_files_written": False,
        "sandbox_bundle_written_by_export": False,
        "activation_authorized": False,
        "strategy_switch_authorized": False,
        "runtime_cutover_authorized": False,
        "broker_execution_performed": False,
        "real_money_used": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
