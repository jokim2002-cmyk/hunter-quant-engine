"""Synthetic Phase 4E guarded shadow session and evidence journal."""

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
from src.multi_strategy.recorded import RecordedStrategyInput
from src.multi_strategy.recovery import OfflineRestartRecoveryReader
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
                "timestamp": f"2026-07-16 10:{index:02d}:00",
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
            "timestamp": "2026-07-16 10:29:00",
            "symbol": "NIFTY_SESSION_CE",
            "ltp": 120.0,
            "dte": 2,
        },
        {
            "timestamp": "2026-07-16 10:29:00",
            "symbol": "NIFTY_SESSION_PE",
            "ltp": 95.0,
            "dte": 2,
        },
    ]


def run_dry_run(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).resolve(strict=False)
    if root.exists():
        raise RuntimeError("Phase 4E workspace must not already exist")
    root.mkdir(parents=True)

    copy_payload = run_synthetic_dry_run(root / "phase4c_copy")
    selection = StrategySelectionSnapshot.from_dict(
        copy_payload["selection"]
    )
    target_root = Path(copy_payload["target_root"])
    recovery = OfflineRestartRecoveryReader(target_root).read(
        selection
    )
    target_before = _tree_hashes(target_root)

    runner = OfflineShadowParityRunner(
        registry=build_phase3_registry(),
        selection=selection,
        recovery=recovery,
    )
    journal = ParityEvidenceJournal(
        root / "shadow_evidence" / "parity_evidence.jsonl"
    )
    controller = GuardedShadowSessionController(
        runner=runner,
        recovery=recovery,
        journal=journal,
        session_id="phase4e-synthetic-session",
    )
    controller.start(event_time="2026-07-16T10:00:00+05:30")

    request = RecordedStrategyInput(
        index_rows=_index_rows(),
        premium_rows=_premium_rows(),
        er20=0.50,
        symbol="NIFTY",
        timeframe="5m",
        data_start="2026-07-16T10:00:00+05:30",
        data_end="2026-07-16T10:29:00+05:30",
    )

    original_gate = legacy_smc._run_gate
    try:
        for index, signal in enumerate(
            ("LONG", "SHORT", "NEUTRAL"),
            start=1,
        ):
            directional_move = (
                200.0
                if signal == "LONG"
                else (-200.0 if signal == "SHORT" else 0.0)
            )

            def fixed_gate(
                events,
                selected=signal,
                move=directional_move,
            ):
                return (
                    selected,
                    f"phase4e_{selected.lower()}",
                    move,
                )

            legacy_smc._run_gate = fixed_gate
            controller.run_cycle(
                cycle_id=f"cycle-{index:03d}",
                event_time=(
                    f"2026-07-16T10:{index * 5:02d}:00+05:30"
                ),
                request=request,
            )
    finally:
        legacy_smc._run_gate = original_gate

    controller.close(event_time="2026-07-16T10:20:00+05:30")
    summary = controller.summary()
    records = journal.read_records()
    target_after = _tree_hashes(target_root)
    if target_after != target_before:
        raise RuntimeError(
            "shadow session modified namespaced strategy artifacts"
        )

    journal_hash = hashlib.sha256(journal.path.read_bytes()).hexdigest()
    return {
        "mode": "GUARDED_SHADOW_SESSION_DRY_RUN",
        "workspace": str(root),
        "canonical_runtime_connected": False,
        "runtime_cutover_performed": False,
        "state_written": False,
        "ledger_written": False,
        "module_131_modified": False,
        "namespaced_strategy_artifacts_modified": False,
        "phase4c_copy": copy_payload,
        "recovery_snapshot_hash": recovery.snapshot_hash,
        "journal_path": str(journal.path),
        "journal_sha256": journal_hash,
        "journal_records": [
            record.to_dict() for record in records
        ],
        "session_summary": summary.to_dict(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "HQE Phase 4E guarded offline shadow-session dry run"
        )
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="New external workspace. It must not already exist.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_dry_run(args.workspace)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
