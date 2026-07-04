"""
Generate FYERS Access Token Script Tests
"""

import json

import pytest

from scripts.generate_fyers_access_token import (
    DEFAULT_ACCESS_TOKEN_OUTPUT,
    DEFAULT_STATE,
    DEFAULT_TOKEN_RESPONSE_OUTPUT,
    ENV_CLIENT_ID,
    ENV_REDIRECT_URI,
    ENV_SECRET_KEY,
    FYERSAuthConfig,
    build_argument_parser,
    extract_access_token,
    load_auth_config_from_env,
    read_required_env,
    write_json_secret,
    write_text_secret,
)


def test_build_argument_parser_uses_expected_defaults():
    args = build_argument_parser().parse_args([])

    assert args.auth_code is None
    assert args.state == DEFAULT_STATE
    assert args.open_browser is False
    assert args.access_token_output == str(DEFAULT_ACCESS_TOKEN_OUTPUT)
    assert args.token_response_output == str(DEFAULT_TOKEN_RESPONSE_OUTPUT)


def test_build_argument_parser_accepts_custom_values():
    args = build_argument_parser().parse_args(
        [
            "--auth-code",
            "sample_auth_code",
            "--state",
            "custom-state",
            "--open-browser",
            "--access-token-output",
            "secrets/token.txt",
            "--token-response-output",
            "secrets/token.json",
        ]
    )

    assert args.auth_code == "sample_auth_code"
    assert args.state == "custom-state"
    assert args.open_browser is True
    assert args.access_token_output == "secrets/token.txt"
    assert args.token_response_output == "secrets/token.json"


def test_read_required_env_returns_value(monkeypatch):
    monkeypatch.setenv(
        "TEST_REQUIRED_ENV",
        "value",
    )

    assert read_required_env("TEST_REQUIRED_ENV") == "value"


def test_read_required_env_rejects_missing_value(monkeypatch):
    monkeypatch.delenv(
        "TEST_REQUIRED_ENV",
        raising=False,
    )

    with pytest.raises(ValueError):
        read_required_env("TEST_REQUIRED_ENV")


def test_load_auth_config_from_env(monkeypatch):
    monkeypatch.setenv(
        ENV_CLIENT_ID,
        "APP_ID-100",
    )
    monkeypatch.setenv(
        ENV_SECRET_KEY,
        "SECRET",
    )
    monkeypatch.setenv(
        ENV_REDIRECT_URI,
        "https://example.com/callback",
    )

    config = load_auth_config_from_env(
        state="state-1",
    )

    assert config == FYERSAuthConfig(
        client_id="APP_ID-100",
        secret_key="SECRET",
        redirect_uri="https://example.com/callback",
        state="state-1",
    )


def test_extract_access_token_returns_token():
    token = extract_access_token(
        {
            "access_token": "sample-token",
        }
    )

    assert token == "sample-token"


def test_extract_access_token_rejects_missing_token():
    with pytest.raises(ValueError):
        extract_access_token({})


def test_write_text_secret_writes_file(tmp_path):
    output_path = tmp_path / "secrets" / "token.txt"

    written_path = write_text_secret(
        output_path=output_path,
        value="secret-token",
    )

    assert written_path == output_path
    assert output_path.read_text(encoding="utf-8") == "secret-token"


def test_write_json_secret_writes_file(tmp_path):
    output_path = tmp_path / "secrets" / "token.json"

    written_path = write_json_secret(
        output_path=output_path,
        value={
            "access_token": "secret-token",
        },
    )

    assert written_path == output_path
    assert json.loads(output_path.read_text(encoding="utf-8")) == {
        "access_token": "secret-token",
    }
