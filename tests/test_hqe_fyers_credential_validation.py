from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_fyers_credential_validation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hqe_fyers_credential_validation_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_secret_hygiene_pass():
    module = load_module()
    payload = module.inspect_secret("X", "abc123")
    assert payload["present"] is True
    assert payload["hygiene_status"] == "PASS"
    assert payload["fingerprint"] != "abc123"


def test_secret_hygiene_detects_quotes_and_spaces():
    module = load_module()
    payload = module.inspect_secret("X", '  "abc123"  ')
    assert payload["leading_or_trailing_whitespace"] is True
    assert payload["wrapped_in_quotes"] is True
    assert payload["hygiene_status"].startswith("SUSPECT_")


def test_auth_minus_16_classification():
    module = load_module()
    client = module.inspect_secret("CLIENT", "client")
    token = module.inspect_secret("TOKEN", "token")
    payload = module.classify(
        client,
        token,
        {"code": -16, "message": "Could not authenticate the user"},
    )
    assert payload["auth_status"] == "AUTH_FAILED_CODE_-16"


def test_missing_credentials_classification():
    module = load_module()
    client = module.inspect_secret("CLIENT", None)
    token = module.inspect_secret("TOKEN", None)
    payload = module.classify(client, token, {})
    assert payload["auth_status"] == "CREDENTIALS_MISSING"
