from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

VERSION = "HQE_APP_MARKET_DATA_QUALITY_CENTER_V1"
STATUS_FILE = "HQE_APP_MARKET_DATA_QUALITY_STATUS.json"


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def center_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_market_data_provider_registry import (
        provider_registry_snapshot,
    )
    from hqe_market_data_quality_engine import quality_snapshot

    providers = provider_registry_snapshot(repo_root)
    quality = quality_snapshot(repo_root, workspace)
    operation = read_json(workspace / STATUS_FILE)

    display = (
        f"Providers ready: "
        f"{providers.get('ready_data_only_count', 0)}/"
        f"{providers.get('provider_count', 0)} | "
        f"{quality.get('display_text', 'Data quality unavailable')}"
    )
    return {
        "version": VERSION,
        "providers": providers,
        "quality": quality,
        "operation": operation,
        "display_text": display,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def launch_cache_index_worker(
    repo_root: Path,
    workspace: Path,
) -> subprocess.Popen[Any]:
    pythonw = repo_root / ".venv" / "Scripts" / "pythonw.exe"
    executable = (
        pythonw
        if pythonw.exists()
        else repo_root / ".venv" / "Scripts" / "python.exe"
    )
    command = [
        str(executable),
        str(repo_root / "scripts" / "hqe_market_data_quality_engine.py"),
        "--repo-root",
        str(repo_root),
        "--workspace",
        str(workspace),
        "--write-index",
    ]
    return subprocess.Popen(
        command,
        cwd=repo_root,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "APP_MARKET_DATA_QUALITY_CENTER",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE app market-data quality center"
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
            center_snapshot(
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
