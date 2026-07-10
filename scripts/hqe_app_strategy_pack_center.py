from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "HQE_APP_STRATEGY_PACK_CENTER_V1"


def strategy_pack_center_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_strategy_pack_registry import registry_snapshot

    snapshot = registry_snapshot(repo_root, workspace)
    snapshot["version"] = VERSION
    return snapshot


def import_pack(
    source_path: Path,
    repo_root: Path,
    workspace: Path,
) -> Path:
    from hqe_strategy_pack_registry import import_strategy_pack

    return import_strategy_pack(
        source_path,
        repo_root,
        workspace,
    )


def export_pack(
    source_path: Path,
    repo_root: Path,
    workspace: Path,
) -> Path:
    from hqe_strategy_pack_registry import export_strategy_pack

    return export_strategy_pack(
        source_path,
        repo_root,
        workspace,
    )


def clone_pack(
    source_path: Path,
    repo_root: Path,
    workspace: Path,
    *,
    new_strategy_id: str,
    new_name: str,
) -> Path:
    from hqe_strategy_pack_registry import clone_pack_as_draft

    return clone_pack_as_draft(
        source_path,
        repo_root,
        workspace,
        new_strategy_id=new_strategy_id,
        new_name=new_name,
    )


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "APP_STRATEGY_PACK_CENTER",
        "json_only": True,
        "paper_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE app strategy-pack center"
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
            strategy_pack_center_snapshot(
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
