"""
Inspect CSV Data

Validates whether a CSV file is compatible with Hunter Quant Engine candle
loading requirements.
"""

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "nifty_5min.csv"

REQUIRED_COLUMNS = (
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


@dataclass(frozen=True)
class CSVInspectionSummary:
    """
    Immutable CSV inspection summary.
    """

    csv_path: Path
    columns: tuple[str, ...]
    missing_columns: tuple[str, ...]
    extra_columns: tuple[str, ...]
    total_rows: int

    first_datetime: datetime | None
    last_datetime: datetime | None

    missing_values: int
    datetime_parse_errors: int
    numeric_parse_errors: int
    duplicate_datetimes: int
    unsorted_datetimes: int
    invalid_ohlc_rows: int
    valid_rows: int

    schema_compatible: bool
    ready_for_hqe: bool


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build command-line argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Inspect CSV candle data for HQE compatibility.",
    )

    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV_PATH),
        help="Path to CSV file to inspect.",
    )

    return parser


def inspect_csv(
    csv_path: str | Path,
) -> CSVInspectionSummary:
    """
    Inspect CSV candle data.

    Args:
        csv_path: Path to CSV file.

    Returns:
        Immutable CSVInspectionSummary.
    """
    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.DictReader(csv_file)
        columns = tuple(reader.fieldnames or ())

        missing_columns = tuple(
            column for column in REQUIRED_COLUMNS if column not in columns
        )
        extra_columns = tuple(
            column for column in columns if column not in REQUIRED_COLUMNS
        )

        total_rows = 0
        missing_values = 0
        datetime_parse_errors = 0
        numeric_parse_errors = 0
        duplicate_datetimes = 0
        unsorted_datetimes = 0
        invalid_ohlc_rows = 0
        valid_rows = 0

        first_datetime: datetime | None = None
        last_datetime: datetime | None = None
        previous_datetime: datetime | None = None
        seen_datetimes: set[datetime] = set()

        for row in reader:
            total_rows += 1
            row_has_error = bool(missing_columns)

            for column in columns:
                if row.get(column) in (None, ""):
                    missing_values += 1
                    row_has_error = True

            parsed_datetime = _parse_datetime(row)

            if parsed_datetime is None:
                datetime_parse_errors += 1
                row_has_error = True
            else:
                if first_datetime is None:
                    first_datetime = parsed_datetime

                last_datetime = parsed_datetime

                if parsed_datetime in seen_datetimes:
                    duplicate_datetimes += 1
                    row_has_error = True

                seen_datetimes.add(parsed_datetime)

                if (
                    previous_datetime is not None
                    and parsed_datetime < previous_datetime
                ):
                    unsorted_datetimes += 1
                    row_has_error = True

                previous_datetime = parsed_datetime

            numeric_values = _parse_numeric_values(row)

            if numeric_values is None:
                numeric_parse_errors += 1
                row_has_error = True
            elif not _has_valid_ohlc(numeric_values):
                invalid_ohlc_rows += 1
                row_has_error = True

            if not row_has_error:
                valid_rows += 1

    schema_compatible = not missing_columns
    ready_for_hqe = (
        schema_compatible
        and total_rows > 0
        and valid_rows == total_rows
        and missing_values == 0
        and datetime_parse_errors == 0
        and numeric_parse_errors == 0
        and duplicate_datetimes == 0
        and unsorted_datetimes == 0
        and invalid_ohlc_rows == 0
    )

    return CSVInspectionSummary(
        csv_path=path,
        columns=columns,
        missing_columns=missing_columns,
        extra_columns=extra_columns,
        total_rows=total_rows,
        first_datetime=first_datetime,
        last_datetime=last_datetime,
        missing_values=missing_values,
        datetime_parse_errors=datetime_parse_errors,
        numeric_parse_errors=numeric_parse_errors,
        duplicate_datetimes=duplicate_datetimes,
        unsorted_datetimes=unsorted_datetimes,
        invalid_ohlc_rows=invalid_ohlc_rows,
        valid_rows=valid_rows,
        schema_compatible=schema_compatible,
        ready_for_hqe=ready_for_hqe,
    )


def _parse_datetime(
    row: dict[str, str],
) -> datetime | None:
    value = row.get("datetime")

    if value in (None, ""):
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_numeric_values(
    row: dict[str, str],
) -> dict[str, float] | None:
    values: dict[str, float] = {}

    for column in ("open", "high", "low", "close", "volume"):
        value = row.get(column)

        if value in (None, ""):
            return None

        try:
            values[column] = float(value)
        except ValueError:
            return None

    return values


def _has_valid_ohlc(
    values: dict[str, float],
) -> bool:
    open_price = values["open"]
    high = values["high"]
    low = values["low"]
    close = values["close"]
    volume = values["volume"]

    if open_price <= 0 or high <= 0 or low <= 0 or close <= 0:
        return False

    if volume < 0:
        return False

    if high < low:
        return False

    if high < open_price or high < close:
        return False

    if low > open_price or low > close:
        return False

    return True


def format_metric(
    label: str,
    value,
) -> str:
    """
    Format a metric line.

    Args:
        label: Metric label.
        value: Metric value.

    Returns:
        Formatted metric line.
    """
    return f"{label}: {value}"


def build_report(
    summary: CSVInspectionSummary,
) -> str:
    """
    Build human-readable CSV inspection report.

    Args:
        summary: Immutable CSV inspection summary.

    Returns:
        Multiline report string.
    """
    lines = [
        "",
        "============================================================",
        "Hunter Quant Engine - CSV Inspection Report",
        "============================================================",
        format_metric("CSV", summary.csv_path),
        "------------------------------------------------------------",
        "SCHEMA",
        "------------------------------------------------------------",
        format_metric("Columns", summary.columns),
        format_metric("Missing Columns", summary.missing_columns),
        format_metric("Extra Columns", summary.extra_columns),
        format_metric("Schema Compatible", summary.schema_compatible),
        "------------------------------------------------------------",
        "DATA RANGE",
        "------------------------------------------------------------",
        format_metric("Total Rows", summary.total_rows),
        format_metric("Valid Rows", summary.valid_rows),
        format_metric("First Datetime", summary.first_datetime),
        format_metric("Last Datetime", summary.last_datetime),
        "------------------------------------------------------------",
        "QUALITY CHECKS",
        "------------------------------------------------------------",
        format_metric("Missing Values", summary.missing_values),
        format_metric("Datetime Parse Errors", summary.datetime_parse_errors),
        format_metric("Numeric Parse Errors", summary.numeric_parse_errors),
        format_metric("Duplicate Datetimes", summary.duplicate_datetimes),
        format_metric("Unsorted Datetimes", summary.unsorted_datetimes),
        format_metric("Invalid OHLC Rows", summary.invalid_ohlc_rows),
        "------------------------------------------------------------",
        format_metric("Ready For HQE", summary.ready_for_hqe),
        "============================================================",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    """
    Inspect CSV data and print report.
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    summary = inspect_csv(args.csv)

    print(build_report(summary))


if __name__ == "__main__":
    main()
