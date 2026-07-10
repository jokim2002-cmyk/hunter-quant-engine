from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

VERSION = "HQE_FYERS_LIVE_FETCH_DIAGNOSTIC_V2"
OUTPUT_FILENAME = "HQE_FYERS_LIVE_FETCH_DIAGNOSTIC.json"
INDIA_TZ = ZoneInfo("Asia/Kolkata")


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


def sha256(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        parsed = None

    if parsed is None:
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        try:
            number = float(text)
        except ValueError:
            return None
        if number > 10_000_000_000:
            number /= 1000
        try:
            parsed = datetime.fromtimestamp(number, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=INDIA_TZ)

    return parsed.astimezone(timezone.utc)


def find_datetime_column(fieldnames: Iterable[str]) -> Optional[str]:
    normalized = {name.strip().lower(): name for name in fieldnames if name}
    for candidate in ("datetime", "timestamp", "time", "date", "candle_time", "bar_time"):
        if candidate in normalized:
            return normalized[candidate]
    return None


def csv_semantics(path: Path) -> Dict[str, Any]:
    base = {
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "modified_ns": path.stat().st_mtime_ns if path.exists() else None,
        "sha256": sha256(path),
        "row_count": 0,
        "latest_candle_utc": None,
    }

    if not path.exists():
        return base

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            column = find_datetime_column(reader.fieldnames or [])
            latest = None
            rows = 0
            for row in reader:
                rows += 1
                if column:
                    parsed = parse_datetime(row.get(column))
                    if parsed is not None and (latest is None or parsed > latest):
                        latest = parsed
    except (OSError, csv.Error):
        return base

    base["row_count"] = rows
    base["latest_candle_utc"] = (
        latest.replace(microsecond=0).isoformat() if latest is not None else None
    )
    return base


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
        item for item in payload
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
    roots = [item for item in items if int(item.get("ParentProcessId") or 0) not in ids]
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
    preferred = repo / "scripts" / "hqe_fyers_historical_5m_data_only_fetcher.py"
    if preferred.exists():
        return {
            "selected": str(preferred),
            "selection_reason": "CANONICAL_FETCHER_PRESENT",
            "candidate_count": 1,
            "candidates": [{"path": str(preferred), "score": 100}],
        }

    candidates = []
    for path in sorted((repo / "scripts").glob("*.py")):
        try:
            lower = path.read_text(encoding="utf-8-sig", errors="replace").lower()
        except OSError:
            continue

        score = 0
        if "fyers" in lower:
            score += 5
        if "historical" in lower or "history" in lower:
            score += 4
        if "data_only_history_call_completed" in lower:
            score += 10
        if path.name == "hqe_fyers_live_fetch_diagnostic.py":
            score -= 100
        if score > 0:
            candidates.append({"path": str(path), "score": score})

    candidates.sort(key=lambda item: (-item["score"], item["path"]))
    return {
        "selected": candidates[0]["path"] if candidates else None,
        "selection_reason": "SCORED_DISCOVERY",
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


def detect_live_flag(help_output: str) -> Optional[str]:
    candidates = (
        "--execute-live-data-only",
        "--execute-live-data",
        "--run-live-data-only",
        "--live-data-only",
        "--execute-history",
        "--run-history",
    )
    for candidate in candidates:
        if candidate in help_output:
            return candidate
    return None


def build_command(
    python_exe: Path,
    script: Path,
    workspace: Path,
    help_output: str,
    require_live: bool,
) -> Dict[str, Any]:
    command = [str(python_exe), str(script)]

    if "--workspace" in help_output:
        command += ["--workspace", str(workspace)]
    if "--symbol" in help_output:
        command += ["--symbol", "NSE:NIFTY50-INDEX"]
    if "--user-id" in help_output:
        command += ["--user-id", "hqe-user"]
    if "--write" in help_output:
        command += ["--write"]

    live_flag = detect_live_flag(help_output)
    if require_live and live_flag:
        command.append(live_flag)

    return {
        "command": command,
        "live_flag": live_flag,
        "live_flag_applied": bool(require_live and live_flag),
    }


def execute_fetcher(
    repo: Path,
    workspace: Path,
    python_exe: Path,
    script: Path,
    evidence_dir: Path,
) -> Dict[str, Any]:
    helper = help_text(python_exe, script, repo)
    command_info = build_command(
        python_exe,
        script,
        workspace,
        helper["stdout"] + helper["stderr"],
        require_live=True,
    )

    stdout_path = evidence_dir / "FETCH_STDOUT.txt"
    stderr_path = evidence_dir / "FETCH_STDERR.txt"
    sample = workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"
    status = workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"

    before = {
        "sample_csv": csv_semantics(sample),
        "fetch_status": {
            "exists": status.exists(),
            "sha256": sha256(status),
            "size_bytes": status.stat().st_size if status.exists() else 0,
            "modified_ns": status.stat().st_mtime_ns if status.exists() else None,
        },
    }

    if not command_info["live_flag"]:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("Live data execution flag not found in fetcher help.\n", encoding="utf-8")
        return {
            "executed": False,
            "decision": "LIVE_FETCH_FLAG_NOT_FOUND",
            "command": command_info["command"],
            "live_flag": None,
            "live_flag_applied": False,
            "help_returncode": helper["returncode"],
            "stdout_file": str(stdout_path),
            "stderr_file": str(stderr_path),
            "before": before,
            "after": before,
            "timed_out": False,
            "returncode": None,
            "duration_seconds": 0.0,
        }

    started = time.monotonic()
    try:
        completed = subprocess.run(
            command_info["command"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=120,
        )
        timed_out = False
        stdout = completed.stdout
        stderr = completed.stderr
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        returncode = None

    stdout_path.write_text(stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(stderr, encoding="utf-8", errors="replace")

    after = {
        "sample_csv": csv_semantics(sample),
        "fetch_status": {
            "exists": status.exists(),
            "sha256": sha256(status),
            "size_bytes": status.stat().st_size if status.exists() else 0,
            "modified_ns": status.stat().st_mtime_ns if status.exists() else None,
        },
    }

    return {
        "executed": True,
        "command": command_info["command"],
        "live_flag": command_info["live_flag"],
        "live_flag_applied": command_info["live_flag_applied"],
        "duration_seconds": round(time.monotonic() - started, 2),
        "timed_out": timed_out,
        "returncode": returncode,
        "stdout_file": str(stdout_path),
        "stderr_file": str(stderr_path),
        "before": before,
        "after": after,
        "help_returncode": helper["returncode"],
    }


def classify(execution: Dict[str, Any], fetch_status: Dict[str, Any]) -> Dict[str, str]:
    if execution.get("decision") == "LIVE_FETCH_FLAG_NOT_FOUND":
        return {
            "decision": "LIVE_FETCH_FLAG_NOT_FOUND",
            "recommendation": "INSPECT_FETCHER_CLI_AND_ADD_EXPLICIT_LIVE_DATA_ONLY_FLAG",
        }

    if execution.get("timed_out"):
        return {
            "decision": "FETCH_DIAGNOSTIC_TIMEOUT",
            "recommendation": "INSPECT_FETCH_STDOUT_STDERR",
        }

    if execution.get("returncode") not in (0, None):
        return {
            "decision": "FETCHER_PROCESS_FAILED",
            "recommendation": "INSPECT_FETCH_STDERR_AND_FETCHER_ARGUMENTS",
        }

    external_api = bool(
        fetch_status.get("external_api_calls_executed")
        or fetch_status.get("external_api_calls_executed_by_module_173")
    )
    history_result = fetch_status.get("history_result") or {}
    response_redacted = history_result.get("response_redacted") or {}
    response_code = response_redacted.get("code")
    response_message = str(response_redacted.get("message") or "").lower()

    if response_code == -16 or "authenticate" in response_message:
        return {
            "decision": "AUTH_FAILED_CODE_-16",
            "recommendation": "REFRESH_FYERS_ACCESS_TOKEN_AND_REVALIDATE",
        }

    history_executed = bool(history_result.get("executed"))
    returned_rows = int(history_result.get("rows") or 0)
    offline_sample = str(history_result.get("status") or "").upper() == "OFFLINE_SAMPLE_SCHEMA_BY_DEFAULT"

    before_csv = execution["before"]["sample_csv"]
    after_csv = execution["after"]["sample_csv"]

    content_changed = before_csv.get("sha256") != after_csv.get("sha256")
    row_count_increased = int(after_csv.get("row_count") or 0) > int(before_csv.get("row_count") or 0)
    candle_advanced = (
        after_csv.get("latest_candle_utc") is not None
        and after_csv.get("latest_candle_utc") != before_csv.get("latest_candle_utc")
    )

    if offline_sample or not execution.get("live_flag_applied"):
        return {
            "decision": "LIVE_FETCH_NOT_REQUESTED_OFFLINE_SAMPLE_ONLY",
            "recommendation": "RERUN_WITH_VALID_LIVE_DATA_ONLY_FLAG",
        }

    if not external_api or not history_executed:
        return {
            "decision": "LIVE_FETCH_FLAG_APPLIED_BUT_API_NOT_EXECUTED",
            "recommendation": "INSPECT_FETCHER_BRANCH_AND_CREDENTIAL_VALIDATION",
        }

    if returned_rows <= 0:
        return {
            "decision": "LIVE_API_EXECUTED_BUT_ZERO_ROWS_RETURNED",
            "recommendation": "CHECK_REQUEST_RANGE_SYMBOL_AND_FYERS_RESPONSE",
        }

    if not content_changed and not row_count_increased and not candle_advanced:
        return {
            "decision": "LIVE_FETCH_REPORTED_SUCCESS_BUT_CSV_CONTENT_UNCHANGED",
            "recommendation": "INSPECT_CSV_WRITER_AND_RESPONSE_MAPPING",
        }

    return {
        "decision": "LIVE_FETCH_UPDATED_CANDLE_DATA",
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
    execution: Dict[str, Any] = {"executed": False, "reason": "EXECUTION_NOT_REQUESTED"}

    if execute and selected:
        execution = execute_fetcher(
            repo,
            workspace,
            python_exe,
            Path(selected),
            evidence_dir,
        )

    fetch_status = read_json(
        workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
    )

    if execution.get("executed") or execution.get("decision") == "LIVE_FETCH_FLAG_NOT_FOUND":
        result = classify(execution, fetch_status)
    elif not selected:
        result = {
            "decision": "FETCHER_SCRIPT_NOT_DISCOVERED",
            "recommendation": "REVIEW_FETCHER_CANDIDATES_MANUALLY",
        }
    else:
        result = {
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
        **result,
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
