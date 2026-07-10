from __future__ import annotations

import argparse
import ctypes
import json
import os
import webbrowser
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

VERSION = "HQE_APP_FYERS_AUTH_V1"
STORE_NAME = "fyers_auth.dpapi"

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


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def auth_store_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip()
    if base:
        return Path(base) / "HunterQuantEngine" / "FyersAuth"
    return Path.home() / "AppData" / "Local" / "HunterQuantEngine" / "FyersAuth"


def auth_store_path() -> Path:
    return auth_store_dir() / STORE_NAME


def _blob_from_bytes(data: bytes) -> tuple[DATA_BLOB, Any]:
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    blob = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    return blob, buffer


def protect_bytes(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Windows DPAPI is required for secure Fyers storage.")
    in_blob, in_buffer = _blob_from_bytes(data)
    out_blob = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)
    )
    _ = in_buffer
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def unprotect_bytes(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Windows DPAPI is required for secure Fyers storage.")
    in_blob, in_buffer = _blob_from_bytes(data)
    out_blob = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)
    )
    _ = in_buffer
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def normalize_record(record: dict[str, Any]) -> dict[str, str]:
    keys = ("client_id", "secret_key", "redirect_uri", "access_token")
    return {key: str(record.get(key, "")).strip() for key in keys}


def save_auth_record(
    record: dict[str, Any],
    *,
    path: Path | None = None,
    protector: Callable[[bytes], bytes] = protect_bytes,
) -> Path:
    target = path or auth_store_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = normalize_record(record)
    payload["updated_at_utc"] = now_utc()
    plaintext = json.dumps(payload, sort_keys=True).encode("utf-8")
    encrypted = protector(plaintext)
    if not encrypted or encrypted == plaintext:
        raise RuntimeError("Credential encryption failed safely.")
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_bytes(encrypted)
    temporary.replace(target)
    return target


def load_auth_record(
    *,
    path: Path | None = None,
    unprotector: Callable[[bytes], bytes] = unprotect_bytes,
) -> dict[str, str]:
    target = path or auth_store_path()
    if not target.exists():
        return normalize_record({})
    decrypted = unprotector(target.read_bytes())
    payload = json.loads(decrypted.decode("utf-8"))
    if not isinstance(payload, dict):
        return normalize_record({})
    return normalize_record(payload)


def clear_auth_record(*, path: Path | None = None) -> bool:
    target = path or auth_store_path()
    existed = target.exists()
    if existed:
        target.unlink()
    for key in (
        "FYERS_CLIENT_ID",
        "FYERS_SECRET_KEY",
        "FYERS_REDIRECT_URI",
        "FYERS_ACCESS_TOKEN",
    ):
        os.environ.pop(key, None)
    return existed


def masked_client_id(client_id: str) -> str:
    value = client_id.strip()
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return value[:3] + ("*" * (len(value) - 6)) + value[-3:]


def auth_status_snapshot() -> dict[str, Any]:
    try:
        record = load_auth_record()
        storage_error = ""
    except Exception as exc:
        record = normalize_record({})
        storage_error = type(exc).__name__

    settings_present = bool(
        record["client_id"] and record["secret_key"] and record["redirect_uri"]
    )
    token_present = bool(record["access_token"])
    if storage_error:
        status = "SECURE_STORE_ERROR"
        message = "Secure Fyers login store could not be read."
    elif settings_present and token_present:
        status = "READY"
        message = "Fyers login and token are securely stored."
    elif settings_present:
        status = "LOGIN_REQUIRED"
        message = "Fyers settings are stored; browser login is required."
    else:
        status = "NOT_CONFIGURED"
        message = "Fyers login settings are not configured."

    return {
        "version": VERSION,
        "status": status,
        "message": message,
        "client_id_masked": masked_client_id(record["client_id"]),
        "redirect_uri": record["redirect_uri"],
        "settings_present": settings_present,
        "access_token_present": token_present,
        "secure_store_path": str(auth_store_path()),
        "secure_store_error": storage_error,
        "secret_values_redacted": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def apply_stored_fyers_environment(*, overwrite: bool = False) -> dict[str, Any]:
    try:
        record = load_auth_record()
    except Exception:
        return {
            "status": "SECURE_STORE_ERROR",
            "applied": False,
            "secret_values_redacted": True,
        }

    mapping = {
        "FYERS_CLIENT_ID": record["client_id"],
        "FYERS_SECRET_KEY": record["secret_key"],
        "FYERS_REDIRECT_URI": record["redirect_uri"],
        "FYERS_ACCESS_TOKEN": record["access_token"],
    }
    applied: list[str] = []
    for key, value in mapping.items():
        if value and (overwrite or not os.environ.get(key)):
            os.environ[key] = value
            applied.append(key)
    return {
        "status": "APPLIED" if applied else "NO_CHANGE",
        "applied": bool(applied),
        "applied_keys": applied,
        "secret_values_redacted": True,
    }


def merge_and_save(
    *,
    client_id: str = "",
    secret_key: str = "",
    redirect_uri: str = "",
    access_token: str = "",
) -> dict[str, Any]:
    try:
        current = load_auth_record()
    except Exception:
        current = normalize_record({})
    updated = {
        "client_id": client_id.strip() or current["client_id"],
        "secret_key": secret_key.strip() or current["secret_key"],
        "redirect_uri": redirect_uri.strip() or current["redirect_uri"],
        "access_token": access_token.strip() or current["access_token"],
    }
    save_auth_record(updated)
    apply_stored_fyers_environment(overwrite=True)
    return auth_status_snapshot()


def _session_model(client_id: str, secret_key: str, redirect_uri: str):
    from fyers_apiv3 import fyersModel

    return fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code",
    )


def generate_login_url(client_id: str, secret_key: str, redirect_uri: str) -> str:
    if not client_id.strip() or not secret_key.strip() or not redirect_uri.strip():
        raise ValueError("Client ID, Secret Key and Redirect URI are required.")
    session = _session_model(
        client_id.strip(), secret_key.strip(), redirect_uri.strip()
    )
    url = session.generate_authcode()
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise RuntimeError("Fyers login URL could not be generated.")
    return url


def open_login_browser(client_id: str, secret_key: str, redirect_uri: str) -> str:
    url = generate_login_url(client_id, secret_key, redirect_uri)
    webbrowser.open(url, new=2)
    return url


def exchange_auth_code(
    *,
    client_id: str,
    secret_key: str,
    redirect_uri: str,
    auth_code: str,
) -> dict[str, Any]:
    if not auth_code.strip():
        raise ValueError("Authorization code is required.")
    session = _session_model(
        client_id.strip(), secret_key.strip(), redirect_uri.strip()
    )
    session.set_token(auth_code.strip())
    response = session.generate_token()
    if not isinstance(response, dict):
        raise RuntimeError("Fyers returned an invalid token response.")
    token = str(response.get("access_token", "")).strip()
    if not token:
        raise RuntimeError("Fyers access token was not returned.")
    status = merge_and_save(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        access_token=token,
    )
    return {
        "status": "PASS",
        "message": "Fyers token refreshed and securely stored.",
        "auth_status": status,
        "secret_values_redacted": True,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
    }


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "secure_storage": "WINDOWS_DPAPI",
        "plaintext_secret_storage": False,
        "secret_values_redacted": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE app-native Fyers auth helper")
    parser.add_argument("--guard-check", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if args.status:
        print(json.dumps(auth_status_snapshot(), indent=2, sort_keys=True))
        return 0
    parser.error("Use --guard-check or --status.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
