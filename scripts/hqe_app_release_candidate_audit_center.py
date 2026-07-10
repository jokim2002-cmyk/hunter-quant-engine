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

VERSION = "HQE_APP_RELEASE_CANDIDATE_AUDIT_CENTER_V1"


def rc_audit_center_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_release_candidate_audit import (
        latest_audit_report,
        verify_freeze_manifest,
    )

    freeze = verify_freeze_manifest(repo_root)
    latest = latest_audit_report(workspace)
    latest_payload = (
        json.loads(Path(latest).read_text(encoding="utf-8-sig"))
        if latest and Path(latest).exists()
        else {}
    )
    latest_status = str(latest_payload.get("status", "NOT_RUN"))
    return {
        "version": VERSION,
        "display_text": (
            f"Final RC Audit: {latest_status} | "
            f"Freeze: {freeze.get('status', '')} | "
            f"Latest report: {'available' if latest else 'none'}"
        ),
        "freeze": freeze,
        "latest_report": latest,
        "latest_audit": latest_payload,
        "operator_guide": str(
            repo_root
            / "docs"
            / "HQE_PAPER_ONLY_RC_OPERATOR_GUIDE.md"
        ),
        "freeze_manifest": str(
            repo_root
            / "release"
            / "HQE_PAPER_ONLY_RC_FREEZE_MANIFEST.json"
        ),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def launch_rc_audit_worker(
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
        str(
            repo_root
            / "scripts"
            / "hqe_release_candidate_audit.py"
        ),
        "--repo-root",
        str(repo_root),
        "--workspace",
        str(workspace),
        "--audit",
        "--write-report",
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
        "workflow": "APP_FINAL_RC_AUDIT_CENTER",
        "audit_mode": "READ_ONLY_SNAPSHOTS_AND_GUARDS",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE app final RC audit center"
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
            rc_audit_center_snapshot(
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
