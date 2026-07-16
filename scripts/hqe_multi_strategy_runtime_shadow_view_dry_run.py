"""Synthetic Phase 4F runtime-shadow hook and operator evidence view."""

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

from scripts import hqe_smc_live_direction as legacy_smc
from scripts.hqe_multi_strategy_flat_copy_dry_run import (
    run_synthetic_dry_run,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.evidence_view import OperatorEvidenceViewReader
from src.multi_strategy.recorded import RecordedStrategyInput
from src.multi_strategy.recovery import OfflineRestartRecoveryReader
from src.multi_strategy.runtime_hook import (
    ReadOnlyProductRuntimeShadowHook,
    StableRuntimeObservation,
)
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.session import (
    GuardedShadowSessionController,
    ParityEvidenceJournal,
)
from src.multi_strategy.shadow import OfflineShadowParityRunner


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): (
            hashlib.sha256(path.read_bytes()).hexdigest()
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _index_rows(count: int = 30) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(count):
        base = 24000.0 + index
        rows.append(
            {
                "timestamp": f"2026-07-16 11:{index:02d}:00",
                "open": base,
                "high": base + 10,
                "low": base - 10,
                "close": base + 2,
                "volume": 1000 + index,
            }
        )
    return rows


def _premium_rows() -> list[dict[str, Any]]:
    return [
        {
            "timestamp": "2026-07-16 11:29:00",
            "symbol": "NIFTY_RUNTIME_CE",
            "ltp": 120.0,
            "dte": 2,
        },
        {
            "timestamp": "2026-07-16 11:29:00",
            "symbol": "NIFTY_RUNTIME_PE",
            "ltp": 95.0,
            "dte": 2,
        },
    ]


def run_dry_run(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).resolve(strict=False)
    if root.exists():
        raise RuntimeError("Phase 4F workspace must not already exist")
    root.mkdir(parents=True)

    copy_payload = run_synthetic_dry_run(root / "phase4c_copy")
    selection = StrategySelectionSnapshot.from_dict(copy_payload["selection"])
    target_root = Path(copy_payload["target_root"])
    recovery = OfflineRestartRecoveryReader(target_root).read(selection)
    target_before = _tree_hashes(target_root)

    runner = OfflineShadowParityRunner(
        registry=build_phase3_registry(),
        selection=selection,
        recovery=recovery,
    )
    journal = ParityEvidenceJournal(
        root / "shadow_evidence" / "runtime_parity_evidence.jsonl"
    )
    controller = GuardedShadowSessionController(
        runner=runner,
        recovery=recovery,
        journal=journal,
        session_id="phase4f-runtime-shadow-session",
    )
    controller.start(event_time="2026-07-16T11:00:00+05:30")
    hook = ReadOnlyProductRuntimeShadowHook(controller=controller)

    request = RecordedStrategyInput(
        index_rows=_index_rows(),
        premium_rows=_premium_rows(),
        er20=0.50,
        symbol="NIFTY",
        timeframe="5m",
        data_start="2026-07-16T11:00:00+05:30",
        data_end="2026-07-16T11:29:00+05:30",
    )

    hook_results: list[dict[str, Any]] = []
    original_gate = legacy_smc._run_gate
    try:
        for index, signal in enumerate(("LONG", "SHORT", "NEUTRAL"), start=1):
            event_time = f"2026-07-16T11:{index * 5:02d}:00+05:30"
            directional_move = (
                200.0 if signal == "LONG" else (-200.0 if signal == "SHORT" else 0.0)
            )

            def fixed_gate(events, selected=signal, move=directional_move):
                return selected, f"phase4f_{selected.lower()}", move

            legacy_smc._run_gate = fixed_gate
            runtime_payload = {
                "status": "RUNNING",
                "pid": 4100,
                "cycle": index,
                "paper_only": True,
                "broker_execution": False,
            }
            observation = StableRuntimeObservation(
                observed_at=event_time,
                runtime_status="RUNNING",
                runtime_pid=4100,
                first_read=runtime_payload,
                second_read=dict(runtime_payload),
            )
            hook_result = hook.observe_cycle(
                cycle_id=f"runtime-cycle-{index:03d}",
                event_time=event_time,
                observation=observation,
                request=request,
            )
            hook_results.append(hook_result.to_dict())
    finally:
        legacy_smc._run_gate = original_gate

    controller.close(event_time="2026-07-16T11:20:00+05:30")
    operator_reader = OperatorEvidenceViewReader(
        journal.path,
        strategy_namespace=recovery.namespace_directory,
    )
    journal_before_view = hashlib.sha256(journal.path.read_bytes()).hexdigest()
    operator_view = operator_reader.read()
    operator_report = root / "operator_evidence" / "shadow_evidence.md"
    operator_report.parent.mkdir(parents=True)
    operator_report.write_text(operator_view.render_markdown(), encoding="utf-8")
    journal_after_view = hashlib.sha256(journal.path.read_bytes()).hexdigest()
    if journal_before_view != journal_after_view:
        raise RuntimeError("operator evidence view modified parity journal")

    target_after = _tree_hashes(target_root)
    if target_before != target_after:
        raise RuntimeError("runtime shadow hook modified strategy namespace")

    records = journal.read_records()
    return {
        "mode": "READ_ONLY_RUNTIME_SHADOW_OPERATOR_VIEW_DRY_RUN",
        "workspace": str(root),
        "canonical_runtime_connected": False,
        "runtime_control_authorized": False,
        "runtime_cutover_performed": False,
        "state_written": False,
        "ledger_written": False,
        "broker_execution_performed": False,
        "module_131_modified": False,
        "namespaced_strategy_artifacts_modified": False,
        "journal_modified_by_operator_view": False,
        "phase4c_copy": copy_payload,
        "hook_results": hook_results,
        "journal_path": str(journal.path),
        "journal_sha256": journal_after_view,
        "journal_record_count": len(records),
        "operator_view": operator_view.to_dict(),
        "operator_report_path": str(operator_report),
        "operator_report_sha256": hashlib.sha256(
            operator_report.read_bytes()
        ).hexdigest(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HQE Phase 4F read-only runtime shadow and operator view"
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
