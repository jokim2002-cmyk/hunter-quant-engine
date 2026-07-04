"""
FYERS Token Refresh Helper

Guided helper for refreshing FYERS access tokens from local secret files.
It opens the FYERS login flow, then reads the redirect URL and delegates token
generation to scripts/generate_fyers_access_token.py.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Mapping
from urllib.parse import unquote


DEFAULT_CLIENT_ID_FILE = Path("secrets/fyers_client_id.txt")
DEFAULT_REDIRECT_URI_FILE = Path("secrets/fyers_redirect_uri.txt")
DEFAULT_SECRET_KEY_FILE = Path("secrets/fyers_secret_key.txt")
DEFAULT_REDIRECT_URL_FILE = Path("secrets/fyers_redirect_url.txt")
DEFAULT_TOKEN_GENERATOR_SCRIPT = Path("scripts/generate_fyers_access_token.py")
DEFAULT_ACCESS_TOKEN_OUTPUT = Path("secrets/fyers_access_token.txt")
DEFAULT_TOKEN_RESPONSE_OUTPUT = Path("secrets/fyers_token_response.json")
DEFAULT_REDIRECT_URI = "https://127.0.0.1"

AUTH_CODE_PATTERN = re.compile(r"[?&]auth_code=([^&\s]+)")


def read_optional_text(path: Path) -> str:
    """
    Read optional text from a file, stripping UTF-8 BOM and whitespace.
    """

    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8-sig").strip()


def read_required_text(path: Path, label: str) -> str:
    """
    Read required text from a file.
    """

    value = read_optional_text(path)

    if not value:
        raise ValueError(f"{label} missing or empty: {path}")

    return value


def resolve_value(
    *,
    environment: Mapping[str, str],
    env_name: str,
    file_path: Path,
    label: str,
    fallback: str | None = None,
) -> str:
    """
    Resolve config value from environment, file, or fallback.
    """

    env_value = environment.get(env_name, "").strip()

    if env_value:
        return env_value

    file_value = read_optional_text(file_path)

    if file_value:
        return file_value

    if fallback is not None:
        return fallback

    raise ValueError(f"{label} missing. Set {env_name} or create {file_path}.")


def prepare_fyers_environment(
    *,
    client_id_file: Path,
    redirect_uri_file: Path,
    secret_key_file: Path,
    base_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """
    Build environment variables required by generate_fyers_access_token.py.
    """

    environment = dict(os.environ if base_environment is None else base_environment)

    client_id = resolve_value(
        environment=environment,
        env_name="FYERS_CLIENT_ID",
        file_path=client_id_file,
        label="FYERS client ID",
    )
    redirect_uri = resolve_value(
        environment=environment,
        env_name="FYERS_REDIRECT_URI",
        file_path=redirect_uri_file,
        label="FYERS redirect URI",
        fallback=DEFAULT_REDIRECT_URI,
    )
    secret_key = resolve_value(
        environment=environment,
        env_name="FYERS_SECRET_KEY",
        file_path=secret_key_file,
        label="FYERS secret key",
    )

    if re.search(r"\s", secret_key):
        raise ValueError(
            "FYERS secret key contains whitespace. "
            "Keep only the 16-character secret in secrets/fyers_secret_key.txt."
        )

    environment["FYERS_CLIENT_ID"] = client_id
    environment["FYERS_REDIRECT_URI"] = redirect_uri
    environment["FYERS_SECRET_KEY"] = secret_key

    return environment


def extract_auth_code(redirect_url: str) -> str:
    """
    Extract auth_code from FYERS redirect URL.
    """

    match = AUTH_CODE_PATTERN.search(redirect_url.strip())

    if not match:
        raise ValueError(
            "auth_code not found. Paste the full FYERS redirect URL containing "
            "auth_code=... into the redirect URL file."
        )

    return unquote(match.group(1))


def ensure_redirect_url_file(path: Path) -> None:
    """
    Ensure redirect URL file exists.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.write_text(
            "Paste full FYERS redirect URL here, then save and close Notepad.\n",
            encoding="utf-8",
        )


def open_redirect_url_editor(path: Path) -> None:
    """
    Open redirect URL file in a text editor.
    """

    ensure_redirect_url_file(path)

    print()
    print("Browser login complete hone ke baad:")
    print("1. Browser address bar ka full URL copy karo.")
    print(f"2. Is file me paste karo: {path}")
    print("3. Save karo, Notepad close karo.")
    print()

    if os.name == "nt":
        subprocess.run(["notepad.exe", str(path)], check=False)
        return

    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, str(path)], check=False)


def build_token_generator_command(
    *,
    token_generator_script: Path,
    open_browser: bool,
    auth_code: str | None,
    access_token_output: Path,
    token_response_output: Path,
) -> list[str]:
    """
    Build command for the existing FYERS token generator script.
    """

    command = [sys.executable, str(token_generator_script)]

    if open_browser:
        return command + ["--open-browser"]

    if not auth_code:
        raise ValueError("auth_code is required when open_browser is False.")

    return command + [
        "--auth-code",
        auth_code,
        "--access-token-output",
        str(access_token_output),
        "--token-response-output",
        str(token_response_output),
    ]


