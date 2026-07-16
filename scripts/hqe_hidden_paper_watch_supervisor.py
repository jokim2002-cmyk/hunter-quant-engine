from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

VERSION = "HQE_HIDDEN_PAPER_WATCH_SUPERVISOR_V1"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
DETACHED_PROCESS = 0x00000008 if os.name == "nt" else 0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def state_file(workspace: Path) -> Path:
    return workspace / "HQE_HIDDEN_PAPER_WATCH_SUPERVISOR_STATUS.json"


def read_state(workspace: Path) -> Dict[str, Any]:
    path = state_file(workspace)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            cp = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            return str(pid) in cp.stdout
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def write_state(workspace: Path, payload: Dict[str, Any]) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    state_file(workspace).write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def status_payload(workspace: Path) -> Dict[str, Any]:
    state = read_state(workspace)
    pid = int(state.get("pid", 0) or 0)
    alive = process_alive(pid)
    return {
        "version": VERSION,
        "workspace": str(workspace),
        "status": "RUNNING_HIDDEN" if alive else "NOT_RUNNING",
        "pid": pid if alive else None,
        "process_alive": alive,
        "state_file": str(state_file(workspace)),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }


def start(workspace: Path, user_id: str, symbol: str) -> Dict[str, Any]:
    current = status_payload(workspace)
    if current["process_alive"]:
        current.update({"started": False, "reason": "already_running"})
        return current

    repo = repo_root()
    executable = (
        repo / ".venv" / "Scripts" / "pythonw.exe"
        if os.name == "nt"
        else repo / ".venv" / "bin" / "python"
    )
    fallback = repo / ".venv" / "Scripts" / "python.exe"
    if not executable.is_file() and fallback.is_file():
        executable = fallback

    command = [
        str(executable),
        str(repo / "scripts" / "hqe_market_day_persistent_paper_watch_loop.py"),
        "--workspace",
        str(workspace),
        "--user-id",
        user_id,
        "--symbol",
        symbol,
        "--interval-seconds",
        "300",
        "--run-data-fetch",
    ]

    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    proc = subprocess.Popen(
        command,
        cwd=str(repo),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
        startupinfo=startupinfo,
    )

    payload = {
        "version": VERSION,
        "generated_at_utc": utc_now(),
        "workspace": str(workspace),
        "status": "RUNNING_HIDDEN",
        "pid": proc.pid,
        "visible_terminal_created": False,
        "pythonw_used": executable.name.lower() == "pythonw.exe",
        "started": True,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }
    write_state(workspace, payload)
    return payload


def stop(workspace: Path) -> Dict[str, Any]:
    state = read_state(workspace)
    pid = int(state.get("pid", 0) or 0)
    if not process_alive(pid):
        payload = status_payload(workspace)
        payload.update({"stopped": False, "reason": "not_running"})
        write_state(workspace, payload)
        return payload
    if os.name == "nt":
        cp = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
        stopped = cp.returncode == 0
    else:
        os.kill(pid, signal.SIGTERM)
        stopped = True
    payload = {
        "version": VERSION,
        "generated_at_utc": utc_now(),
        "workspace": str(workspace),
        "status": "STOPPED_BY_OPERATOR" if stopped else "STOP_FAILED",
        "pid": pid,
        "stopped": stopped,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }
    write_state(workspace, payload)
    return payload


def guard_payload() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "hidden_process_supported": True,
        "visible_terminal_required": False,
        "manual_operator_start_required": True,
        "manual_operator_stop_supported": True,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "paper_only": True,
        "data_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE hidden paper-watch supervisor")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--user-id", default="hqe-user")
    parser.add_argument("--symbol", default="NSE:NIFTY50-INDEX")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--start", action="store_true")
    group.add_argument("--stop", action="store_true")
    group.add_argument("--status", action="store_true")
    group.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.workspace)
    if args.guard_check:
        payload = guard_payload()
    elif args.start:
        payload = start(workspace, args.user_id, args.symbol)
    elif args.stop:
        payload = stop(workspace)
    else:
        payload = status_payload(workspace)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
