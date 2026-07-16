"""Synthetic Phase 4D offline recovery and shadow-parity dry run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.hqe_multi_strategy_flat_copy_dry_run import (
    run_synthetic_dry_run,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.recorded import RecordedStrategyInput
from src.multi_strategy.recovery import OfflineRestartRecoveryReader
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.shadow import OfflineShadowParityRunner


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
            "symbol": "NIFTY_SHADOW_CE",
            "ltp": 120.0,
            "dte": 2,
        },
        {
            "timestamp": "2026-07-16 10:29:00",
            "symbol": "NIFTY_SHADOW_PE",
            "ltp": 95.0,
            "dte": 2,
        },
    ]


def run_dry_run(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).resolve(strict=False)
    copy_payload = run_synthetic_dry_run(root / "phase4c_copy")

    selection = StrategySelectionSnapshot.from_dict(
        copy_payload["selection"]
    )
    target_root = Path(copy_payload["target_root"])
    recovery = OfflineRestartRecoveryReader(target_root).read(
        selection
    )

    request = RecordedStrategyInput(
        index_rows=_index_rows(),
        premium_rows=_premium_rows(),
        er20=0.50,
        symbol="NIFTY",
        timeframe="5m",
        data_start="2026-07-16T10:00:00+05:30",
        data_end="2026-07-16T10:29:00+05:30",
    )
    parity = OfflineShadowParityRunner(
        registry=build_phase3_registry(),
        selection=selection,
        recovery=recovery,
    ).run(request)
    parity.require_match()

    second_recovery = OfflineRestartRecoveryReader(target_root).read(
        selection
    )
    if second_recovery.snapshot_hash != recovery.snapshot_hash:
        raise RuntimeError("offline recovery snapshot is not deterministic")

    return {
        "mode": "OFFLINE_RECOVERY_SHADOW_DRY_RUN",
        "workspace": str(root),
        "canonical_runtime_connected": False,
        "runtime_cutover_performed": False,
        "state_written": False,
        "ledger_written": False,
        "phase4c_copy": copy_payload,
        "recovery": recovery.to_dict(),
        "shadow_parity": parity.to_dict(),
        "recovery_repeat_hash_match": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HQE Phase 4D offline recovery and shadow-parity dry run"
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
