"""HQE local login shell / desktop app gate.

Module 147 safety scope:
- Local access gate only.
- Paper/simulation only.
- No broker execution, no real orders, no auto trading, no option selling.
- No external API calls.
- No plaintext password storage.
- No profitability claim.

This script stores a salted PBKDF2 password hash in a local file outside the
repo by default and writes login session evidence to the forward validation
workspace after a successful login.
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as _dt
import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

VERSION = "MODULE_147_LOCAL_LOGIN_SHELL_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_CREDENTIAL_FILE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_LOCAL_LOGIN\hqe_local_login_credentials.json")
DEFAULT_SESSION_FILE_NAME = "HQE_LOCAL_LOGIN_SESSION.json"
DEFAULT_SESSION_LEDGER_NAME = "HQE_LOCAL_LOGIN_SESSION_LEDGER.csv"

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 390_000
SALT_BYTES = 32

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_external_api": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}


def utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def safe_user_id(user_id: str) -> str:
    normalized = (user_id or "").strip()
    if not normalized:
        raise ValueError("user_id is required")
    if len(normalized) > 80:
        raise ValueError("user_id is too long")
    disallowed = set('\\/\x00\r\n\t')
    if any(ch in disallowed for ch in normalized):
        raise ValueError("user_id contains unsafe characters")
    return normalized


def _b64_encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64_decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def hash_password(password: str, *, salt: Optional[bytes] = None) -> Dict[str, Any]:
    if password is None or password == "":
        raise ValueError("password is required")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    salt = salt if salt is not None else secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return {
        "algorithm": f"pbkdf2_hmac_{PBKDF2_ALGORITHM}",
        "iterations": PBKDF2_ITERATIONS,
        "salt_b64": _b64_encode(salt),
        "password_hash_b64": _b64_encode(digest),
    }


def verify_password(password: str, credential: Dict[str, Any]) -> bool:
    try:
        if credential.get("algorithm") != f"pbkdf2_hmac_{PBKDF2_ALGORITHM}":
            return False
        iterations = int(credential.get("iterations", 0))
        if iterations < 100_000:
            return False
        salt = _b64_decode(str(credential["salt_b64"]))
        expected = _b64_decode(str(credential["password_hash_b64"]))
        actual = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(expected, actual)
    except Exception:
        return False


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def load_credentials(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Credential file not found: {path}. Run --init first."
        )
    data = read_json(path)
    if data.get("version") != VERSION:
        raise ValueError("Unsupported credential file version")
    if data.get("safety_lock") != SAFETY_LOCK:
        raise ValueError("Credential safety lock mismatch")
    safe_user_id(str(data.get("user_id", "")))
    if "password" in data or "plain_password" in data:
        raise ValueError("Plaintext password key detected; refusing to use credentials")
    return data


def init_credentials(
    credential_file: Path,
    user_id: str,
    password: str,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    user_id = safe_user_id(user_id)
    if credential_file.exists() and not force:
        raise FileExistsError(
            f"Credential file already exists: {credential_file}. Use --force-reset to rotate."
        )
    password_block = hash_password(password)
    payload: Dict[str, Any] = {
        "version": VERSION,
        "created_at_utc": utc_now_iso(),
        "user_id": user_id,
        "credential_storage": "salted_pbkdf2_hash_only_no_plaintext_password",
        "password_block": password_block,
        "safety_lock": SAFETY_LOCK,
    }
    write_json_atomic(credential_file, payload)
    return payload


def append_session_ledger(path: Path, session: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "session_id",
        "login_status",
        "user_id",
        "login_time_utc",
        "workspace",
        "paper_only",
        "no_broker_execution",
        "no_real_orders",
        "no_auto_trading",
        "no_external_api",
    ]
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({key: session.get(key, "") for key in fieldnames})


def successful_session_payload(user_id: str, workspace: Path, credential_file: Path) -> Dict[str, Any]:
    return {
        "version": VERSION,
        "login_status": "LOGIN_PASS_LOCAL_GATE_ONLY",
        "session_id": secrets.token_hex(16),
        "user_id": user_id,
        "login_time_utc": utc_now_iso(),
        "workspace": str(workspace),
        "credential_file": str(credential_file),
        "post_login_state": "HQE_OPERATOR_GATE_OPEN_PAPER_ONLY",
        "allowed_next_actions": [
            "open local dashboard/control center",
            "run paper-only daily workflow",
            "read local evidence reports",
        ],
        "blocked_actions": [
            "broker execution",
            "real order placement",
            "auto trading",
            "option selling",
            "candidate tuning during validation",
            "external API calls from this login gate",
        ],
        "paper_only": True,
        "no_broker_execution": True,
        "no_real_orders": True,
        "no_auto_trading": True,
        "no_external_api": True,
        "safety_lock": SAFETY_LOCK,
    }


def login(
    credential_file: Path,
    workspace: Path,
    user_id: str,
    password: str,
    *,
    write_session: bool = True,
) -> Dict[str, Any]:
    creds = load_credentials(credential_file)
    expected_user = safe_user_id(str(creds["user_id"]))
    supplied_user = safe_user_id(user_id)
    if supplied_user != expected_user:
        return {
            "version": VERSION,
            "login_status": "LOGIN_DENIED",
            "reason": "USER_ID_MISMATCH",
            "safety_lock": SAFETY_LOCK,
        }
    if not verify_password(password, dict(creds["password_block"])):
        return {
            "version": VERSION,
            "login_status": "LOGIN_DENIED",
            "reason": "PASSWORD_MISMATCH",
            "safety_lock": SAFETY_LOCK,
        }
    session = successful_session_payload(expected_user, workspace, credential_file)
    if write_session:
        workspace.mkdir(parents=True, exist_ok=True)
        write_json_atomic(workspace / DEFAULT_SESSION_FILE_NAME, session)
        append_session_ledger(workspace / DEFAULT_SESSION_LEDGER_NAME, session)
    return session


def summarize_status(credential_file: Path, workspace: Path) -> Dict[str, Any]:
    credential_exists = credential_file.exists()
    session_file = workspace / DEFAULT_SESSION_FILE_NAME
    status: Dict[str, Any] = {
        "version": VERSION,
        "credential_file": str(credential_file),
        "credential_exists": credential_exists,
        "workspace": str(workspace),
        "session_file": str(session_file),
        "session_exists": session_file.exists(),
        "safety_lock": SAFETY_LOCK,
    }
    if credential_exists:
        try:
            creds = load_credentials(credential_file)
            status["configured_user_id"] = creds.get("user_id", "")
            status["credential_storage"] = creds.get("credential_storage", "")
        except Exception as exc:
            status["credential_error"] = str(exc)
    if session_file.exists():
        try:
            session = read_json(session_file)
            status["last_login_status"] = session.get("login_status", "")
            status["last_login_time_utc"] = session.get("login_time_utc", "")
            status["last_session_id"] = session.get("session_id", "")
        except Exception as exc:
            status["session_error"] = str(exc)
    return status


def _read_password_from_cli(args: argparse.Namespace, *, confirm: bool = False) -> str:
    if args.password_env:
        value = os.environ.get(args.password_env, "")
        if not value:
            raise ValueError(f"Environment variable is empty or missing: {args.password_env}")
        return value
    if args.password_stdin:
        value = sys.stdin.readline().rstrip("\n")
        if not value:
            raise ValueError("Password from stdin is empty")
        return value
    first = getpass.getpass("HQE local password: ")
    if confirm:
        second = getpass.getpass("Confirm HQE local password: ")
        if first != second:
            raise ValueError("Passwords do not match")
    return first


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HQE Module 147 local login shell")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init", action="store_true", help="Create local credentials with salted hash")
    mode.add_argument("--login", action="store_true", help="Login through local gate")
    mode.add_argument("--status", action="store_true", help="Print local login shell status")
    parser.add_argument("--user-id", default="", help="Local HQE login user id")
    parser.add_argument("--credential-file", default=str(DEFAULT_CREDENTIAL_FILE))
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--force-reset", action="store_true", help="Overwrite credential hash")
    parser.add_argument("--password-env", default="", help="Read password from named env var")
    parser.add_argument("--password-stdin", action="store_true", help="Read one password line from stdin")
    parser.add_argument("--no-write-session", action="store_true", help="Do not write session evidence")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    credential_file = Path(args.credential_file)
    workspace = Path(args.workspace)
    try:
        if args.status:
            result = summarize_status(credential_file, workspace)
        elif args.init:
            password = _read_password_from_cli(args, confirm=not (args.password_env or args.password_stdin))
            payload = init_credentials(
                credential_file,
                args.user_id,
                password,
                force=args.force_reset,
            )
            result = {
                "version": VERSION,
                "init_status": "LOCAL_LOGIN_CREDENTIALS_CREATED",
                "user_id": payload["user_id"],
                "credential_file": str(credential_file),
                "credential_storage": payload["credential_storage"],
                "safety_lock": SAFETY_LOCK,
            }
        else:
            password = _read_password_from_cli(args, confirm=False)
            result = login(
                credential_file,
                workspace,
                args.user_id,
                password,
                write_session=not args.no_write_session,
            )
        print(json.dumps(result, indent=2, sort_keys=True))
        if result.get("login_status") == "LOGIN_DENIED":
            return 2
        return 0
    except Exception as exc:
        result = {
            "version": VERSION,
            "status": "ERROR",
            "error": str(exc),
            "safety_lock": SAFETY_LOCK,
        }
        print(json.dumps(result, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

