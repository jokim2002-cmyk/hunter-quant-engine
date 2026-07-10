from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_APP_PAPER_WATCH_CONTROL_V1"
STATUS_FILE = "HQE_APP_PAPER_WATCH_STATUS.json"
LOG_FILE = "HQE_APP_PAPER_WATCH_SESSION.log"

RUNNER_CANDIDATES = (
    "run_forward_paper_auto_runner.py",
    "hqe_forward_paper_auto_runner.py",
    "hqe_forward_paper_watch.py",
)

FORBIDDEN_ARGUMENTS = {
    "--real",
    "--live-trading",
    "--real-orders",
    "--broker-execution",
    "--place-order",
    "--auto-trading",
    "--option-selling",
}

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def discover_runner(repo_root: Path) -> Path | None:
    scripts = repo_root / "scripts"
    for candidate in RUNNER_CANDIDATES:
        path = scripts / candidate
        if path.exists():
            return path
    if scripts.exists():
        matches = sorted(
            path
            for path in scripts.glob("*paper*runner*.py")
            if path.is_file()
        )
        if matches:
            return matches[0]
    return None


def runner_help(
    repo_root: Path,
    runner: Path,
) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(repo_root / ".venv" / "Scripts" / "python.exe"),
            str(runner),
            "--help",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    text = (completed.stdout + "\n" + completed.stderr).strip()
    return {
        "status": "PASS" if completed.returncode == 0 else "FAILED",
        "return_code": completed.returncode,
        "text": text,
    }


def supported_options(help_text: str) -> set[str]:
    return set(re.findall(r"(?<!\w)--[a-z0-9][a-z0-9-]*", help_text.lower()))


def build_runner_command(
    repo_root: Path,
    runner: Path,
    workspace: Path,
    help_text: str,
) -> list[str]:
    options = supported_options(help_text)
    if "--workspace" not in options:
        raise RuntimeError("Paper runner does not expose --workspace.")

    command = [
        str(repo_root / ".venv" / "Scripts" / "python.exe"),
        str(runner),
        "--workspace",
        str(workspace),
    ]

    preferred_flags = (
        "--paper-only",
        "--simulation-only",
        "--paper-watch",
        "--watch",
        "--write",
    )
    for flag in preferred_flags:
        if flag in options:
            command.append(flag)

    optional_pairs = (
        ("--user-id", "JOKIM"),
        ("--symbol", "NSE:NIFTY50-INDEX"),
        ("--poll-seconds", "30"),
        ("--interval-seconds", "30"),
    )
    for flag, value in optional_pairs:
        if flag in options:
            command.extend((flag, value))

    lowered = {part.lower() for part in command}
    forbidden = sorted(lowered & FORBIDDEN_ARGUMENTS)
    if forbidden:
        raise RuntimeError(
            "Unsafe runner arguments detected: " + ", ".join(forbidden)
        )
    return command


def runner_guard(
    repo_root: Path,
    runner: Path,
    help_text: str,
) -> dict[str, Any]:
    options = supported_options(help_text)
    if "--guard-check" not in options:
        return {
            "status": "CHECK_REQUIRED",
            "message": "Runner does not expose --guard-check.",
        }

    completed = subprocess.run(
        [
            str(repo_root / ".venv" / "Scripts" / "python.exe"),
            str(runner),
            "--guard-check",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=90,
    )
    return {
        "status": "PASS" if completed.returncode == 0 else "FAILED",
        "message": "Paper runner guard check completed.",
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-900:],
        "stderr_tail": completed.stderr[-900:],
    }


def pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        pass

    try:
        completed = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return str(pid) in completed.stdout
    except Exception:
        return False


def latest_watch_evidence(workspace: Path) -> str:
    patterns = (
        "*PAPER*WATCH*STATUS*.json",
        "*FORWARD*PAPER*STATUS*.json",
        "*LIVE_DATA*CYCLE*STATUS*.json",
        "*FORWARD*TRADE*LOG*.csv",
    )
    candidates: list[Path] = []
    if workspace.exists():
        for pattern in patterns:
            candidates.extend(
                path
                for path in workspace.rglob(pattern)
                if path.is_file()
                and path.name not in {STATUS_FILE}
            )
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return str(candidates[0]) if candidates else ""


