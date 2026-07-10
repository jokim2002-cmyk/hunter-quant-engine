from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_fyers_auth.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def reverse_bytes(data: bytes) -> bytes:
    return data[::-1]


def test_secure_record_roundtrip_without_plaintext(tmp_path):
    module = load("fyers_auth_roundtrip")
    path = tmp_path / "auth.dpapi"
    secret = "never-store-this-in-plaintext"
    module.save_auth_record(
        {
            "client_id": "CLIENT-123",
            "secret_key": secret,
            "redirect_uri": "https://127.0.0.1/callback",
            "access_token": "TOKEN-456",
        },
        path=path,
        protector=reverse_bytes,
    )
    assert secret.encode("utf-8") not in path.read_bytes()
    record = module.load_auth_record(path=path, unprotector=reverse_bytes)
    assert record["secret_key"] == secret
    assert record["access_token"] == "TOKEN-456"


def test_apply_environment_uses_secure_record(monkeypatch, tmp_path):
    module = load("fyers_auth_environment")
    path = tmp_path / "auth.dpapi"
    module.save_auth_record(
        {
            "client_id": "CLIENT-123",
            "secret_key": "SECRET-456",
            "redirect_uri": "https://127.0.0.1/callback",
            "access_token": "TOKEN-789",
        },
        path=path,
        protector=reverse_bytes,
    )
    original_load_auth_record = module.load_auth_record
    monkeypatch.setattr(
        module,
        "load_auth_record",
        lambda: original_load_auth_record(
            path=path,
            unprotector=reverse_bytes,
        ),
    )
    for key in (
        "FYERS_CLIENT_ID",
        "FYERS_SECRET_KEY",
        "FYERS_REDIRECT_URI",
        "FYERS_ACCESS_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)
    payload = module.apply_stored_fyers_environment(overwrite=True)
    assert payload["status"] == "APPLIED"
    assert os.environ["FYERS_CLIENT_ID"] == "CLIENT-123"
    assert os.environ["FYERS_ACCESS_TOKEN"] == "TOKEN-789"


def test_guard_keeps_execution_and_plaintext_storage_blocked():
    module = load("fyers_auth_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["plaintext_secret_storage"] is False
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["option_selling_enabled"] is False


def test_auth_status_never_returns_secret_values(monkeypatch):
    module = load("fyers_auth_status")
    monkeypatch.setattr(
        module,
        "load_auth_record",
        lambda: {
            "client_id": "CLIENT-123456",
            "secret_key": "TOP-SECRET",
            "redirect_uri": "https://127.0.0.1/callback",
            "access_token": "ACCESS-TOKEN",
        },
    )
    payload = module.auth_status_snapshot()
    rendered = json.dumps(payload)
    assert payload["status"] == "READY"
    assert "TOP-SECRET" not in rendered
    assert "ACCESS-TOKEN" not in rendered
    assert payload["secret_values_redacted"] is True


def test_app_contains_native_fyers_auth_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "apply_stored_fyers_environment" in text
    assert "auth_status_snapshot" in text
    assert "open_fyers_auth_dialog" in text
    assert "Fyers Login & Token Refresh" in text
    assert "Save Login Settings" in text
    assert "Open Fyers Login Page" in text
    assert "Exchange Auth Code" in text
    assert "Save Existing Access Token" in text
    assert "Clear Stored Login" in text
