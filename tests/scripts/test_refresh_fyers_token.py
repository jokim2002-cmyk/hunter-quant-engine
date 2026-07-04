"""
Tests for FYERS token refresh helper.
"""

from pathlib import Path

import pytest

from scripts.refresh_fyers_token import (
    build_token_generator_command,
    extract_auth_code,
    prepare_fyers_environment,
    read_optional_text,
)


def test_extract_auth_code_from_fyers_redirect_url():
    redirect_url = (
        "https://127.0.0.1/?s=ok&code=200&auth_code=abc.def.ghi"
        "&state=hqe-fyers-auth"
    )

    assert extract_auth_code(redirect_url) == "abc.def.ghi"


def test_extract_auth_code_rejects_missing_auth_code():
    with pytest.raises(ValueError, match="auth_code not found"):
        extract_auth_code("https://127.0.0.1/?s=ok&code=200")


def test_read_optional_text_strips_utf8_bom_and_whitespace(tmp_path: Path):
    path = tmp_path / "value.txt"
    path.write_text("\ufeff  hello  \n", encoding="utf-8")

    assert read_optional_text(path) == "hello"


def test_prepare_fyers_environment_reads_values_from_files(tmp_path: Path):
    client_id_file = tmp_path / "client_id.txt"
    redirect_uri_file = tmp_path / "redirect_uri.txt"
    secret_key_file = tmp_path / "secret_key.txt"

    client_id_file.write_text("APPID123-200", encoding="utf-8")
    redirect_uri_file.write_text("https://127.0.0.1", encoding="utf-8")
    secret_key_file.write_text("SECRET1234567890", encoding="utf-8")

    environment = prepare_fyers_environment(
        client_id_file=client_id_file,
        redirect_uri_file=redirect_uri_file,
        secret_key_file=secret_key_file,
        base_environment={},
    )

    assert environment["FYERS_CLIENT_ID"] == "APPID123-200"
    assert environment["FYERS_REDIRECT_URI"] == "https://127.0.0.1"
    assert environment["FYERS_SECRET_KEY"] == "SECRET1234567890"


def test_prepare_fyers_environment_rejects_secret_with_whitespace(tmp_path: Path):
    client_id_file = tmp_path / "client_id.txt"
    redirect_uri_file = tmp_path / "redirect_uri.txt"
    secret_key_file = tmp_path / "secret_key.txt"

    client_id_file.write_text("APPID123-200", encoding="utf-8")
    redirect_uri_file.write_text("https://127.0.0.1", encoding="utf-8")
    secret_key_file.write_text("BAD SECRET", encoding="utf-8")

    with pytest.raises(ValueError, match="contains whitespace"):
        prepare_fyers_environment(
            client_id_file=client_id_file,
            redirect_uri_file=redirect_uri_file,
            secret_key_file=secret_key_file,
            base_environment={},
        )


def test_build_token_generator_command_for_auth_code_exchange():
    command = build_token_generator_command(
        token_generator_script=Path("scripts/generate_fyers_access_token.py"),
        open_browser=False,
        auth_code="abc.def.ghi",
        access_token_output=Path("secrets/fyers_access_token.txt"),
        token_response_output=Path("secrets/fyers_token_response.json"),
    )

    assert command[1:] == [
        "scripts\\generate_fyers_access_token.py",
        "--auth-code",
        "abc.def.ghi",
        "--access-token-output",
        "secrets\\fyers_access_token.txt",
        "--token-response-output",
        "secrets\\fyers_token_response.json",
    ]


def test_build_token_generator_command_for_open_browser():
    command = build_token_generator_command(
        token_generator_script=Path("scripts/generate_fyers_access_token.py"),
        open_browser=True,
        auth_code=None,
        access_token_output=Path("secrets/fyers_access_token.txt"),
        token_response_output=Path("secrets/fyers_token_response.json"),
    )

    assert command[1:] == [
        "scripts\\generate_fyers_access_token.py",
        "--open-browser",
    ]
