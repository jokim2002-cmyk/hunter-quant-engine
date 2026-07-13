from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def process_snapshot(pid: int) -> dict[str, Any]:
    if os.name != "nt":
        return {
            "pid": pid,
            "responding": True,
            "working_set_bytes": 0,
            "handle_count": 0,
        }

    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            f"$p = Get-Process -Id {pid} -ErrorAction Stop; "
            "$p | Select-Object Id,Responding,WorkingSet64,HandleCount,CPU "
            "| ConvertTo-Json -Compress"
        ),
    ]
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=20,
        creationflags=CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        return {
            "pid": pid,
            "responding": False,
            "error": result.stderr.strip() or "process_not_found",
        }
    payload = json.loads(result.stdout)
    return {
        "pid": int(payload.get("Id", pid)),
        "responding": bool(payload.get("Responding", False)),
        "working_set_bytes": int(payload.get("WorkingSet64", 0) or 0),
        "handle_count": int(payload.get("HandleCount", 0) or 0),
        "cpu_seconds": float(payload.get("CPU", 0.0) or 0.0),
    }


def run_check(command: list[str], timeout: int = 45) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=repo_root(),
        text=True,
        capture_output=True,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def terminate_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def run_soak(
    minutes: float,
    sample_seconds: float,
    workspace: Path,
) -> dict[str, Any]:
    repo = repo_root()
    python_exe = repo / ".venv" / "Scripts" / "python.exe"
    app = repo / "scripts" / "hqe_product_app_v2.py"

    command = [
        str(python_exe),
        str(app),
        "--workspace",
        str(workspace),
        "--skip-license-check",
    ]

    process = subprocess.Popen(
        command,
        cwd=repo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

    started_at = datetime.now(timezone.utc).isoformat()
    deadline = time.monotonic() + max(1.0, minutes * 60.0)
    samples: list[dict[str, Any]] = []
    guard_checks: list[dict[str, Any]] = []
    status = "PASS"
    failure_reason = ""

    try:
        time.sleep(min(5.0, max(1.0, sample_seconds)))
        if process.poll() is not None:
            return {
                "status": "FAILED",
                "failure_reason": (
                    "HQE GUI exited during startup. "
                    "Close any already-running HQE window and rerun."
                ),
                "pid": process.pid,
                "samples": [],
                "guard_checks": [],
                "real_order_invoked": False,
                "broker_execution_invoked": False,
            }

        while time.monotonic() < deadline:
            if process.poll() is not None:
                status = "FAILED"
                failure_reason = "HQE GUI exited before the soak completed."
                break

            snapshot = process_snapshot(process.pid)
            snapshot["captured_at"] = datetime.now(timezone.utc).isoformat()
            samples.append(snapshot)

            if not snapshot.get("responding", False):
                status = "FAILED"
                failure_reason = "HQE became non-responsive during the soak."
                break

            guard = run_check([str(python_exe), str(app), "--guard-check"])
            guard["captured_at"] = datetime.now(timezone.utc).isoformat()
            guard_checks.append(guard)
            if guard["returncode"] != 0:
                status = "FAILED"
                failure_reason = "HQE safety guard failed during the soak."
                break

            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(sample_seconds, remaining))
    finally:
        terminate_process(process)

    memory_values = [
        int(item.get("working_set_bytes", 0) or 0)
        for item in samples
        if int(item.get("working_set_bytes", 0) or 0) > 0
    ]
    peak_memory = max(memory_values, default=0)
    start_memory = memory_values[0] if memory_values else 0
    end_memory = memory_values[-1] if memory_values else 0
    memory_growth = max(0, end_memory - start_memory)

    if peak_memory > 1_500_000_000:
        status = "FAILED"
        failure_reason = "HQE exceeded the 1.5 GB soak memory ceiling."

    payload = {
        "status": status,
        "failure_reason": failure_reason,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "minutes_requested": minutes,
        "sample_seconds": sample_seconds,
        "pid": process.pid,
        "sample_count": len(samples),
        "guard_check_count": len(guard_checks),
        "peak_memory_bytes": peak_memory,
        "memory_growth_bytes": memory_growth,
        "samples": samples,
        "guard_checks": guard_checks,
        "real_order_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_invoked": False,
    }

    report_dir = workspace / "HQE_SOAK_REPORTS"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "HQE_APP_LONG_SOAK_LATEST.json"
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    payload["report_path"] = str(report_path)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HQE long-duration GUI soak")
    parser.add_argument("--minutes", type=float, default=5.0)
    parser.add_argument("--sample-seconds", type=float, default=15.0)
    parser.add_argument(
        "--workspace",
        default=r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = run_soak(
        minutes=args.minutes,
        sample_seconds=args.sample_seconds,
        workspace=Path(args.workspace),
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"HQE APP LONG SOAK: {payload['status']}")
        print(f"Samples: {payload.get('sample_count', 0)}")
        print(f"Guard checks: {payload.get('guard_check_count', 0)}")
        print(f"Peak memory: {payload.get('peak_memory_bytes', 0)} bytes")
        print(f"Memory growth: {payload.get('memory_growth_bytes', 0)} bytes")
        if payload.get("failure_reason"):
            print(payload["failure_reason"])
        if payload.get("report_path"):
            print(f"Report: {payload['report_path']}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