def session_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    runner = discover_runner(repo_root)
    status_payload = read_json(workspace / STATUS_FILE)
    pid = int(status_payload.get("pid", 0) or 0)
    running = pid_is_running(pid)

    help_payload: dict[str, Any] = {
        "status": "MISSING",
        "text": "",
    }
    guard = {
        "status": "MISSING",
        "message": "Paper runner is missing.",
    }
    command_preview: list[str] = []

    if runner is not None:
        help_payload = runner_help(repo_root, runner)
        if help_payload["status"] == "PASS":
            try:
                command_preview = build_runner_command(
                    repo_root,
                    runner,
                    workspace,
                    str(help_payload["text"]),
                )
                guard = runner_guard(
                    repo_root,
                    runner,
                    str(help_payload["text"]),
                )
            except Exception as exc:
                guard = {
                    "status": "CHECK_REQUIRED",
                    "message": str(exc),
                }

    if running:
        session_status = "RUNNING"
    elif status_payload.get("status") in {"FAILED", "BLOCKED"}:
        session_status = str(status_payload["status"])
    elif status_payload:
        session_status = "STOPPED"
    else:
        session_status = "IDLE"

    start_ready = bool(
        runner is not None
        and help_payload["status"] == "PASS"
        and guard["status"] == "PASS"
        and command_preview
        and not running
    )
    display = (
        f"Paper watch: {session_status} | "
        f"Runner: {'READY' if runner else 'MISSING'} | "
        f"Guard: {guard['status']} | PID: {pid or 'none'}"
    )
    return {
        "version": VERSION,
        "generated_at_utc": utc_now_text(),
        "session_status": session_status,
        "running": running,
        "pid": pid,
        "runner_path": str(runner) if runner else "",
        "runner_help_status": help_payload["status"],
        "runner_guard": guard,
        "start_ready": start_ready,
        "command_preview": command_preview,
        "latest_log_path": str(workspace / LOG_FILE)
        if (workspace / LOG_FILE).exists()
        else "",
        "latest_evidence_path": latest_watch_evidence(workspace),
        "last_message": str(status_payload.get("message", "")),
        "display_text": display,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def start_paper_watch(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    snapshot = session_snapshot(repo_root, workspace)
    status_path = workspace / STATUS_FILE

    if snapshot["running"]:
        payload = {
            "version": VERSION,
            "status": "RUNNING",
            "message": "Paper-watch session is already running.",
            "pid": snapshot["pid"],
            "updated_at_utc": utc_now_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        }
        write_json(status_path, payload)
        return payload

    if not snapshot["start_ready"]:
        payload = {
            "version": VERSION,
            "status": "BLOCKED",
            "message": (
                "Paper-watch start blocked. Runner, help or guard "
                "validation is not ready."
            ),
            "updated_at_utc": utc_now_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        }
        write_json(status_path, payload)
        return payload

    log_path = workspace / LOG_FILE
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("a", encoding="utf-8")
    log_handle.write(
        f"\n[{utc_now_text()}] HQE app starting paper-watch session.\n"
    )
    log_handle.flush()

    process = subprocess.Popen(
        list(snapshot["command_preview"]),
        cwd=repo_root,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    log_handle.close()

    payload = {
        "version": VERSION,
        "status": "RUNNING",
        "message": "Paper-watch session started.",
        "pid": process.pid,
        "runner_path": snapshot["runner_path"],
        "log_path": str(log_path),
        "started_at_utc": utc_now_text(),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }
    write_json(status_path, payload)
    return payload


def stop_paper_watch(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    del repo_root
    status_path = workspace / STATUS_FILE
    current = read_json(status_path)
    pid = int(current.get("pid", 0) or 0)

    if not pid or not pid_is_running(pid):
        payload = {
            "version": VERSION,
            "status": "STOPPED",
            "message": "No running paper-watch session was found.",
            "pid": pid,
            "stopped_at_utc": utc_now_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        }
        write_json(status_path, payload)
        return payload

    completed = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    stopped = completed.returncode == 0 or not pid_is_running(pid)
    payload = {
        "version": VERSION,
        "status": "STOPPED" if stopped else "FAILED",
        "message": (
            "Paper-watch session stopped."
            if stopped
            else "Paper-watch process could not be stopped."
        ),
        "pid": pid,
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-700:],
        "stderr_tail": completed.stderr[-700:],
        "stopped_at_utc": utc_now_text(),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }
    write_json(status_path, payload)
    return payload


def launch_watch_control_worker(
    repo_root: Path,
    workspace: Path,
    operation: str,
) -> subprocess.Popen[Any]:
    if operation not in {"start", "stop"}:
        raise ValueError("operation must be start or stop")

    pythonw = repo_root / ".venv" / "Scripts" / "pythonw.exe"
    executable = (
        pythonw
        if pythonw.exists()
        else repo_root / ".venv" / "Scripts" / "python.exe"
    )
    command = [
        str(executable),
        str(Path(__file__).resolve()),
        "--repo-root",
        str(repo_root),
        "--workspace",
        str(workspace),
        f"--{operation}",
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
        "workflow": "PAPER_WATCH_SESSION_CONTROL",
        "paper_process_control_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE app paper-watch session control"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")

    repo_root = Path(args.repo_root)
    workspace = Path(args.workspace)

    if args.snapshot:
        print(json.dumps(
            session_snapshot(repo_root, workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.start:
        payload = start_paper_watch(repo_root, workspace)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "RUNNING" else 1
    if args.stop:
        payload = stop_paper_watch(repo_root, workspace)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "STOPPED" else 1

    parser.error("Use --guard-check, --snapshot, --start or --stop.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
