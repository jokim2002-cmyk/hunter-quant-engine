"""
Option Premium Candle CSV Writer Tests
"""

import csv
from datetime import datetime
from pathlib import Path

import pytest

from src.backtesting.option_premium_candle_csv_loader import (
    OptionPremiumCandleCsvLoader,
)
from src.backtesting.option_premium_candle_csv_writer import (
    OptionPremiumCandleCsvWriter,
)
from src.models.option_premium_candle import OptionPremiumCandle


def _candle(timestamp, open=100, high=110, low=90, close=105, volume=1000):
    return OptionPremiumCandle(
        timestamp=timestamp,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def test_write_grouped_candles_writes_expected_header(tmp_path):
    writer = OptionPremiumCandleCsvWriter()
    csv_path = tmp_path / "nested" / "candles.csv"

    writer.write_grouped_candles(
        {
            "ABC": (
                _candle(datetime(2026, 7, 6, 9, 30)),
                _candle(datetime(2026, 7, 6, 10, 0)),
            ),
        },
        csv_path,
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[0] == ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
    assert rows[1][0] == "ABC"


def test_write_grouped_candles_creates_parent_directory(tmp_path):
    writer = OptionPremiumCandleCsvWriter()
    csv_path = tmp_path / "reports" / "subdir" / "candles.csv"

    writer.write_grouped_candles({"ABC": (_candle(datetime(2026, 7, 6, 9, 30)),)}, csv_path)

    assert csv_path.exists()
    assert csv_path.parent.exists()


def test_write_grouped_candles_sorts_symbols_alphabetically(tmp_path):
    writer = OptionPremiumCandleCsvWriter()
    csv_path = tmp_path / "candles.csv"

    writer.write_grouped_candles(
        {
            "ZED": (_candle(datetime(2026, 7, 6, 9, 30)),),
            "ABC": (_candle(datetime(2026, 7, 6, 9, 30)),),
        },
        csv_path,
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[1][0] == "ABC"
    assert rows[2][0] == "ZED"


def test_write_grouped_candles_sorts_candles_by_timestamp(tmp_path):
    writer = OptionPremiumCandleCsvWriter()
    csv_path = tmp_path / "candles.csv"

    writer.write_grouped_candles(
        {
            "ABC": (
                _candle(datetime(2026, 7, 6, 10, 0)),
                _candle(datetime(2026, 7, 6, 9, 0)),
            )
        },
        csv_path,
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[1][1] == "2026-07-06T09:00:00"
    assert rows[2][1] == "2026-07-06T10:00:00"


def test_write_grouped_candles_rejects_blank_symbol(tmp_path):
    writer = OptionPremiumCandleCsvWriter()

    with pytest.raises(ValueError, match="option premium candle symbol is required"):
        writer.write_grouped_candles({" ": (_candle(datetime(2026, 7, 6, 9, 30)),)}, tmp_path / "candles.csv")


def test_write_grouped_candles_rejects_empty_candle_sequence(tmp_path):
    writer = OptionPremiumCandleCsvWriter()

    with pytest.raises(ValueError, match="option premium candles are required for symbol: ABC"):
        writer.write_grouped_candles({"ABC": ()}, tmp_path / "candles.csv")


def test_append_candles_creates_file_with_header(tmp_path):
    writer = OptionPremiumCandleCsvWriter()
    csv_path = tmp_path / "candles.csv"

    writer.append_candles("ABC", (_candle(datetime(2026, 7, 6, 9, 30)),), csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[0] == ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
    assert rows[1][0] == "ABC"


def test_append_candles_appends_without_duplicating_header(tmp_path):
    writer = OptionPremiumCandleCsvWriter()
    csv_path = tmp_path / "candles.csv"

    writer.append_candles("ABC", (_candle(datetime(2026, 7, 6, 9, 30)),), csv_path)
    writer.append_candles("XYZ", (_candle(datetime(2026, 7, 6, 10, 30)),), csv_path)

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert len(rows) == 3
    assert rows[0] == ["symbol", "timestamp", "open", "high", "low", "close", "volume"]


def test_append_candles_sorts_appended_candles_by_timestamp(tmp_path):
    writer = OptionPremiumCandleCsvWriter()
    csv_path = tmp_path / "candles.csv"

    writer.append_candles(
        "ABC",
        (
            _candle(datetime(2026, 7, 6, 10, 0)),
            _candle(datetime(2026, 7, 6, 9, 0)),
        ),
        csv_path,
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[1][1] == "2026-07-06T09:00:00"
    assert rows[2][1] == "2026-07-06T10:00:00"


def test_written_csv_can_be_loaded_by_loader(tmp_path):
    writer = OptionPremiumCandleCsvWriter()
    csv_path = tmp_path / "candles.csv"

    writer.write_grouped_candles(
        {
            "ABC": (
                _candle(datetime(2026, 7, 6, 9, 30)),
                _candle(datetime(2026, 7, 6, 10, 0)),
            )
        },
        csv_path,
    )

    grouped = OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)

    assert set(grouped) == {"ABC"}
    assert len(grouped["ABC"]) == 2


def test_writer_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = Path(__file__).resolve().parents[1] / ".." / "src" / "backtesting" / "option_premium_candle_csv_writer.py"
    content = source.read_text(encoding="utf-8").lower()

    assert "fyers" not in content
