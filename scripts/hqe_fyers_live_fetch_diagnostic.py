from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "HQE_FYERS_LIVE_FETCH_DIAGNOSTIC_V1"
OUTPUT_FILENAME = "HQE_FYERS_LIVE_FETCH_DIAGNOSTIC.json"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().replace(microsecond=0).isoformat()


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def sha_snapshot(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"exists": False, "size_bytes": 0, "modified_ns": None}
    stat = path.stat()
    return {
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
    }


def actual_python_watch_processes() -> List[Dict[str, Any]]:
    if os.name != "nt":
        return []

    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            "Where-Object {"
            "$_.CommandLine -like '*hqe_market_day_persistent_paper_watch_loop.py*' "
            "-and $_.Name -match '^python(w)?\\.exe$'"
            "} | "
            "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | "
            "ConvertTo-Json -Compress"
        ),
    ]

    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []

    raw = completed.stdout.strip()
    if not raw:
        return []

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        payload = [payload]

    return [
        item
        for item in payload
        if isinstance(item, dict)
        and item.get("ProcessId")
        and str(item.get("Name", "")).lower() in {"python.exe", "pythonw.exe"}
    ]


def canonical_python_watch_process(
    processes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    items = processes if processes is not None else actual_python_watch_processes()

    if not items:
        return {
            "canonical_pid": None,
            "process_count": 0,
            "reason": "ACTUAL_PYTHON_WATCH_PROCESS_NOT_FOUND",
            "processes": [],
        }

    ids = {int(item["ProcessId"]) for item in items}
    roots = [
        item
        for item in items
        if int(item.get("ParentProcessId") or 0) not in ids
    ]
    preferred = roots or items
    canonical = min(preferred, key=lambda item: int(item["ProcessId"]))

    return {
        "canonical_pid": int(canonical["ProcessId"]),
        "canonical_parent_pid": int(canonical.get("ParentProcessId") or 0),
        "canonical_executable": canonical.get("ExecutablePath", ""),
        "process_count": len(items),
        "reason": "ROOT_PYTHON_WATCH_PROCESS" if canonical in roots else "LOWEST_PYTHON_PID_FALLBACK",
        "processes": items,
    }


def discover_fetcher(repo: Path) -> Dict[str, Any]:
    candidates = []
    for path in sorted((repo / "scripts").glob("*.py")):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue

        score = 0
        lower = text.lower()
        if "data_only_history_call_completed" in lower:
            score += 10
        if "fyers" in lower:
            score += 5
        if "historical" in lower or "history" in lower:
            score += 4
        if "5m" in lower or "resolution" in lower:
            score += 2
        if "argparse" in lower:
            score += 1
        if "persistent_paper_watch_loop" in path.name:
            score -= 5
        if score > 0:
            candidates.append({"path": str(path), "score": score})

    candidates.sort(key=lambda item: (-item["score"], item["path"]))

    return {
        "selected": candidates[0]["path"] if candidates else None,
        "candidate_count": len(candidates),
        "candidates": candidates[:10],
    }


def help_text(python_exe: Path, script: Path, repo: Path) -> Dict[str, Any]:
    completed = subprocess.run(
        [str(python_exe), str(script), "--help"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def build_command(
    python_exe: Path,
    script: Path,
    workspace: Path,
    help_output: str,
) -> List[str]:
    command = [str(python_exe), str(script)]

    if "--workspace" in help_output:
        command += ["--workspace", str(workspace)]
    if "--symbol" in help_output:
        command += ["--symbol", "NSE:NIFTY50-INDEX"]
    if "--user-id" in help_output:
        command += ["--user-id", "hqe-user"]
    if "--write" in help_output:
        command += ["--write"]

    return command


def execute_fetcher(
    repo: Path,
    workspace: Path,
    python_exe: Path,
    script: Path,
    evidence_dir: Path,
) -> Dict[str, Any]:
    helper = help_text(python_exe, script, repo)
    command = build_command(python_exe, script, workspace, helper["stdout"] + helper["stderr"])

    stdout_path = evidence_dir / "FETCH_STDOUT.txt"
    stderr_path = evidence_dir / "FETCH_STDERR.txt"

    before = {
        "sample_csv": sha_snapshot(workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"),
        "fetch_status": sha_snapshot(workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"),
    }

    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=120,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        completed = None
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
    else:
        stdout = completed.stdout
        stderr = completed.stderr

    stdout_path.write_text(stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(stderr, encoding="utf-8", errors="replace")

    after = {
        "sample_csv": sha_snapshot(workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"),
        "fetch_status": sha_snapshot(workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"),
    }

    changed = {
        key: before[key] != after[key]
        for key in before
    }

    return {
        "command": command,
        "duration_seconds": round(time.monotonic() - started, 2),
        "timed_out": timed_out,
        "returncode": None if completed is None else completed.returncode,
        "stdout_file": str(stdout_path),
        "stderr_file": str(stderr_path),
        "before": before,
        "after": after,
        "changed": changed,
        "help_returncode": helper["returncode"],
    }


def classify(
    execution: Dict[str, Any],
    fetch_status: Dict[str, Any],
    csv_changed: bool,
) -> Dict[str, str]:
    raw_status = str(
        fetch_status.get("status")
        or fetch_status.get("decision")
        or fetch_status.get("fetch_status")
        or "UNKNOWN"
    )

    if execution["timed_out"]:
        return {
            "decision": "FETCH_DIAGNOSTIC_TIMEOUT",
            "recommendation": "INSPECT_FETCH_STDOUT_STDERR",
        }

    if execution["returncode"] not in (0, None):
        return {
            "decision": "FETCHER_PROCESS_FAILED",
            "recommendation": "INSPECT_FETCH_STDERR_AND_FETCHER_ARGUMENTS",
        }

    if not csv_changed:
        if "COMPLETED" in raw_status.upper() or "PASS" in raw_status.upper():
            return {
                "decision": "FETCH_REPORTED_COMPLETE_BUT_CSV_UNCHANGED",
                "recommendation": "INSPECT_FYERS_RESPONSE_AND_CSV_WRITER",
            }
        return {
            "decision": "FETCH_DID_NOT_UPDATE_CSV",
            "recommendation": "CHECK_FYERS_RESPONSE_STATUS_AND_CREDENTIALS",
        }

    return {
        "decision": "FETCH_UPDATED_CSV",
        "recommendation": "RUN_CANDLE_FRESHNESS_AUDIT",
    }


def run_diagnostic(repo: Path, workspace: Path, execute: bool) -> Dict[str, Any]:
    python_exe = repo / ".venv" / "Scripts" / "python.exe"
    discovery = discover_fetcher(repo)
    process = canonical_python_watch_process()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_dir = workspace / f"HQE_FYERS_LIVE_FETCH_DIAGNOSTIC_{stamp}"
    evidence_dir.mkdir(parents=True, exist_ok=False)

    selected = discovery["selected"]
    execution: Dict[str, Any] = {
        "executed": False,
        "reason": "EXECUTION_NOT_REQUESTED",
    }

    if execute and selected:
        execution = {
            "executed": True,
            **execute_fetcher(
                repo,
                workspace,
                python_exe,
                Path(selected),
                evidence_dir,
            ),
        }

    fetch_status = read_json(
        workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
    )

    if execution.get("executed"):
        decision = classify(
            execution,
            fetch_status,
            bool(execution["changed"]["sample_csv"]),
        )
    elif not selected:
        decision = {
            "decision": "FETCHER_SCRIPT_NOT_DISCOVERED",
            "recommendation": "REVIEW_FETCHER_CANDIDATES_MANUALLY",
        }
    else:
        decision = {
            "decision": "FETCHER_DISCOVERED_READY_FOR_EXECUTION",
            "recommendation": "RERUN_WITH_EXECUTE_FETCH",
        }

    payload = {
        "version": VERSION,
        "generated_at_utc": iso_now(),
        "repo": str(repo),
        "workspace": str(workspace),
        "evidence_dir": str(evidence_dir),
        "fetcher_discovery": discovery,
        "canonical_watch_process": process,
        "execution": execution,
        "fetch_status_after": fetch_status,
        **decision,
        "paper_only": True,
        "data_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }

    atomic_write_json(evidence_dir / OUTPUT_FILENAME, payload)
    atomic_write_json(workspace / OUTPUT_FILENAME, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE Fyers live fetch diagnostic")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--repo-root")
    parser.add_argument("--execute-fetch", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[1]
    workspace = Path(args.workspace)

    if not repo.exists():
        raise SystemExit(f"Repo not found: {repo}")
    if not workspace.exists():
        raise SystemExit(f"Workspace not found: {workspace}")

    payload = run_diagnostic(repo, workspace, args.execute_fetch)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
