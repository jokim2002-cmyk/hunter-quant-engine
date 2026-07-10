from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

VERSION = "HQE_APP_STRATEGY_BUILDER_CENTER_V1"


def builder_center_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_strategy_builder_engine import (
        active_selection_snapshot,
        builder_defaults,
    )
    from hqe_strategy_pack_registry import registry_snapshot

    registry = registry_snapshot(repo_root, workspace)
    selection = active_selection_snapshot(workspace)
    return {
        "version": VERSION,
        "registry": registry,
        "selection": selection,
        "defaults": builder_defaults("breakout"),
        "display_text": (
            f"Strategy Builder: {registry.get('valid_count', 0)} valid packs | "
            f"{selection.get('display_text', '')}"
        ),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def build_preview(form: dict[str, Any]) -> dict[str, Any]:
    from hqe_strategy_builder_engine import (
        build_strategy_pack,
        strategy_preview,
    )

    pack = build_strategy_pack(form)
    preview = strategy_preview(pack)
    return {
        "pack": pack,
        "preview": preview,
    }


def save_builder_draft(
    form: dict[str, Any],
    workspace: Path,
) -> Path:
    from hqe_strategy_builder_engine import save_draft

    return save_draft(form, workspace)


def select_paper_pack(
    pack_path: Path,
    workspace: Path,
) -> Path:
    from hqe_strategy_builder_engine import select_active_paper_pack

    return select_active_paper_pack(pack_path, workspace)


def clear_paper_selection(workspace: Path) -> bool:
    from hqe_strategy_builder_engine import clear_active_selection

    return clear_active_selection(workspace)


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "APP_STRATEGY_BUILDER_AND_SELECTOR",
        "paper_selection_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE app strategy builder center"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")
    if args.snapshot:
        print(json.dumps(
            builder_center_snapshot(
                Path(args.repo_root),
                Path(args.workspace),
            ),
            indent=2,
            sort_keys=True,
        ))
        return 0
    parser.error("Use --snapshot or --guard-check.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
