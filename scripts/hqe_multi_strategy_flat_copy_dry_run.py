"""Synthetic isolated dry-run for the Phase 4C flat-state copy executor."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.migration import (
    LEGACY_LEDGER_REQUIRED_COLUMNS,
    LegacyModule131MigrationPlanner,
    LegacyModule131Paths,
)
from src.multi_strategy.migration_copy import (
    FlatStateCopyAuthorization,
    ReviewedFlatStateCopyExecutor,
)
from src.multi_strategy.selection import StrategySelectionSnapshot


def _write_synthetic_source(root: Path) -> LegacyModule131Paths:
    paths = LegacyModule131Paths.from_runtime_folder(root)
    root.mkdir(parents=True, exist_ok=False)
    state = {
        "status": "FLAT",
        "paper_only": True,
        "module": 131,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "auto_trading_allowed": False,
        "real_money_allowed": False,
    }
    paths.state.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    rows = [
        {
            "timestamp": "2026-07-16T10:00:00+05:30",
            "module": "131",
            "event": "POSITION_OPENED",
            "side": "CE_BUY",
            "option_symbol": "NIFTY_SYNTHETIC_CE",
            "entry": "100.0",
            "stop_loss": "60.0",
            "target": "220.0",
            "exit_reason": "",
            "paper_pnl": "0.0",
            "paper_only": "True",
        },
        {
            "timestamp": "2026-07-16T10:30:00+05:30",
            "module": "131",
            "event": "POSITION_CLOSED",
            "side": "CE_BUY",
            "option_symbol": "NIFTY_SYNTHETIC_CE",
            "entry": "100.0",
            "stop_loss": "60.0",
            "target": "220.0",
            "exit_reason": "TARGET_HIT",
            "paper_pnl": "120.0",
            "paper_only": "True",
        },
    ]
    with paths.ledger.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(LEGACY_LEDGER_REQUIRED_COLUMNS),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    paths.summary.write_text(
        json.dumps(
            {"paper_only": True, "synthetic": True},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    paths.report.write_text(
        "# Synthetic Phase 4C legacy report\n",
        encoding="utf-8",
    )
    return paths


def run_synthetic_dry_run(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).resolve(strict=False)
    if root.exists():
        raise RuntimeError(f"workspace already exists: {root}")

    source = root / "synthetic_legacy"
    target = root / "isolated_namespaced_copy"
    paths = _write_synthetic_source(source)

    registry = build_phase3_registry()
    registration = registry.get(
        CURRENT_SMC_STRATEGY_ID,
        CURRENT_SMC_STRATEGY_VERSION,
    )
    selection = StrategySelectionSnapshot.from_registration(
        registration
    )
    plan = LegacyModule131MigrationPlanner(
        paths,
        selection,
        runtime_confirmed_stopped=True,
    ).build_plan()
    authorization = FlatStateCopyAuthorization.from_plan(
        plan,
        selection,
        runtime_confirmed_stopped=True,
        isolated_storage_confirmed=True,
    )
    result = ReviewedFlatStateCopyExecutor(
        target,
        isolated_storage_confirmed=True,
    ).execute(plan, selection, authorization)

    return {
        "mode": "ISOLATED_SYNTHETIC_DRY_RUN",
        "workspace": str(root),
        "source_root": str(source),
        "target_root": str(target),
        "canonical_runtime_connected": False,
        "runtime_cutover_performed": False,
        "source_modified": False,
        "selection": selection.to_dict(),
        "plan": plan.to_dict(),
        "result": result.to_dict(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HQE Phase 4C isolated synthetic flat-copy dry run"
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="New external workspace. It must not already exist.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_synthetic_dry_run(args.workspace)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
