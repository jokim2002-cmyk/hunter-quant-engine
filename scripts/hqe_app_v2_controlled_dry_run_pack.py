from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

VERSION = "HQE_APP_V2_CONTROLLED_DRY_RUN_PACK_V1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def process_command(repo: Path, workspace: Path, interval_seconds: int) -> List[str]:
    return [
        str(repo / ".venv" / "Scripts" / "python.exe"),
        str(repo / "scripts" / "hqe_market_day_persistent_paper_watch_loop.py"),
        "--workspace",
        str(workspace),
        "--user-id",
        "hqe-user",
        "--symbol",
        "NSE:NIFTY50-INDEX",
        "--interval-seconds",
        str(interval_seconds),
        "--run-data-fetch",
    ]


def run_preflight(repo: Path, workspace: Path, evidence_dir: Path) -> Dict[str, Any]:
    output = evidence_dir / "PREFLIGHT_OUTPUT.txt"
    command = [
        str(repo / ".venv" / "Scripts" / "python.exe"),
        str(repo / "scripts" / "hqe_app_v2_preflight.py"),
        "--workspace",
        str(workspace),
        "--repo-root",
        str(repo),
    ]
    completed = subprocess.run(
        command,
        cwd=repo,
        capture_output=True,
        text=True,
    )
    output.write_text(
        completed.stdout + ("\nSTDERR:\n" + completed.stderr if completed.stderr else ""),
        encoding="utf-8",
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "output_file": str(output),
    }


def snapshot_files(workspace: Path) -> Dict[str, Any]:
    files = []
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        files.append(
            {
                "path": str(path),
                "size_bytes": stat.st_size,
                "modified_ns": stat.st_mtime_ns,
            }
        )
    return {item["path"]: item for item in files}


def stop_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            text=True,
        )
    else:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def changed_files(before: Dict[str, Any], after: Dict[str, Any]) -> List[Dict[str, Any]]:
    changed = []
    for path, current in after.items():
        previous = before.get(path)
        if previous is None:
            changed.append({**current, "change": "CREATED"})
        elif (
            previous["size_bytes"] != current["size_bytes"]
            or previous["modified_ns"] != current["modified_ns"]
        ):
            changed.append({**current, "change": "MODIFIED"})
    return sorted(changed, key=lambda item: item["path"])


def run_once(
    repo: Path,
    workspace: Path,
    run_dir: Path,
    run_number: int,
    observe_seconds: int,
    interval_seconds: int,
) -> Dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = run_dir / "WATCH_STDOUT.txt"
    stderr_path = run_dir / "WATCH_STDERR.txt"

    before = snapshot_files(workspace)
    command = process_command(repo, workspace, interval_seconds)

    started_at = utc_now()
    started_monotonic = time.monotonic()

    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_handle:
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        process = subprocess.Popen(
            command,
            cwd=repo,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )

        time.sleep(observe_seconds)
        running_at_observation = process.poll() is None
        returncode_before_stop = process.poll()
        stop_process_tree(process)

    duration_seconds = round(time.monotonic() - started_monotonic, 2)
    after = snapshot_files(workspace)
    changed = changed_files(before, after)

    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")

    fatal_markers = [
        "Traceback (most recent call last)",
        "FileNotFoundError",
        "ModuleNotFoundError",
        "PermissionError",
    ]
    fatal_errors = [
        marker
        for marker in fatal_markers
        if marker in stderr_text or marker in stdout_text
    ]

    status = (
        "PASS"
        if running_at_observation and not fatal_errors
        else "FAIL"
    )

    payload = {
        "run_number": run_number,
        "started_at_utc": started_at,
        "finished_at_utc": utc_now(),
        "duration_seconds": duration_seconds,
        "observe_seconds": observe_seconds,
        "interval_seconds": interval_seconds,
        "pid": process.pid,
        "running_at_observation": running_at_observation,
        "returncode_before_stop": returncode_before_stop,
        "final_returncode": process.returncode,
        "changed_file_count": len(changed),
        "changed_files": changed,
        "fatal_error_markers": fatal_errors,
        "stdout_file": str(stdout_path),
        "stderr_file": str(stderr_path),
        "status": status,
        "paper_only": True,
        "data_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }

    (run_dir / "RUN_RESULT.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return payload


def build_decision(preflight: Dict[str, Any], runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    passed = preflight["status"] == "PASS" and all(
        run["status"] == "PASS" for run in runs
    )
    return {
        "version": VERSION,
        "generated_at_utc": utc_now(),
        "preflight": preflight,
        "runs": runs,
        "completed_runs": len(runs),
        "passed_runs": sum(run["status"] == "PASS" for run in runs),
        "dry_run_pack_status": "PASS" if passed else "HOLD",
        "decision": (
            "APP_V2_CONTROLLED_DRY_RUNS_COMPLETE"
            if passed
            else "APP_V2_DRY_RUN_REPAIR_REQUIRED"
        ),
        "paper_only": True,
        "data_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run two controlled HQE App V2 paper-watch dry runs."
    )
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--observe-seconds", type=int, default=90)
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--pause-seconds", type=int, default=10)
    args = parser.parse_args()

    repo = repo_root()
    workspace = Path(args.workspace)

    required = [
        repo / ".venv" / "Scripts" / "python.exe",
        repo / "scripts" / "hqe_market_day_persistent_paper_watch_loop.py",
        repo / "scripts" / "hqe_app_v2_preflight.py",
        workspace,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print(json.dumps({"status": "FAIL", "missing": missing}, indent=2))
        return 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_dir = workspace / f"HQE_APP_V2_CONTROLLED_DRY_RUNS_{stamp}"
    evidence_dir.mkdir(parents=True, exist_ok=False)

    preflight = run_preflight(repo, workspace, evidence_dir)
    runs: List[Dict[str, Any]] = []

    if preflight["status"] == "PASS":
        for run_number in range(1, args.runs + 1):
            runs.append(
                run_once(
                    repo,
                    workspace,
                    evidence_dir / f"RUN_{run_number:02d}",
                    run_number,
                    args.observe_seconds,
                    args.interval_seconds,
                )
            )
            if run_number < args.runs:
                time.sleep(args.pause_seconds)

    payload = build_decision(preflight, runs)
    payload["evidence_dir"] = str(evidence_dir)

    output = evidence_dir / "HQE_APP_V2_CONTROLLED_DRY_RUN_SUMMARY.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["dry_run_pack_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
