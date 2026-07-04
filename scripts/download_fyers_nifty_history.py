"""
FYERS NIFTY History Downloader

Downloads NIFTY 5-minute historical candles from FYERS History API and writes
them in Hunter Quant Engine CSV format.
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


DEFAULT_SYMBOL = "NSE:NIFTY50-INDEX"
DEFAULT_RESOLUTION = "5"
DEFAULT_DATE_FORMAT = "1"
DEFAULT_CONT_FLAG = "1"
DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_TOKEN_PATH = Path("secrets/fyers_access_token.txt")
DEFAULT_OUTPUT_PATH = Path("data/raw/fyers_nifty_5min.csv")


@dataclass(frozen=True)
class FyersCandle:
    """
    Represents one FYERS candle.

    FYERS candle format:
    [timestamp, open, high, low, close, volume]
    """

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def default_from_date(today: date | None = None) -> str:
    """
    Return default from-date as 30 calendar days before today.
    """

    current_date = today or date.today()
    return (current_date - timedelta(days=30)).isoformat()


def default_to_date(today: date | None = None) -> str:
    """
    Return default to-date as today.
    """

    current_date = today or date.today()
    return current_date.isoformat()


def read_required_text(path: Path) -> str:
    """
    Read a required text file and return stripped content.
    """

    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    value = path.read_text(encoding="utf-8").strip()

    if not value:
        raise ValueError(f"Required file is empty: {path}")

    return value


def resolve_client_id(cli_client_id: str | None) -> str:
    """
    Resolve FYERS client/app ID from CLI argument or environment.
    """

    client_id = (cli_client_id or os.environ.get("FYERS_CLIENT_ID") or "").strip()

    if not client_id:
        raise ValueError(
            "FYERS client ID missing. Pass --client-id or set FYERS_CLIENT_ID."
        )

    return client_id


def build_history_request(
    *,
    symbol: str,
    resolution: str,
    from_date: str,
    to_date: str,
    date_format: str = DEFAULT_DATE_FORMAT,
    cont_flag: str = DEFAULT_CONT_FLAG,
) -> dict[str, str]:
    """
    Build FYERS History API request payload.
    """

    return {
        "symbol": symbol,
        "resolution": resolution,
        "date_format": date_format,
        "range_from": from_date,
        "range_to": to_date,
        "cont_flag": cont_flag,
    }


def create_fyers_history_client(*, client_id: str, access_token: str) -> Any:
    """
    Create FYERS API client.

    Import is intentionally inside the function so tests do not need fyers-apiv3.
    """

    try:
        from fyers_apiv3 import fyersModel
    except ImportError as exc:
        raise ImportError(
            "fyers-apiv3 is not installed. Run: py -m pip install fyers-apiv3"
        ) from exc

    return fyersModel.FyersModel(
        client_id=client_id,
        token=access_token,
        is_async=False,
        log_path="",
    )


def download_history_response(client: Any, request_payload: dict[str, str]) -> dict[str, Any]:
    """
    Download history response from FYERS client.
    """

    response = client.history(data=request_payload)

    if not isinstance(response, dict):
        raise ValueError(f"Unexpected FYERS response type: {type(response).__name__}")

    return response


def extract_candles(response: dict[str, Any]) -> list[FyersCandle]:
    """
    Extract and validate FYERS candles from response.
    """

    if response.get("s") != "ok":
        raise ValueError(f"FYERS history request failed: {response}")

    raw_candles = response.get("candles")

    if not isinstance(raw_candles, list):
        raise ValueError(f"FYERS candles not found in response: {response}")

    candles: list[FyersCandle] = []

    for row in raw_candles:
        if not isinstance(row, list) or len(row) != 6:
            raise ValueError(f"Invalid FYERS candle row: {row}")

        candles.append(
            FyersCandle(
                timestamp=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
        )

    return candles


def format_timestamp(timestamp: int, timezone_name: str) -> str:
    """
    Format FYERS epoch timestamp into local datetime string.
    """

    local_timezone = ZoneInfo(timezone_name)

    return (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        .astimezone(local_timezone)
        .strftime("%Y-%m-%d %H:%M:%S")
    )


def candle_to_csv_row(candle: FyersCandle, timezone_name: str) -> list[Any]:
    """
    Convert FYERS candle to HQE CSV row.
    """

    return [
        format_timestamp(candle.timestamp, timezone_name),
        candle.open,
        candle.high,
        candle.low,
        candle.close,
        candle.volume,
    ]


def write_hqe_csv(
    *,
    candles: list[FyersCandle],
    output_path: Path,
    timezone_name: str,
) -> None:
    """
    Write candles to HQE-compatible CSV.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["datetime", "open", "high", "low", "close", "volume"])

        for candle in candles:
            writer.writerow(candle_to_csv_row(candle, timezone_name))


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Download FYERS NIFTY 5-minute history CSV."
    )

    parser.add_argument(
        "--client-id",
        default=None,
        help="FYERS app/client ID. Defaults to FYERS_CLIENT_ID env var.",
    )
    parser.add_argument(
        "--access-token-path",
        default=str(DEFAULT_TOKEN_PATH),
        help="Path to FYERS access token text file.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--symbol",
        default=DEFAULT_SYMBOL,
        help="FYERS symbol.",
    )
    parser.add_argument(
        "--resolution",
        default=DEFAULT_RESOLUTION,
        help="Candle resolution. Use 5 for 5-minute candles.",
    )
    parser.add_argument(
        "--from-date",
        default=default_from_date(),
        help="Start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--to-date",
        default=default_to_date(),
        help="End date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help="Output datetime timezone.",
    )

    return parser.parse_args()


def main() -> None:
    """
    Download FYERS history and write HQE CSV.
    """

    args = parse_args()

    client_id = resolve_client_id(args.client_id)
    access_token = read_required_text(Path(args.access_token_path))

    request_payload = build_history_request(
        symbol=args.symbol,
        resolution=args.resolution,
        from_date=args.from_date,
        to_date=args.to_date,
    )

    client = create_fyers_history_client(
        client_id=client_id,
        access_token=access_token,
    )

    response = download_history_response(client, request_payload)
    candles = extract_candles(response)

    write_hqe_csv(
        candles=candles,
        output_path=Path(args.output),
        timezone_name=args.timezone,
    )

    print(f"Downloaded candles: {len(candles)}")
    print(f"Symbol: {args.symbol}")
    print(f"Resolution: {args.resolution}")
    print(f"Range: {args.from_date} to {args.to_date}")
    print(f"Output CSV: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
