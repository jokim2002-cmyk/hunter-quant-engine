from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
AUTH = SCRIPTS / "hqe_app_fyers_auth.py"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load_module():
    name = "hqe_app_fyers_auth_diagnostic_test"
    spec = importlib.util.spec_from_file_location(name, AUTH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.token = ""

    def set_token(self, token):
        self.token = token

    def generate_token(self):
        return self.response


def test_full_redirect_url_is_accepted():
    module = load_module()
    url = (
        "https://127.0.0.1/?auth_code=ABC123%2Fxyz"
        "&state=sample"
    )
    assert (
        module.normalize_authorization_code(url)
        == "ABC123/xyz"
    )


def test_rejected_exchange_surfaces_code_and_message(monkeypatch):
    module = load_module()
    session = FakeSession(
        {
            "s": "error",
            "code": -8,
            "message": "Invalid authorization code",
        }
    )
    monkeypatch.setattr(
        module,
        "_session_model",
        lambda *args: session,
    )

    try:
        module.exchange_auth_code(
            client_id="CLIENT-100",
            secret_key="SECRET-200",
            redirect_uri="https://127.0.0.1",
            auth_code="AUTH-300",
        )
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Rejected response was accepted.")

    assert "code=-8" in message
    assert "Invalid authorization code" in message
    assert "SECRET-200" not in message
    assert "AUTH-300" not in message


def test_success_saves_token_without_returning_it(
    monkeypatch,
):
    module = load_module()
    session = FakeSession(
        {
            "s": "ok",
            "code": 200,
            "access_token": "LIVE-SECRET-TOKEN",
        }
    )
    saved = {}

    monkeypatch.setattr(
        module,
        "_session_model",
        lambda *args: session,
    )
    monkeypatch.setattr(
        module,
        "merge_and_save",
        lambda **kwargs: saved.update(kwargs) or {
            "status": "READY"
        },
    )

    result = module.exchange_auth_code(
        client_id="CLIENT-100",
        secret_key="SECRET-200",
        redirect_uri="https://127.0.0.1",
        auth_code="AUTH-300",
    )

    assert result["status"] == "PASS"
    assert saved["access_token"] == "LIVE-SECRET-TOKEN"
    assert "LIVE-SECRET-TOKEN" not in str(result)


def test_app_displays_sanitized_exchange_detail():
    text = APP.read_text(encoding="utf-8-sig")
    assert "Token refresh failed: " in text
    assert "detail = str(exc).strip()" in text
    assert "detail.replace(secret_key" in text
    assert "detail.replace(auth_code" in text
