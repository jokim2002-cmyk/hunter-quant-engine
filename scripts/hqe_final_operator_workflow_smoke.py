from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_checked(command: list[str], timeout: int = 45) -> dict:
    result = subprocess.run(
        command,
        cwd=repo_root(),
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def workflow_smoke() -> dict:
    repo = repo_root()
    python_exe = repo / ".venv" / "Scripts" / "python.exe"
    app = repo / "scripts" / "hqe_product_app_v2.py"

    checks = {
        "app_guard": run_checked([str(python_exe), str(app), "--guard-check"]),
        "rc_guard": run_checked([
            str(python_exe),
            str(repo / "scripts" / "hqe_release_candidate_audit.py"),
            "--guard-check",
        ]),
        "operator_guard": run_checked([
            str(python_exe),
            str(repo / "scripts" / "hqe_operator_acceptance_engine.py"),
            "--guard-check",
        ]),
        "signoff_guard": run_checked([
            str(python_exe),
            str(repo / "scripts" / "hqe_final_rc_signoff_engine.py"),
            "--guard-check",
        ]),
    }

    passed = all(item["returncode"] == 0 for item in checks.values())
    combined = "\n".join(item["stdout"] for item in checks.values())
    safety_terms = {
        "paper_only": "paper" in combined.lower(),
        "no_real_orders": (
            "no_real_orders" in combined.lower()
            or "real_orders_enabled" in combined.lower()
            or "real orders" in combined.lower()
        ),
        "no_broker_execution": (
            "no_broker_execution" in combined.lower()
            or "broker_execution_enabled" in combined.lower()
            or "broker execution" in combined.lower()
        ),
        "no_auto_trading": (
            "no_auto_trading" in combined.lower()
            or "auto_trading_enabled" in combined.lower()
            or "auto trading" in combined.lower()
        ),
    }

    status = "PASS" if passed and all(safety_terms.values()) else "FAILED"
    return {
        "status": status,
        "checks": checks,
        "safety_terms": safety_terms,
        "real_order_invoked": False,
        "broker_execution_invoked": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HQE final operator workflow smoke"
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = workflow_smoke()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"HQE FINAL OPERATOR WORKFLOW SMOKE: {payload['status']}")
        for name, item in payload["checks"].items():
            print(f"{name}: {'PASS' if item['returncode'] == 0 else 'FAILED'}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