def run_command(command: list[str], environment: dict[str, str]) -> None:
    """
    Run a subprocess command and fail with its exit code.
    """

    completed = subprocess.run(command, env=environment, check=False)

    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def run_open_browser(
    *,
    token_generator_script: Path,
    environment: dict[str, str],
    access_token_output: Path,
    token_response_output: Path,
) -> None:
    """
    Open FYERS browser login URL using existing token generator.
    """

    command = build_token_generator_command(
        token_generator_script=token_generator_script,
        open_browser=True,
        auth_code=None,
        access_token_output=access_token_output,
        token_response_output=token_response_output,
    )
    run_command(command, environment)


def run_token_exchange(
    *,
    token_generator_script: Path,
    environment: dict[str, str],
    auth_code: str,
    access_token_output: Path,
    token_response_output: Path,
) -> None:
    """
    Exchange FYERS auth code for access token.
    """

    command = build_token_generator_command(
        token_generator_script=token_generator_script,
        open_browser=False,
        auth_code=auth_code,
        access_token_output=access_token_output,
        token_response_output=token_response_output,
    )
    run_command(command, environment)


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Guided FYERS access token refresh helper."
    )

    parser.add_argument(
        "--open-browser-only",
        action="store_true",
        help="Only open FYERS login URL, then exit.",
    )
    parser.add_argument(
        "--edit-redirect-url",
        action="store_true",
        help="Open redirect URL file in Notepad, then generate token.",
    )
    parser.add_argument(
        "--from-redirect-file",
        action="store_true",
        help="Read redirect URL file directly and generate token.",
    )
    parser.add_argument(
        "--from-redirect-url",
        default=None,
        help="Generate token from a full FYERS redirect URL string.",
    )
    parser.add_argument(
        "--client-id-file",
        default=str(DEFAULT_CLIENT_ID_FILE),
        help="File containing FYERS client/app ID.",
    )
    parser.add_argument(
        "--redirect-uri-file",
        default=str(DEFAULT_REDIRECT_URI_FILE),
        help="File containing FYERS redirect URI.",
    )
    parser.add_argument(
        "--secret-key-file",
        default=str(DEFAULT_SECRET_KEY_FILE),
        help="File containing FYERS secret key.",
    )
    parser.add_argument(
        "--redirect-url-file",
        default=str(DEFAULT_REDIRECT_URL_FILE),
        help="File containing full FYERS redirect URL.",
    )
    parser.add_argument(
        "--token-generator-script",
        default=str(DEFAULT_TOKEN_GENERATOR_SCRIPT),
        help="Existing token generator script path.",
    )
    parser.add_argument(
        "--access-token-output",
        default=str(DEFAULT_ACCESS_TOKEN_OUTPUT),
        help="Output path for plain access token.",
    )
    parser.add_argument(
        "--token-response-output",
        default=str(DEFAULT_TOKEN_RESPONSE_OUTPUT),
        help="Output path for full token response JSON.",
    )

    return parser.parse_args()


def main() -> None:
    """
    Run guided FYERS token refresh flow.
    """

    args = parse_args()

    client_id_file = Path(args.client_id_file)
    redirect_uri_file = Path(args.redirect_uri_file)
    secret_key_file = Path(args.secret_key_file)
    redirect_url_file = Path(args.redirect_url_file)
    token_generator_script = Path(args.token_generator_script)
    access_token_output = Path(args.access_token_output)
    token_response_output = Path(args.token_response_output)

    environment = prepare_fyers_environment(
        client_id_file=client_id_file,
        redirect_uri_file=redirect_uri_file,
        secret_key_file=secret_key_file,
    )

    if args.open_browser_only:
        run_open_browser(
            token_generator_script=token_generator_script,
            environment=environment,
            access_token_output=access_token_output,
            token_response_output=token_response_output,
        )
        return

    if args.from_redirect_url:
        redirect_url = args.from_redirect_url
    elif args.from_redirect_file:
        redirect_url = read_required_text(redirect_url_file, "FYERS redirect URL")
    elif args.edit_redirect_url:
        open_redirect_url_editor(redirect_url_file)
        redirect_url = read_required_text(redirect_url_file, "FYERS redirect URL")
    else:
        run_open_browser(
            token_generator_script=token_generator_script,
            environment=environment,
            access_token_output=access_token_output,
            token_response_output=token_response_output,
        )
        open_redirect_url_editor(redirect_url_file)
        redirect_url = read_required_text(redirect_url_file, "FYERS redirect URL")

    auth_code = extract_auth_code(redirect_url)

    print(f"Auth Code Found: {not not auth_code}")
    print(f"Auth Code Length: {len(auth_code)}")

    run_token_exchange(
        token_generator_script=token_generator_script,
        environment=environment,
        auth_code=auth_code,
        access_token_output=access_token_output,
        token_response_output=token_response_output,
    )


if __name__ == "__main__":
    main()

