"""
Inspect CSV Data Script Tests
"""

from datetime import datetime
from pathlib import Path

import pytest

from scripts.inspect_csv_data import (
    DEFAULT_CSV_PATH,
    REQUIRED_COLUMNS,
    build_argument_parser,
    build_report,
    inspect_csv,
)


def test_build_argument_parser_uses_expected_defaults():
    args = build_argument_parser().parse_args([])

    assert args.csv == str(DEFAULT_CSV_PATH)


def test_build_argument_parser_accepts_custom_csv_path():
    args = build_argument_parser().parse_args(
        [
            "--csv",
            "data/raw/custom.csv",
        ]
    )

    assert args.csv == "data/raw/custom.csv"


def test_inspect_csv_reports_valid_hqe_ready_file(tmp_path):
    csv_path = tmp_path / "valid.csv"
    csv_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
                "2026-01-01T09:20:00,102.0,108.0,101.0,107.0,1200",
            ]
        ),
        encoding="utf-8",
    )

    summary = inspect_csv(csv_path)

    assert summary.csv_path == csv_path
    assert summary.columns == REQUIRED_COLUMNS
    assert summary.missing_columns == ()
    assert summary.extra_columns == ()
    assert summary.total_rows == 2
    assert summary.first_datetime == datetime(2026, 1, 1, 9, 15)
    assert summary.last_datetime == datetime(2026, 1, 1, 9, 20)
    assert summary.missing_values == 0
    assert summary.datetime_parse_errors == 0
    assert summary.numeric_parse_errors == 0
    assert summary.duplicate_datetimes == 0
    assert summary.unsorted_datetimes == 0
    assert summary.invalid_ohlc_rows == 0
    assert summary.valid_rows == 2
    assert summary.schema_compatible is True
    assert summary.ready_for_hqe is True


def test_inspect_csv_reports_missing_columns(tmp_path):
    csv_path = tmp_path / "missing_columns.csv"
    csv_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0",
            ]
        ),
        encoding="utf-8",
    )

    summary = inspect_csv(csv_path)

    assert summary.missing_columns == ("volume",)
    assert summary.schema_compatible is False
    assert summary.ready_for_hqe is False


def test_inspect_csv_reports_extra_columns(tmp_path):
    csv_path = tmp_path / "extra_columns.csv"
    csv_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume,source",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000,NSE",
            ]
        ),
        encoding="utf-8",
    )

    summary = inspect_csv(csv_path)

    assert summary.extra_columns == ("source",)
    assert summary.schema_compatible is True
    assert summary.ready_for_hqe is True


def test_inspect_csv_reports_datetime_parse_errors(tmp_path):
    csv_path = tmp_path / "bad_datetime.csv"
    csv_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "bad-date,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = inspect_csv(csv_path)

    assert summary.datetime_parse_errors == 1
    assert summary.valid_rows == 0
    assert summary.ready_for_hqe is False


def test_inspect_csv_reports_numeric_parse_errors(tmp_path):
    csv_path = tmp_path / "bad_numeric.csv"
    csv_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,abc,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = inspect_csv(csv_path)

    assert summary.numeric_parse_errors == 1
    assert summary.valid_rows == 0
    assert summary.ready_for_hqe is False


def test_inspect_csv_reports_missing_values(tmp_path):
    csv_path = tmp_path / "missing_values.csv"
    csv_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = inspect_csv(csv_path)

    assert summary.missing_values == 1
    assert summary.numeric_parse_errors == 1
    assert summary.valid_rows == 0
    assert summary.ready_for_hqe is False


def test_inspect_csv_reports_duplicate_datetimes(tmp_path):
    csv_path = tmp_path / "duplicate_datetime.csv"
    csv_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
                "2026-01-01T09:15:00,102.0,108.0,101.0,107.0,1200",
            ]
        ),
        encoding="utf-8",
    )

    summary = inspect_csv(csv_path)

    assert summary.duplicate_datetimes == 1
    assert summary.valid_rows == 1
    assert summary.ready_for_hqe is False


def test_inspect_csv_reports_unsorted_datetimes(tmp_path):
    csv_path = tmp_path / "unsorted_datetime.csv"
    csv_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:20:00,102.0,108.0,101.0,107.0,1200",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = inspect_csv(csv_path)

    assert summary.unsorted_datetimes == 1
    assert summary.valid_rows == 1
    assert summary.ready_for_hqe is False


def test_inspect_csv_reports_invalid_ohlc_rows(tmp_path):
    csv_path = tmp_path / "invalid_ohlc.csv"
    csv_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,99.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = inspect_csv(csv_path)

    assert summary.invalid_ohlc_rows == 1
    assert summary.valid_rows == 0
    assert summary.ready_for_hqe is False


def test_inspect_csv_raises_file_not_found_for_missing_file(tmp_path):
    csv_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        inspect_csv(csv_path)


def test_build_report_includes_required_sections(tmp_path):
    csv_path = tmp_path / "valid.csv"
    csv_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = inspect_csv(csv_path)
    report = build_report(summary)

    assert "Hunter Quant Engine - CSV Inspection Report" in report
    assert "SCHEMA" in report
    assert "DATA RANGE" in report
    assert "QUALITY CHECKS" in report
    assert "Ready For HQE: True" in report
    assert "Total Rows: 1" in report
    assert "Valid Rows: 1" in report
