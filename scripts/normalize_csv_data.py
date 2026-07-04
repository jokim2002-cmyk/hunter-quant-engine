"""
Normalize CSV Data

Converts broker/data-provider CSV files into Hunter Quant Engine compatible
candle CSV format:

datetime,open,high,low,close,volume
"""

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "nifty_5min.csv"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "normalized_candles.csv"

OUTPUT_COLUMNS = (
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume",
)

COLUMN_ALIASES = {
    "datetime": (
        "datetime",
        "date_time",
        "date time",
        "timestamp",
        "time_stamp",
        "time stamp",
        "datetimeutc",
        "timestamputc",
    ),
    "date": (
        "date",
        "trade_date",
        "trade date",
    ),
    "time": (
        "time",
        "trade_time",
        "trade time",
    ),
    "open": (
        "open",
        "o",
    ),
    "high": (
        "high",
        "h",
    ),
    "low": (
        "low",
        "l",
    ),
    "close": (
        "close",
        "c",
        "ltp",
    ),
    "volume": (
        "volume",
        "vol",
        "v",
    ),
}

DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
)


@dataclass(frozen=True)
class NormalizationSummary:
    """
    Immutable CSV normalization summary.
    """

    input_path: Path
    output_path: Path
    rows_read: int
    rows_written: int
    input_columns: tuple[str, ...]
    datetime_column: str | None
    date_column: str | None
    time_column: str | None
    open_column: str
    high_column: str
    low_column: str
    close_column: str
    volume_column: str | None
    default_volume: float
    sorted_output: bool


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build command-line argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Normalize broker CSV candle data into HQE CSV format.",
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Input CSV path.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output HQE-compatible CSV path.",
    )
    parser.add_argument(
        "--datetime-column",
        default=None,
        help="Input datetime/timestamp column name.",
    )
    parser.add_argument(
        "--date-column",
        default=None,
        help="Input date column name when date and time are separate.",
    )
    parser.add_argument(
        "--time-column",
        default=None,
        help="Input time column name when date and time are separate.",
    )
    parser.add_argument(
        "--open-column",
        default=None,
        help="Input open column name.",
    )
    parser.add_argument(
        "--high-column",
        default=None,
        help="Input high column name.",
    )
    parser.add_argument(
        "--low-column",
        default=None,
        help="Input low column name.",
    )
    parser.add_argument(
        "--close-column",
        default=None,
        help="Input close column name.",
    )
    parser.add_argument(
        "--volume-column",
        default=None,
        help="Input volume column name.",
    )
    parser.add_argument(
        "--default-volume",
        type=float,
        default=0.0,
        help="Volume value used when no volume column exists.",
    )

    return parser


def normalize_csv(
    input_path: str | Path,
    output_path: str | Path,
    datetime_column: str | None = None,
    date_column: str | None = None,
    time_column: str | None = None,
    open_column: str | None = None,
    high_column: str | None = None,
    low_column: str | None = None,
    close_column: str | None = None,
    volume_column: str | None = None,
    default_volume: float = 0.0,
) -> NormalizationSummary:
    """
    Normalize input CSV into HQE-compatible candle CSV.

    Args:
        input_path: Input CSV path.
        output_path: Output CSV path.
        datetime_column: Optional explicit datetime column.
        date_column: Optional explicit date column.
        time_column: Optional explicit time column.
        open_column: Optional explicit open column.
        high_column: Optional explicit high column.
        low_column: Optional explicit low column.
        close_column: Optional explicit close column.
        volume_column: Optional explicit volume column.
        default_volume: Volume value used when no volume column exists.

    Returns:
        Immutable NormalizationSummary.
    """
    input_csv_path = Path(input_path)
    output_csv_path = Path(output_path)

    if not input_csv_path.exists():
        raise FileNotFoundError(f"Input CSV file not found: {input_csv_path}")

    with input_csv_path.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.DictReader(csv_file)
        input_columns = tuple(reader.fieldnames or ())

        resolved_open_column = _resolve_required_column(
            columns=input_columns,
            canonical_name="open",
            explicit_column=open_column,
        )
        resolved_high_column = _resolve_required_column(
            columns=input_columns,
            canonical_name="high",
            explicit_column=high_column,
        )
        resolved_low_column = _resolve_required_column(
            columns=input_columns,
            canonical_name="low",
            explicit_column=low_column,
        )
        resolved_close_column = _resolve_required_column(
            columns=input_columns,
            canonical_name="close",
            explicit_column=close_column,
        )
        resolved_volume_column = _resolve_optional_column(
            columns=input_columns,
            canonical_name="volume",
            explicit_column=volume_column,
        )

        resolved_datetime_column = _resolve_optional_column(
            columns=input_columns,
            canonical_name="datetime",
            explicit_column=datetime_column,
        )
        resolved_date_column = _resolve_optional_column(
            columns=input_columns,
            canonical_name="date",
            explicit_column=date_column,
        )
        resolved_time_column = _resolve_optional_column(
            columns=input_columns,
            canonical_name="time",
            explicit_column=time_column,
        )

        if resolved_datetime_column is None and resolved_date_column is None:
            raise ValueError(
                "Could not resolve datetime column. Provide --datetime-column "
                "or --date-column."
            )

        normalized_rows = []
        rows_read = 0

        for row in reader:
            rows_read += 1

            normalized_datetime = _resolve_datetime_value(
                row=row,
                datetime_column=resolved_datetime_column,
                date_column=resolved_date_column,
                time_column=resolved_time_column,
            )
            open_price = _parse_positive_float(
                row[resolved_open_column],
                resolved_open_column,
            )
            high = _parse_positive_float(
                row[resolved_high_column],
                resolved_high_column,
            )
            low = _parse_positive_float(
                row[resolved_low_column],
                resolved_low_column,
            )
            close = _parse_positive_float(
                row[resolved_close_column],
                resolved_close_column,
            )
            volume = _resolve_volume(
                row=row,
                volume_column=resolved_volume_column,
                default_volume=default_volume,
            )

            _validate_ohlc(
                open_price=open_price,
                high=high,
                low=low,
                close=close,
            )

            normalized_rows.append(
                {
                    "datetime": normalized_datetime.isoformat(),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }
            )

    normalized_rows.sort(key=lambda normalized_row: normalized_row["datetime"])

    output_csv_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_csv_path.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=OUTPUT_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(normalized_rows)

    return NormalizationSummary(
        input_path=input_csv_path,
        output_path=output_csv_path,
        rows_read=rows_read,
        rows_written=len(normalized_rows),
        input_columns=input_columns,
        datetime_column=resolved_datetime_column,
        date_column=resolved_date_column,
        time_column=resolved_time_column,
        open_column=resolved_open_column,
        high_column=resolved_high_column,
        low_column=resolved_low_column,
        close_column=resolved_close_column,
        volume_column=resolved_volume_column,
        default_volume=default_volume,
        sorted_output=True,
    )


