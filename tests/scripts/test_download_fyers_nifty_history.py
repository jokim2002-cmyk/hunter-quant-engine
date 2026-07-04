"""
Tests for FYERS NIFTY history downloader.
"""

from datetime import date
from pathlib import Path

import pytest

from scripts.download_fyers_nifty_history import (
    DEFAULT_SYMBOL,
    FyersCandle,
    build_history_request,
    candle_to_csv_row,
    default_from_date,
    default_to_date,
    extract_candles,
    read_required_text,
    write_hqe_csv,
)


def test_default_dates_use_30_day_window():
    today = date(2026, 7, 4)

    assert default_from_date(today) == "2026-06-04"
    assert default_to_date(today) == "2026-07-04"


def test_build_history_request_uses_fyers_payload_shape():
    payload = build_history_request(
        symbol=DEFAULT_SYMBOL,
        resolution="5",
        from_date="2026-06-01",
        to_date="2026-06-30",
    )

    assert payload == {
        "symbol": "NSE:NIFTY50-INDEX",
        "resolution": "5",
        "date_format": "1",
        "range_from": "2026-06-01",
        "range_to": "2026-06-30",
        "cont_flag": "1",
    }


def test_extract_candles_from_successful_response():
    response = {
        "s": "ok",
        "candles": [
            [0, 100.0, 110.0, 95.0, 105.0, 1000],
            [300, 105.0, 115.0, 100.0, 108.0, 1200],
        ],
    }

    candles = extract_candles(response)

    assert candles == [
        FyersCandle(
            timestamp=0,
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=1000.0,
        ),
        FyersCandle(
            timestamp=300,
            open=105.0,
            high=115.0,
            low=100.0,
            close=108.0,
            volume=1200.0,
        ),
    ]


def test_extract_candles_raises_on_error_response():
    response = {"s": "error", "message": "token expired"}

    with pytest.raises(ValueError, match="FYERS history request failed"):
        extract_candles(response)


def test_candle_to_csv_row_formats_ist_datetime():
    candle = FyersCandle(
        timestamp=0,
        open=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=1000.0,
    )

    row = candle_to_csv_row(candle, "Asia/Kolkata")

    assert row == [
        "1970-01-01 05:30:00",
        100.0,
        110.0,
        95.0,
        105.0,
        1000.0,
    ]


def test_write_hqe_csv_creates_expected_file(tmp_path: Path):
    output_path = tmp_path / "fyers_nifty_5min.csv"
    candles = [
        FyersCandle(
            timestamp=0,
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=1000.0,
        )
    ]

    write_hqe_csv(
        candles=candles,
        output_path=output_path,
        timezone_name="Asia/Kolkata",
    )

    assert output_path.read_text(encoding="utf-8").splitlines() == [
        "datetime,open,high,low,close,volume",
        "1970-01-01 05:30:00,100.0,110.0,95.0,105.0,1000.0",
    ]


def test_read_required_text_rejects_missing_file(tmp_path: Path):
    missing_path = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError):
        read_required_text(missing_path)


def test_read_required_text_rejects_empty_file(tmp_path: Path):
    empty_path = tmp_path / "empty.txt"
    empty_path.write_text("   ", encoding="utf-8")

    with pytest.raises(ValueError, match="Required file is empty"):
        read_required_text(empty_path)
