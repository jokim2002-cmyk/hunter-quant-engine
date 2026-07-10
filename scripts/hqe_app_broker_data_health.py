from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_APP_BROKER_DATA_HEALTH_V1"
STATUS_FILE = "HQE_APP_BROKER_DATA_HEALTH_STATUS.json"

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


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def local_auth_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip()
    if base:
        return Path(base) / "HunterQuantEngine" / "FyersAuth"
    return Path.home() / "AppData" / "Local" / "HunterQuantEngine" / "FyersAuth"


def token_candidates(repo_root: Path) -> list[Path]:
    return [
        repo_root / "secrets" / "fyers_access_token.txt",
        local_auth_root() / "FYERS_ACCESS_TOKEN.txt",
    ]


def client_candidates(repo_root: Path) -> list[Path]:
    return [
        repo_root / "secrets" / "fyers_client_id.txt",
        local_auth_root() / "FYERS_CLIENT_ID.txt",
    ]


def first_present(candidates: list[Path], env_name: str) -> dict[str, Any]:
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            value = candidate.read_text(encoding="utf-8-sig").strip()
        except Exception:
            continue
        if value and not value.startswith("PASTE_"):
            return {"present": True, "source": str(candidate), "length": len(value)}
    env_value = os.environ.get(env_name, "").strip()
    if env_value:
        return {"present": True, "source": "USER_ENVIRONMENT", "length": len(env_value)}
    return {"present": False, "source": "", "length": 0}


def credential_presence(repo_root: Path) -> dict[str, Any]:
    client = first_present(client_candidates(repo_root), "FYERS_CLIENT_ID")
    token = first_present(token_candidates(repo_root), "FYERS_ACCESS_TOKEN")
    return {
        "client_id_present": client["present"],
        "access_token_present": token["present"],
        "client_id_source": client["source"],
        "access_token_source": token["source"],
        "client_id_length": client["length"],
        "access_token_length": token["length"],
        "secret_values_redacted": True,
    }


def internet_status(timeout: float = 0.7) -> dict[str, str]:
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=timeout):
            return {"status": "OK", "message": "Internet connected"}
    except OSError:
        return {"status": "DISCONNECTED", "message": "Internet unavailable"}


def latest_data_evidence(workspace: Path) -> dict[str, str]:
    patterns = (
        "*LIVE_DATA*CYCLE*STATUS*.json",
        "*FYERS*FETCHER*STATUS*.json",
        "*MARKET*DATA*STATUS*.json",
        "*PAPER*WATCH*STATUS*.json",
    )
    candidates: list[Path] = []
    if workspace.exists():
        for pattern in patterns:
            candidates.extend(path for path in workspace.rglob(pattern) if path.is_file())
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return {
            "status": "WAITING",
            "message": "No market-data evidence found yet",
            "evidence_path": "",
            "last_updated_utc": "",
        }
    latest = candidates[0]
    payload = read_json(latest)
    raw = str(
        payload.get("cycle_status")
        or payload.get("status")
        or payload.get("decision")
        or payload.get("guard_check_status")
        or "EVIDENCE_FOUND"
    ).upper()
    positive = ("PASS", "READY", "LIVE", "CONNECTED", "COMPLETE")
    status = "LIVE" if any(word in raw for word in positive) else "CHECK"
    updated = datetime.fromtimestamp(
        latest.stat().st_mtime, timezone.utc
    ).replace(microsecond=0).isoformat()
    return {
        "status": status,
        "message": raw,
        "evidence_path": str(latest),
        "last_updated_utc": updated,
    }


def operation_status(workspace: Path) -> dict[str, str]:
    payload = read_json(workspace / STATUS_FILE)
    return {
        "status": str(payload.get("status", "IDLE")),
        "message": str(payload.get("message", "")),
        "completed_at_utc": str(payload.get("completed_at_utc", "")),
    }


