"""
Normalize CSV Data Script Tests
"""

import csv
from datetime import datetime

import pytest

from scripts.normalize_csv_data import (
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_PATH,
    OUTPUT_COLUMNS,
    build_argument_parser,
    build_report,
    normalize_csv,
)


def _read_rows(csv_path):
    with csv_path.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        return tuple(csv.DictReader(csv_file))


def test_build_argument_parser_uses_expected_defaults():
    args = build_argument_parser().parse_args([])

    assert args.input == str(DEFAULT_INPUT_PATH)
    assert args.output == str(DEFAULT_OUTPUT_PATH)
    assert args.datetime_column is None
    assert args.date_column is None
    assert args.time_column is None
    assert args.default_volume == 0.0


def test_build_argument_parser_accepts_custom_values():
    args = build_argument_parser().parse_args(
        [
            "--input",
            "data/raw/broker.csv",
            "--output",
            "data/processed/hqe.csv",
            "--datetime-column",
            "Timestamp",
            "--open-column",
            "O",
            "--high-column",
            "H",
            "--low-column",
            "L",
            "--close-column",
            "C",
            "--volume-column",
            "V",
            "--default-volume",
            "10",
        ]
    )

    assert args.input == "data/raw/broker.csv"
    assert args.output == "data/processed/hqe.csv"
    assert args.datetime_column == "Timestamp"
    assert args.open_column == "O"
    assert args.high_column == "H"
    assert args.low_column == "L"
    assert args.close_column == "C"
    assert args.volume_column == "V"
    assert args.default_volume == 10.0


def test_normalize_csv_accepts_hqe_ready_schema(tmp_path):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = normalize_csv(
        input_path=input_path,
        output_path=output_path,
    )

    rows = _read_rows(output_path)

    assert summary.rows_read == 1
    assert summary.rows_written == 1
    assert summary.datetime_column == "datetime"
    assert summary.volume_column == "volume"
    assert tuple(rows[0].keys()) == OUTPUT_COLUMNS
    assert rows[0]["datetime"] == "2026-01-01T09:15:00"
    assert rows[0]["open"] == "100.0"
    assert rows[0]["high"] == "105.0"
    assert rows[0]["low"] == "95.0"
    assert rows[0]["close"] == "102.0"
    assert rows[0]["volume"] == "1000.0"


def test_normalize_csv_auto_detects_common_broker_columns(tmp_path):
    input_path = tmp_path / "broker.csv"
    output_path = tmp_path / "normalized.csv"

    input_path.write_text(
        "\n".join(
            [
                "Timestamp,O,H,L,C,V",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = normalize_csv(
        input_path=input_path,
        output_path=output_path,
    )

    rows = _read_rows(output_path)

    assert summary.datetime_column == "Timestamp"
    assert summary.open_column == "O"
    assert summary.high_column == "H"
    assert summary.low_column == "L"
    assert summary.close_column == "C"
    assert summary.volume_column == "V"
    assert rows[0]["datetime"] == "2026-01-01T09:15:00"


def test_normalize_csv_combines_date_and_time_columns(tmp_path):
    input_path = tmp_path / "date_time.csv"
    output_path = tmp_path / "normalized.csv"

    input_path.write_text(
        "\n".join(
            [
                "Date,Time,Open,High,Low,Close,Volume",
                "01-01-2026,09:15:00,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = normalize_csv(
        input_path=input_path,
        output_path=output_path,
    )

    rows = _read_rows(output_path)

    assert summary.datetime_column is None
    assert summary.date_column == "Date"
    assert summary.time_column == "Time"
    assert rows[0]["datetime"] == "2026-01-01T09:15:00"


def test_normalize_csv_uses_default_volume_when_volume_column_is_missing(tmp_path):
    input_path = tmp_path / "no_volume.csv"
    output_path = tmp_path / "normalized.csv"

    input_path.write_text(
        "\n".join(
            [
                "Timestamp,Open,High,Low,Close",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0",
            ]
        ),
        encoding="utf-8",
    )

    summary = normalize_csv(
        input_path=input_path,
        output_path=output_path,
        default_volume=50.0,
    )

    rows = _read_rows(output_path)

    assert summary.volume_column is None
    assert summary.default_volume == 50.0
    assert rows[0]["volume"] == "50.0"


def test_normalize_csv_sorts_output_by_datetime(tmp_path):
    input_path = tmp_path / "unsorted.csv"
    output_path = tmp_path / "normalized.csv"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:20:00,102.0,108.0,101.0,107.0,1200",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = normalize_csv(
        input_path=input_path,
        output_path=output_path,
    )

    rows = _read_rows(output_path)

    assert summary.sorted_output is True
    assert rows[0]["datetime"] == "2026-01-01T09:15:00"
    assert rows[1]["datetime"] == "2026-01-01T09:20:00"


def test_normalize_csv_supports_explicit_column_mapping(tmp_path):
    input_path = tmp_path / "custom.csv"
    output_path = tmp_path / "normalized.csv"

    input_path.write_text(
        "\n".join(
            [
                "When,Op,Hi,Lo,Cl,Qty",
                "2026/01/01 09:15:00,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = normalize_csv(
        input_path=input_path,
        output_path=output_path,
        datetime_column="When",
        open_column="Op",
        high_column="Hi",
        low_column="Lo",
        close_column="Cl",
        volume_column="Qty",
    )

    rows = _read_rows(output_path)

    assert summary.datetime_column == "When"
    assert rows[0]["datetime"] == datetime(2026, 1, 1, 9, 15).isoformat()


def test_normalize_csv_raises_for_missing_required_price_column(tmp_path):
    input_path = tmp_path / "missing_open.csv"
    output_path = tmp_path / "normalized.csv"

    input_path.write_text(
        "\n".join(
            [
                "datetime,high,low,close,volume",
                "2026-01-01T09:15:00,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        normalize_csv(
            input_path=input_path,
            output_path=output_path,
        )


def test_normalize_csv_raises_for_invalid_datetime(tmp_path):
    input_path = tmp_path / "bad_datetime.csv"
    output_path = tmp_path / "normalized.csv"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "bad-date,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        normalize_csv(
            input_path=input_path,
            output_path=output_path,
        )


def test_normalize_csv_raises_for_invalid_ohlc(tmp_path):
    input_path = tmp_path / "bad_ohlc.csv"
    output_path = tmp_path / "normalized.csv"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,99.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        normalize_csv(
            input_path=input_path,
            output_path=output_path,
        )


def test_normalize_csv_raises_for_missing_file(tmp_path):
    input_path = tmp_path / "missing.csv"
    output_path = tmp_path / "normalized.csv"

    with pytest.raises(FileNotFoundError):
        normalize_csv(
            input_path=input_path,
            output_path=output_path,
        )


def test_build_report_includes_expected_fields(tmp_path):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = normalize_csv(
        input_path=input_path,
        output_path=output_path,
    )

    report = build_report(summary)

    assert "Hunter Quant Engine - CSV Normalization Report" in report
    assert "Rows Read: 1" in report
    assert "Rows Written: 1" in report
    assert "Datetime Column: datetime" in report
    assert "Volume Column: volume" in report
    assert "Sorted Output: True" in report
