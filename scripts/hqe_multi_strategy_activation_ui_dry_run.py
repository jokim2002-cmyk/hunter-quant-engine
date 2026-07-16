"""Synthetic Phase 4G disabled activation preflight and UI model."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.hqe_multi_strategy_runtime_shadow_view_dry_run import (
    run_dry_run as run_phase4f_dry_run,
)
from src.multi_strategy.activation import DisabledActivationPreflight
from src.multi_strategy.adapters.current_smc import current_smc_manifest
from src.multi_strategy.evidence_view import OperatorEvidenceViewReader
from src.multi_strategy.recovery import OfflineRestartRecoveryReader
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.ui_model import ReadOnlyProductStrategyUiModel


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run_dry_run(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).resolve(strict=False)
    if root.exists():
        raise RuntimeError("Phase 4G workspace must not already exist")
    root.mkdir(parents=True)

    phase4f = run_phase4f_dry_run(root / "phase4f_runtime_shadow")
    selection = StrategySelectionSnapshot.from_dict(
        phase4f["phase4c_copy"]["selection"]
    )
    target_root = Path(phase4f["phase4c_copy"]["target_root"])
    recovery = OfflineRestartRecoveryReader(target_root).read(selection)
    journal_path = Path(phase4f["journal_path"])
    operator_view = OperatorEvidenceViewReader(
        journal_path,
        strategy_namespace=recovery.namespace_directory,
    ).read()
    manifest = current_smc_manifest()

    strategy_before = _tree_hashes(target_root)
    journal_before = hashlib.sha256(journal_path.read_bytes()).hexdigest()

    stopped_payload = {
        "status": "STOPPED",
        "pid": None,
        "paper_only": True,
        "broker_execution": False,
        "source": "PHASE4G_READ_ONLY_PREFLIGHT",
    }
    stopped_observation = StableRuntimeObservation(
        observed_at="2026-07-16T11:25:00+05:30",
        runtime_status="STOPPED",
        runtime_pid=None,
        first_read=stopped_payload,
        second_read=dict(stopped_payload),
    )
    preflight_engine = DisabledActivationPreflight(minimum_cycles=3)
    ready_preflight = preflight_engine.evaluate(
        manifest=manifest,
        selection=selection,
        recovery=recovery,
        operator_view=operator_view,
        runtime_observation=stopped_observation,
    )
    ui_model = ReadOnlyProductStrategyUiModel.build(
        manifest=manifest,
        selection=selection,
        preflight=ready_preflight,
        operator_view=operator_view,
        runtime_observation=stopped_observation,
    )

    running_payload = dict(stopped_payload)
    running_payload.update({"status": "RUNNING", "pid": 4100})
    running_observation = StableRuntimeObservation(
        observed_at="2026-07-16T11:25:00+05:30",
        runtime_status="RUNNING",
        runtime_pid=4100,
        first_read=running_payload,
        second_read=dict(running_payload),
    )
    blocked_preflight = preflight_engine.evaluate(
        manifest=manifest,
        selection=selection,
        recovery=recovery,
        operator_view=operator_view,
        runtime_observation=running_observation,
    )

    report_path = root / "product_ui_model" / "strategy_status_read_only.md"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(ui_model.render_markdown(), encoding="utf-8")

    journal_after = hashlib.sha256(journal_path.read_bytes()).hexdigest()
    strategy_after = _tree_hashes(target_root)
    if journal_before != journal_after:
        raise RuntimeError("Phase 4G modified the parity journal")
    if strategy_before != strategy_after:
        raise RuntimeError("Phase 4G modified namespaced strategy artifacts")

    return {
        "mode": "DISABLED_ACTIVATION_PREFLIGHT_UI_MODEL_DRY_RUN",
        "workspace": str(root),
        "canonical_runtime_connected": False,
        "runtime_control_authorized": False,
        "runtime_cutover_performed": False,
        "activation_authorized": False,
        "state_written": False,
        "ledger_written": False,
        "broker_execution_performed": False,
        "real_money_authorized": False,
        "module_131_modified": False,
        "journal_modified": False,
        "namespaced_strategy_artifacts_modified": False,
        "phase4f_evidence": {
            "journal_path": phase4f["journal_path"],
            "journal_sha256": phase4f["journal_sha256"],
            "operator_status": phase4f["operator_view"]["overall_status"],
            "operator_view_hash": phase4f["operator_view"]["view_hash"],
            "cycle_count": phase4f["operator_view"]["cycle_count"],
            "match_count": phase4f["operator_view"]["match_count"],
            "mismatch_count": phase4f["operator_view"]["mismatch_count"],
            "selection_hash": selection.selection_hash,
            "recovery_snapshot_hash": recovery.snapshot_hash,
            "target_root": str(target_root),
        },
        "ready_preflight": ready_preflight.to_dict(),
        "runtime_active_preflight": blocked_preflight.to_dict(),
        "ui_model": ui_model.to_dict(),
        "ui_report_path": str(report_path),
        "ui_report_sha256": hashlib.sha256(
            report_path.read_bytes()
        ).hexdigest(),
        "journal_sha256": journal_after,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HQE Phase 4G disabled activation and UI model dry run"
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="New external workspace. It must not already exist.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(run_dry_run(args.workspace), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