def broker_health_snapshot(
    repo_root: Path,
    workspace: Path,
    *,
    check_internet: bool = True,
) -> dict[str, Any]:
    credentials = credential_presence(repo_root)
    internet = (
        internet_status()
        if check_internet
        else {"status": "NOT_CHECKED", "message": "Internet check skipped"}
    )
    data = latest_data_evidence(workspace)
    operation = operation_status(workspace)

    if credentials["client_id_present"] and credentials["access_token_present"]:
        broker_status = "READY_FOR_DATA_TEST"
        broker_message = "Fyers login details detected"
    elif credentials["client_id_present"]:
        broker_status = "LOGIN_EXPIRED"
        broker_message = "Fyers access token missing or expired"
    else:
        broker_status = "NOT_CONFIGURED"
        broker_message = "Fyers login details not configured"

    display = (
        f"Internet: {internet['status']}  |  Broker: {broker_status}  |  "
        f"Market data: {data['status']}  |  Safe test: {operation['status']}"
    )
    return {
        "version": VERSION,
        "generated_at_utc": now_utc(),
        "broker_id": "fyers",
        "broker_display_name": "Fyers",
        "internet": internet,
        "credentials": credentials,
        "broker_status": broker_status,
        "broker_message": broker_message,
        "market_data": data,
        "operation": operation,
        "display_text": display,
        "safety_lock": SAFETY_LOCK,
        "secret_values_redacted": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def safe_test_command(repo_root: Path, workspace: Path, symbol: str) -> list[str]:
    return [
        str(repo_root / ".venv" / "Scripts" / "python.exe"),
        str(repo_root / "scripts" / "hqe_fyers_historical_5m_data_only_fetcher.py"),
        "--workspace",
        str(workspace),
        "--symbol",
        symbol,
        "--execute-live-data-only",
        "--write",
    ]


def load_value(candidates: list[Path]) -> str:
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            value = candidate.read_text(encoding="utf-8-sig").strip()
        except Exception:
            continue
        if value and not value.startswith("PASTE_"):
            return value
    return ""


def execute_safe_data_test(
    repo_root: Path,
    workspace: Path,
    symbol: str,
) -> dict[str, Any]:
    credentials = credential_presence(repo_root)
    output_path = workspace / STATUS_FILE
    if not credentials["client_id_present"] or not credentials["access_token_present"]:
        payload = {
            "version": VERSION,
            "status": "BLOCKED",
            "message": "Fyers client ID and access token are required.",
            "completed_at_utc": now_utc(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        }
        write_json(output_path, payload)
        return payload

    command = safe_test_command(repo_root, workspace, symbol)
    if not Path(command[1]).exists():
        payload = {
            "version": VERSION,
            "status": "FAILED",
            "message": "Safe Fyers data-only fetcher is missing.",
            "completed_at_utc": now_utc(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        }
        write_json(output_path, payload)
        return payload

    write_json(
        output_path,
        {
            "version": VERSION,
            "status": "RUNNING",
            "message": "Safe Fyers data-only connection test is running.",
            "started_at_utc": now_utc(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        },
    )

    env = os.environ.copy()
    token = load_value(token_candidates(repo_root))
    client_id = load_value(client_candidates(repo_root))
    if token:
        env["FYERS_ACCESS_TOKEN"] = token
    if client_id:
        env["FYERS_CLIENT_ID"] = client_id

    completed = subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    passed = completed.returncode == 0
    payload = {
        "version": VERSION,
        "status": "PASS" if passed else "FAILED",
        "message": (
            "Fyers market-data connection test passed."
            if passed
            else "Fyers data test failed. Refresh broker login and try again."
        ),
        "completed_at_utc": now_utc(),
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-1000:],
        "stderr_tail": completed.stderr[-1000:],
        "secret_values_redacted": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }
    write_json(output_path, payload)
    return payload


def launch_broker_health_worker(
    repo_root: Path,
    workspace: Path,
    operation: str,
    symbol: str = "NSE:NIFTY50-INDEX",
) -> subprocess.Popen[Any]:
    pythonw = repo_root / ".venv" / "Scripts" / "pythonw.exe"
    executable = pythonw if pythonw.exists() else repo_root / ".venv" / "Scripts" / "python.exe"
    command = [
        str(executable),
        str(Path(__file__).resolve()),
        "--repo-root",
        str(repo_root),
        "--workspace",
        str(workspace),
        "--execute-operation",
        operation,
        "--symbol",
        symbol,
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
        "network_mode": "DATA_ONLY_TEST",
        "secret_values_redacted": True,
        "plaintext_secret_echo_allowed": False,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE app broker/data health helper")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--workspace", default="")
    parser.add_argument("--symbol", default="NSE:NIFTY50-INDEX")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    parser.add_argument("--execute-operation", choices=["safe_data_test"])
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
            broker_health_snapshot(repo_root, workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.execute_operation == "safe_data_test":
        payload = execute_safe_data_test(repo_root, workspace, args.symbol)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1
    parser.error("Use --guard-check, --snapshot or --execute-operation.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
