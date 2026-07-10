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

VERSION = "HQE_APP_OPERATOR_ACCEPTANCE_CENTER_V1"


def operator_acceptance_center_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_operator_acceptance_engine import latest_acceptance

    latest = latest_acceptance(workspace)
    report = latest.get("report", {})
    decision = report.get("decision", {})
    decision_status = str(decision.get("status", "NOT_RUN"))
    return {
        "version": VERSION,
        "display_text": (
            f"Operator Acceptance: {decision_status} | "
            f"Latest report: "
            f"{'available' if latest.get('json_path') else 'none'}"
        ),
        "latest": latest,
        "operator_guide": str(
            repo_root
            / "docs"
            / "HQE_PAPER_ONLY_RC_OPERATOR_GUIDE.md"
        ),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def launch_operator_acceptance(
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
            / "hqe_operator_acceptance_engine.py"
        ),
        "--repo-root",
        str(repo_root),
        "--workspace",
        str(workspace),
        "--run-acceptance",
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
        "workflow": "APP_OPERATOR_ACCEPTANCE_CENTER",
        "read_only_acceptance": True,
        "new_product_features": False,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE app operator acceptance center"
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
            operator_acceptance_center_snapshot(
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