def _resolve_required_column(
    columns: tuple[str, ...],
    canonical_name: str,
    explicit_column: str | None,
) -> str:
    resolved_column = _resolve_optional_column(
        columns=columns,
        canonical_name=canonical_name,
        explicit_column=explicit_column,
    )

    if resolved_column is None:
        raise ValueError(f"Could not resolve required column: {canonical_name}")

    return resolved_column


def _resolve_optional_column(
    columns: tuple[str, ...],
    canonical_name: str,
    explicit_column: str | None,
) -> str | None:
    if explicit_column is not None:
        if explicit_column not in columns:
            raise ValueError(
                f"Explicit column '{explicit_column}' was not found."
            )

        return explicit_column

    normalized_aliases = {
        _normalize_column_name(alias)
        for alias in COLUMN_ALIASES[canonical_name]
    }

    for column in columns:
        if _normalize_column_name(column) in normalized_aliases:
            return column

    return None


def _normalize_column_name(
    column_name: str,
) -> str:
    return "".join(
        character.lower()
        for character in column_name
        if character.isalnum()
    )


def _resolve_datetime_value(
    row: dict[str, str],
    datetime_column: str | None,
    date_column: str | None,
    time_column: str | None,
) -> datetime:
    if datetime_column is not None:
        return _parse_datetime(row[datetime_column])

    if date_column is None:
        raise ValueError("date_column is required when datetime_column is missing.")

    date_value = row[date_column]

    if time_column is None:
        return _parse_datetime(date_value)

    return _parse_datetime(f"{date_value} {row[time_column]}")


def _parse_datetime(
    value: str,
) -> datetime:
    cleaned_value = value.strip()

    try:
        return datetime.fromisoformat(cleaned_value)
    except ValueError:
        pass

    for datetime_format in DATETIME_FORMATS:
        try:
            return datetime.strptime(cleaned_value, datetime_format)
        except ValueError:
            continue

    raise ValueError(f"Could not parse datetime value: {value}")


def _parse_positive_float(
    value: str,
    column_name: str,
) -> float:
    parsed_value = float(value)

    if parsed_value <= 0:
        raise ValueError(f"{column_name} must be greater than zero.")

    return parsed_value


def _resolve_volume(
    row: dict[str, str],
    volume_column: str | None,
    default_volume: float,
) -> float:
    if volume_column is None:
        return default_volume

    volume = float(row[volume_column])

    if volume < 0:
        raise ValueError("volume must be greater than or equal to zero.")

    return volume


def _validate_ohlc(
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> None:
    if high < low:
        raise ValueError("high must be greater than or equal to low.")

    if high < open_price or high < close:
        raise ValueError("high must be greater than or equal to open and close.")

    if low > open_price or low > close:
        raise ValueError("low must be less than or equal to open and close.")


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
    summary: NormalizationSummary,
) -> str:
    """
    Build human-readable normalization report.

    Args:
        summary: Immutable NormalizationSummary.

    Returns:
        Multiline report string.
    """
    lines = [
        "",
        "============================================================",
        "Hunter Quant Engine - CSV Normalization Report",
        "================================================------------",
        format_metric("Input", summary.input_path),
        format_metric("Output", summary.output_path),
        "------------------------------------------------------------",
        format_metric("Rows Read", summary.rows_read),
        format_metric("Rows Written", summary.rows_written),
        format_metric("Input Columns", summary.input_columns),
        "------------------------------------------------------------",
        "COLUMN MAPPING",
        "------------------------------------------------------------",
        format_metric("Datetime Column", summary.datetime_column),
        format_metric("Date Column", summary.date_column),
        format_metric("Time Column", summary.time_column),
        format_metric("Open Column", summary.open_column),
        format_metric("High Column", summary.high_column),
        format_metric("Low Column", summary.low_column),
        format_metric("Close Column", summary.close_column),
        format_metric("Volume Column", summary.volume_column),
        format_metric("Default Volume", summary.default_volume),
        "------------------------------------------------------------",
        format_metric("Sorted Output", summary.sorted_output),
        "============================================================",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    """
    Normalize CSV data and print report.
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    summary = normalize_csv(
        input_path=args.input,
        output_path=args.output,
        datetime_column=args.datetime_column,
        date_column=args.date_column,
        time_column=args.time_column,
        open_column=args.open_column,
        high_column=args.high_column,
        low_column=args.low_column,
        close_column=args.close_column,
        volume_column=args.volume_column,
        default_volume=args.default_volume,
    )

    print(build_report(summary))


if __name__ == "__main__":
    main()
