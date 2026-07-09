from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hqe_local_login_shell.py"
sys.path.insert(0, str(SCRIPT.parent))

import hqe_local_login_shell as login_shell  # noqa: E402


def test_password_hash_uses_salt_and_verifies_without_plaintext() -> None:
    first = login_shell.hash_password("StrongPass123!", salt=b"a" * 32)
    second = login_shell.hash_password("StrongPass123!", salt=b"b" * 32)

    assert first["password_hash_b64"] != second["password_hash_b64"]
    assert login_shell.verify_password("StrongPass123!", first) is True
    assert login_shell.verify_password("WrongPass123!", first) is False
    assert "StrongPass123!" not in json.dumps(first)


def test_init_and_login_write_local_session_evidence(tmp_path: Path) -> None:
    credential_file = tmp_path / "creds" / "hqe_login.json"
    workspace = tmp_path / "workspace"

    payload = login_shell.init_credentials(
        credential_file,
        "jokim-local",
        "StrongPass123!",
    )
    assert payload["credential_storage"] == "salted_pbkdf2_hash_only_no_plaintext_password"
    assert credential_file.exists()
    assert "StrongPass123!" not in credential_file.read_text(encoding="utf-8")

    session = login_shell.login(
        credential_file,
        workspace,
        "jokim-local",
        "StrongPass123!",
    )

    assert session["login_status"] == "LOGIN_PASS_LOCAL_GATE_ONLY"
    assert session["paper_only"] is True
    assert session["no_broker_execution"] is True
    assert session["no_real_orders"] is True
    assert session["no_auto_trading"] is True
    assert session["no_external_api"] is True
    assert (workspace / login_shell.DEFAULT_SESSION_FILE_NAME).exists()
    assert (workspace / login_shell.DEFAULT_SESSION_LEDGER_NAME).exists()


def test_wrong_password_denied_and_no_success_session_written(tmp_path: Path) -> None:
    credential_file = tmp_path / "hqe_login.json"
    workspace = tmp_path / "workspace"
    login_shell.init_credentials(credential_file, "jokim-local", "StrongPass123!")

    denied = login_shell.login(
        credential_file,
        workspace,
        "jokim-local",
        "WrongPass123!",
    )

    assert denied["login_status"] == "LOGIN_DENIED"
    assert denied["reason"] == "PASSWORD_MISMATCH"
    assert not (workspace / login_shell.DEFAULT_SESSION_FILE_NAME).exists()


def test_cli_status_returns_safety_lock(tmp_path: Path) -> None:
    credential_file = tmp_path / "hqe_login.json"
    workspace = tmp_path / "workspace"

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--status",
            "--credential-file",
            str(credential_file),
            "--workspace",
            str(workspace),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(proc.stdout)
    assert data["version"] == login_shell.VERSION
    assert data["credential_exists"] is False
    assert data["safety_lock"]["paper_only"] is True
    assert data["safety_lock"]["no_broker_execution"] is True

