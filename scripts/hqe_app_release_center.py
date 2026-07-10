from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

VERSION = "HQE_APP_RELEASE_CENTER_V1"


def release_center_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_release_readiness_engine import (
        latest_output_paths,
        release_snapshot,
    )

    snapshot = release_snapshot(repo_root, workspace)
    snapshot["version"] = VERSION
    snapshot["latest_outputs"] = latest_output_paths(workspace)
    return snapshot


def launch_release_operation(
    repo_root: Path,
    workspace: Path,
    operation: str,
    source_zip: str = "",
) -> subprocess.Popen[Any]:
    pythonw = repo_root / ".venv" / "Scripts" / "pythonw.exe"
    executable = (
        pythonw
        if pythonw.exists()
        else repo_root / ".venv" / "Scripts" / "python.exe"
    )
    command = [
        str(executable),
        str(
            repo_root
            / "scripts"
            / "hqe_release_readiness_engine.py"
        ),
        "--repo-root",
        str(repo_root),
        "--workspace",
        str(workspace),
        "--operation",
        operation,
    ]
    if source_zip:
        command.extend(("--source-zip", source_zip))

    return subprocess.Popen(
        command,
        cwd=repo_root,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def launch_desktop_shortcut_install(
    repo_root: Path,
) -> subprocess.Popen[Any]:
    from hqe_release_readiness_engine import launch_shortcut_install

    return launch_shortcut_install(repo_root)


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "APP_WINDOWS_RELEASE_CENTER",
        "dry_run_only": True,
        "restore_staging_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE app Windows release center"
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
            release_center_snapshot(
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
