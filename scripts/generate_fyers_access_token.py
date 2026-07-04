"""
Generate FYERS Access Token

Creates a browser login URL for FYERS API and exchanges the returned auth code
for an access token.

Sensitive values are read from environment variables:
- FYERS_CLIENT_ID
- FYERS_SECRET_KEY
- FYERS_REDIRECT_URI

Never commit generated token files.
"""

import argparse
import json
import os
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_STATE = "hqe-fyers-auth"
DEFAULT_ACCESS_TOKEN_OUTPUT = PROJECT_ROOT / "secrets" / "fyers_access_token.txt"
DEFAULT_TOKEN_RESPONSE_OUTPUT = PROJECT_ROOT / "secrets" / "fyers_token_response.json"

ENV_CLIENT_ID = "FYERS_CLIENT_ID"
ENV_SECRET_KEY = "FYERS_SECRET_KEY"
ENV_REDIRECT_URI = "FYERS_REDIRECT_URI"


@dataclass(frozen=True)
class FYERSAuthConfig:
    """
    Immutable FYERS auth config.
    """

    client_id: str
    secret_key: str
    redirect_uri: str
    state: str = DEFAULT_STATE
    response_type: str = "code"
    grant_type: str = "authorization_code"


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build command-line argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Generate FYERS API access token.",
    )

    parser.add_argument(
        "--auth-code",
        default=None,
        help="Auth code copied from FYERS redirect URL.",
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE,
        help="State value used in FYERS auth flow.",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open generated FYERS login URL in default browser.",
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

    return parser


def read_required_env(
    name: str,
) -> str:
    """
    Read required environment variable.

    Args:
        name: Environment variable name.

    Returns:
        Environment variable value.
    """
    value = os.environ.get(name, "").strip()

    if not value:
        raise ValueError(f"Missing required environment variable: {name}")

    return value


def load_auth_config_from_env(
    state: str = DEFAULT_STATE,
) -> FYERSAuthConfig:
    """
    Load FYERS auth config from environment variables.

    Args:
        state: Auth state value.

    Returns:
        Immutable FYERSAuthConfig.
    """
    return FYERSAuthConfig(
        client_id=read_required_env(ENV_CLIENT_ID),
        secret_key=read_required_env(ENV_SECRET_KEY),
        redirect_uri=read_required_env(ENV_REDIRECT_URI),
        state=state,
    )


def build_session_model(
    config: FYERSAuthConfig,
):
    """
    Build FYERS SessionModel.

    Args:
        config: FYERS auth config.

    Returns:
        FYERS SessionModel.
    """
    try:
        from fyers_apiv3 import fyersModel
    except ImportError as error:
        raise ImportError(
            "Missing dependency: fyers-apiv3. "
            "Install it with: py -m pip install fyers-apiv3"
        ) from error

    return fyersModel.SessionModel(
        client_id=config.client_id,
        redirect_uri=config.redirect_uri,
        response_type=config.response_type,
        state=config.state,
        secret_key=config.secret_key,
        grant_type=config.grant_type,
    )


def generate_auth_url(
    config: FYERSAuthConfig,
) -> str:
    """
    Generate FYERS browser login URL.

    Args:
        config: FYERS auth config.

    Returns:
        Login URL.
    """
    session = build_session_model(config)

    return session.generate_authcode()


def generate_token_response(
    config: FYERSAuthConfig,
    auth_code: str,
) -> dict[str, Any]:
    """
    Exchange auth code for access token response.

    Args:
        config: FYERS auth config.
        auth_code: Auth code copied from FYERS redirect URL.

    Returns:
        Token response dictionary.
    """
    session = build_session_model(config)
    session.set_token(auth_code)

    response = session.generate_token()

    if not isinstance(response, dict):
        raise ValueError(f"Unexpected FYERS token response: {response}")

    return response


def extract_access_token(
    token_response: dict[str, Any],
) -> str:
    """
    Extract access token from FYERS token response.

    Args:
        token_response: FYERS token response.

    Returns:
        Access token.
    """
    access_token = token_response.get("access_token", "")

    if not access_token:
        raise ValueError(f"Access token not found in response: {token_response}")

    return str(access_token)


def write_text_secret(
    output_path: str | Path,
    value: str,
) -> Path:
    """
    Write secret text to local file.

    Args:
        output_path: Output path.
        value: Secret value.

    Returns:
        Output path.
    """
    path = Path(output_path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        value,
        encoding="utf-8",
    )

    return path


def write_json_secret(
    output_path: str | Path,
    value: dict[str, Any],
) -> Path:
    """
    Write secret JSON to local file.

    Args:
        output_path: Output path.
        value: JSON value.

    Returns:
        Output path.
    """
    path = Path(output_path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return path


def main() -> None:
    """
    Generate FYERS auth URL or access token.
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    config = load_auth_config_from_env(
        state=args.state,
    )

    if args.auth_code is None:
        auth_url = generate_auth_url(config)

        print("Open this FYERS login URL:")
        print(auth_url)
        print()
        print("After login, copy the auth_code/code from the redirected URL.")
        print("Then run this script again with:")
        print('py scripts\\generate_fyers_access_token.py --auth-code "PASTE_AUTH_CODE"')

        if args.open_browser:
            webbrowser.open(
                auth_url,
                new=1,
            )

        return

    token_response = generate_token_response(
        config=config,
        auth_code=args.auth_code,
    )
    access_token = extract_access_token(token_response)

    access_token_path = write_text_secret(
        output_path=args.access_token_output,
        value=access_token,
    )
    token_response_path = write_json_secret(
        output_path=args.token_response_output,
        value=token_response,
    )

    print(f"Access token saved: {access_token_path}")
    print(f"Full token response saved: {token_response_path}")
    print("Do not commit files inside secrets/.")


if __name__ == "__main__":
    main()
