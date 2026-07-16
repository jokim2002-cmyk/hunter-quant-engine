"""Read-only CLI for inspecting legacy Module 131 migration readiness."""

from __future__ import annotations

import argparse
import json
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
    LegacyModule131MigrationPlanner,
    LegacyModule131Paths,
    build_recovery_compatibility_snapshot,
)
from src.multi_strategy.selection import StrategySelectionSnapshot


def build_audit_payload(
    runtime_folder: str | Path,
    *,
    runtime_confirmed_stopped: bool = False,
) -> dict[str, Any]:
    """Build one read-only plan and recovery snapshot."""

    registry = build_phase3_registry()
    registration = registry.get(
        CURRENT_SMC_STRATEGY_ID,
        CURRENT_SMC_STRATEGY_VERSION,
    )
    selection = StrategySelectionSnapshot.from_registration(
        registration
    )
    plan = LegacyModule131MigrationPlanner(
        LegacyModule131Paths.from_runtime_folder(runtime_folder),
        selection,
        runtime_confirmed_stopped=runtime_confirmed_stopped,
    ).build_plan()
    recovery = build_recovery_compatibility_snapshot(
        plan, selection
    )
    return {
        "mode": "READ_ONLY",
        "runtime_connected": False,
        "migration_execution_enabled": False,
        "selection": selection.to_dict(),
        "plan": plan.to_dict(),
        "recovery": recovery.to_dict(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only HQE Module 131 multi-strategy migration audit"
        )
    )
    parser.add_argument(
        "--runtime-folder",
        required=True,
        help="Existing HQE_PAPER_PRODUCT_RUNTIME folder",
    )
    parser.add_argument(
        "--runtime-confirmed-stopped",
        action="store_true",
        help=(
            "Record an external operator confirmation that no runtime "
            "process is active. This still does not execute migration."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_audit_payload(
        args.runtime_folder,
        runtime_confirmed_stopped=args.runtime_confirmed_stopped,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
