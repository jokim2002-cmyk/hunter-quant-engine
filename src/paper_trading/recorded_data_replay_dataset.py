"""
Recorded data replay dataset normalizer.

Evidence-only scaffold for turning discovered recorded market-data files into a
simple, normalized replay dataset. This module never connects to a broker, never
requests live market data, and never places orders.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SUPPORTED_REPLAY_SUFFIXES = {".csv", ".json", ".jsonl", ".parquet"}

TIMESTAMP_KEYS = {
    "timestamp",
    "time",
    "datetime",
    "date",
    "ts",
    "candle_time",
    "bar_time",
}
OPEN_KEYS = {"open", "o", "open_price"}
HIGH_KEYS = {"high", "h", "high_price"}
LOW_KEYS = {"low", "l", "low_price"}
CLOSE_KEYS = {"close", "c", "close_price", "price", "ltp", "last"}
VOLUME_KEYS = {"volume", "vol", "v", "qty", "quantity"}


@dataclass(frozen=True)
class ReplayRecord:
    """A normalized OHLCV replay row when fields are available."""

    source_path: str
    source_type: str
    row_number: int
    timestamp: str | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    missing_fields: list[str]


@dataclass(frozen=True)
class ReplaySourceSummary:
    """Per-source parsing summary for operator evidence reports."""

    path: str
    file_type: str
    status: str
    discovered_records: int
    normalized_records: int
    skipped_records: int
    message: str


@dataclass(frozen=True)
class ReplayDatasetReport:
    """Replay dataset report object written to disk by the CLI."""

    generated_at_utc: str
    source_count: int
    normalized_record_count: int
    output_directory: str
    safety_notice: str
    sources: list[ReplaySourceSummary]
    records: list[ReplayRecord]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This replay dataset normalizer does not "
        "connect to brokers, request live market data, place real orders, handle "
        "real money, or prove profitability."
    )


def _normalize_key(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "_")
    )


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def _as_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _value_for(row: Mapping[str, Any], possible_keys: set[str]) -> Any:
    normalized = {_normalize_key(str(key)): value for key, value in row.items()}
    for possible_key in possible_keys:
        if possible_key in normalized:
            return normalized[possible_key]
    return None


def normalize_mapping(
    row: Mapping[str, Any],
    *,
    source_path: str,
    source_type: str,
    row_number: int,
) -> ReplayRecord | None:
    """Normalize one mapping into a replay record when at least one field exists."""

    timestamp = _as_timestamp(_value_for(row, TIMESTAMP_KEYS))
    open_price = _as_float(_value_for(row, OPEN_KEYS))
    high_price = _as_float(_value_for(row, HIGH_KEYS))
    low_price = _as_float(_value_for(row, LOW_KEYS))
    close_price = _as_float(_value_for(row, CLOSE_KEYS))
    volume = _as_float(_value_for(row, VOLUME_KEYS))

    values = {
        "timestamp": timestamp,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
    }
    if all(value is None for value in values.values()):
        return None

    missing_fields = [
        field_name for field_name, field_value in values.items() if field_value is None
    ]

    return ReplayRecord(
        source_path=source_path,
        source_type=source_type,
        row_number=row_number,
        timestamp=timestamp,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        missing_fields=missing_fields,
    )


def _read_csv_records(path: Path) -> tuple[list[ReplayRecord], int, int]:
    records: list[ReplayRecord] = []
    discovered = 0
    skipped = 0
    with path.open("r", encoding="utf-8-sig", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        for row_number, row in enumerate(reader, start=1):
            discovered += 1
            record = normalize_mapping(
                row,
                source_path=str(path),
                source_type="csv",
                row_number=row_number,
            )
            if record is None:
                skipped += 1
                continue
            records.append(record)
    return records, discovered, skipped


def _mapping_rows_from_json(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]

    if isinstance(payload, Mapping):
        for key in ("records", "data", "candles", "bars", "ohlcv"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]

        known_keys = (
            TIMESTAMP_KEYS | OPEN_KEYS | HIGH_KEYS | LOW_KEYS | CLOSE_KEYS | VOLUME_KEYS
        )
        if any(_normalize_key(str(key)) in known_keys for key in payload):
            return [payload]

    return []


def _read_json_records(path: Path) -> tuple[list[ReplayRecord], int, int]:
    with path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)

    rows = _mapping_rows_from_json(payload)
    records: list[ReplayRecord] = []
    skipped = 0
    for row_number, row in enumerate(rows, start=1):
        record = normalize_mapping(
            row,
            source_path=str(path),
            source_type="json",
            row_number=row_number,
        )
        if record is None:
            skipped += 1
            continue
        records.append(record)
    return records, len(rows), skipped


def _read_jsonl_records(path: Path) -> tuple[list[ReplayRecord], int, int]:
    records: list[ReplayRecord] = []
    discovered = 0
    skipped = 0
    with path.open("r", encoding="utf-8") as file_handle:
        for row_number, line in enumerate(file_handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                skipped += 1
                continue

            if not isinstance(payload, Mapping):
                skipped += 1
                continue

            discovered += 1
            record = normalize_mapping(
                payload,
                source_path=str(path),
                source_type="jsonl",
                row_number=row_number,
            )
            if record is None:
                skipped += 1
                continue
            records.append(record)
    return records, discovered, skipped


def normalize_file(path: Path) -> tuple[list[ReplayRecord], ReplaySourceSummary]:
    """Normalize a supported file into replay records with a source summary."""

    suffix = path.suffix.lower()
    if suffix == ".csv":
        records, discovered, skipped = _read_csv_records(path)
        summary = ReplaySourceSummary(
            path=str(path),
            file_type="csv",
            status="parsed",
            discovered_records=discovered,
            normalized_records=len(records),
            skipped_records=skipped,
            message="Parsed CSV rows with simple OHLCV field detection.",
        )
        return records, summary

    if suffix == ".json":
        records, discovered, skipped = _read_json_records(path)
        summary = ReplaySourceSummary(
            path=str(path),
            file_type="json",
            status="parsed",
            discovered_records=discovered,
            normalized_records=len(records),
            skipped_records=skipped,
            message="Parsed JSON list/object rows with simple OHLCV field detection.",
        )
        return records, summary

    if suffix == ".jsonl":
        records, discovered, skipped = _read_jsonl_records(path)
        summary = ReplaySourceSummary(
            path=str(path),
            file_type="jsonl",
            status="parsed",
            discovered_records=discovered,
            normalized_records=len(records),
            skipped_records=skipped,
            message="Parsed JSONL rows with simple OHLCV field detection.",
        )
        return records, summary

    if suffix == ".parquet":
        summary = ReplaySourceSummary(
            path=str(path),
            file_type="parquet",
            status="skipped",
            discovered_records=0,
            normalized_records=0,
            skipped_records=0,
            message=(
                "Parquet was discovered but parsing is intentionally deferred in "
                "this evidence scaffold."
            ),
        )
        return [], summary

    summary = ReplaySourceSummary(
        path=str(path),
        file_type=suffix.lstrip(".") or "unknown",
        status="skipped",
        discovered_records=0,
        normalized_records=0,
        skipped_records=0,
        message="Unsupported file type for replay normalization.",
    )
    return [], summary


def discover_recorded_files(roots: Sequence[Path]) -> list[Path]:
    """Discover supported recorded-data files from one or more roots."""

    discovered: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_REPLAY_SUFFIXES:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            discovered.append(path)
    return discovered


def _extract_paths_from_inventory_payload(payload: Any) -> list[str]:
    """Recursively extract likely file paths from a tolerant inventory schema."""

    path_keys = {"path", "file_path", "source_path", "recorded_path", "full_path"}
    paths: list[str] = []

    if isinstance(payload, Mapping):
        for key, value in payload.items():
            normalized_key = _normalize_key(str(key))
            if normalized_key in path_keys and isinstance(value, str):
                paths.append(value)
                continue
            paths.extend(_extract_paths_from_inventory_payload(value))

    if isinstance(payload, list):
        for item in payload:
            paths.extend(_extract_paths_from_inventory_payload(item))

    return paths


def paths_from_inventory(inventory_path: Path) -> list[Path]:
    """Read inventory JSON output and return discovered supported paths."""

    if not inventory_path.exists():
        return []

    with inventory_path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)

    inventory_dir = inventory_path.parent
    paths: list[Path] = []
    seen: set[Path] = set()

    for raw_path in _extract_paths_from_inventory_payload(payload):
        candidate = Path(raw_path)
        candidates = [candidate]
        if not candidate.is_absolute():
            candidates.append((inventory_dir / candidate).resolve())
            candidates.append((Path.cwd() / candidate).resolve())

        for possible_path in candidates:
            if possible_path.suffix.lower() not in SUPPORTED_REPLAY_SUFFIXES:
                continue
            if not possible_path.exists():
                continue
            resolved = possible_path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(possible_path)
            break

    return paths


def build_replay_dataset(
    *,
    inventory_path: Path,
    recorded_roots: Sequence[Path],
    output_dir: Path,
) -> ReplayDatasetReport:
    """Build a replay dataset report from inventory paths plus discovered files."""

    source_paths: list[Path] = []
    seen: set[Path] = set()

    for path in paths_from_inventory(inventory_path):
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            source_paths.append(path)

    for path in discover_recorded_files(recorded_roots):
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            source_paths.append(path)

    records: list[ReplayRecord] = []
    summaries: list[ReplaySourceSummary] = []

    for path in source_paths:
        try:
            source_records, source_summary = normalize_file(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, csv.Error) as exc:
            source_records = []
            source_summary = ReplaySourceSummary(
                path=str(path),
                file_type=path.suffix.lower().lstrip(".") or "unknown",
                status="error",
                discovered_records=0,
                normalized_records=0,
                skipped_records=0,
                message=f"Could not parse source safely: {exc}",
            )

        records.extend(source_records)
        summaries.append(source_summary)

    return ReplayDatasetReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        source_count=len(summaries),
        normalized_record_count=len(records),
        output_directory=str(output_dir),
        safety_notice=safety_notice(),
        sources=summaries,
        records=records,
    )


def _report_to_dict(report: ReplayDatasetReport) -> dict[str, Any]:
    data = asdict(report)
    data["sources"] = [asdict(source) for source in report.sources]
    data["records"] = [asdict(record) for record in report.records]
    return data


def write_replay_dataset(report: ReplayDatasetReport, output_dir: Path) -> dict[str, Path]:
    """Write replay dataset report files and return their paths."""

    output_dir.mkdir(parents=True, exist_ok=True)

    dataset_json = output_dir / "dataset.json"
    dataset_jsonl = output_dir / "dataset.jsonl"
    dataset_txt = output_dir / "dataset.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = _report_to_dict(report)
    dataset_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with dataset_jsonl.open("w", encoding="utf-8", newline="\n") as file_handle:
        for record in report.records:
            file_handle.write(json.dumps(asdict(record), sort_keys=True))
            file_handle.write("\n")

    lines = [
        "HQE Recorded Data Replay Dataset",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Source files scanned: {report.source_count}",
        f"Normalized replay records: {report.normalized_record_count}",
        "",
        "Source Summary:",
    ]

    if not report.sources:
        lines.append("- No supported recorded-data files were found.")
    else:
        for source in report.sources:
            lines.append(
                "- "
                f"{source.path} | {source.status} | "
                f"records={source.normalized_records}/{source.discovered_records} | "
                f"{source.message}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {dataset_json}",
            f"- {dataset_jsonl}",
            f"- {manifest_json}",
            "",
            "This report is not a profitability claim.",
        ]
    )
    dataset_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_replay_dataset",
        "generated_at_utc": report.generated_at_utc,
        "source_count": report.source_count,
        "normalized_record_count": report.normalized_record_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "dataset_json": str(dataset_json),
            "dataset_jsonl": str(dataset_jsonl),
            "dataset_txt": str(dataset_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "dataset_json": dataset_json,
        "dataset_jsonl": dataset_jsonl,
        "dataset_txt": dataset_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_replay_dataset(
    *,
    inventory_path: Path,
    recorded_roots: Sequence[Path],
    output_dir: Path,
) -> tuple[ReplayDatasetReport, dict[str, Path]]:
    report = build_replay_dataset(
        inventory_path=inventory_path,
        recorded_roots=recorded_roots,
        output_dir=output_dir,
    )
    outputs = write_replay_dataset(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a paper-only normalized replay dataset from recorded data."
    )
    parser.add_argument(
        "--inventory",
        default="reports/paper_trading/recorded_data_inventory/inventory.json",
        help="Path to recorded-data inventory JSON output.",
    )
    parser.add_argument(
        "--recorded-root",
        action="append",
        default=None,
        help=(
            "Recorded-data root to scan. Can be passed multiple times. "
            "Defaults to data/recorded and data/live_recording."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_replay_dataset",
        help="Directory where replay dataset reports are written.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    recorded_roots = (
        [Path(value) for value in args.recorded_root]
        if args.recorded_root
        else [Path("data/recorded"), Path("data/live_recording")]
    )
    report, outputs = build_and_write_replay_dataset(
        inventory_path=Path(args.inventory),
        recorded_roots=recorded_roots,
        output_dir=Path(args.output_dir),
    )

    print("HQE recorded data replay dataset built.")
    print(report.safety_notice)
    print(f"Source files scanned: {report.source_count}")
    print(f"Normalized replay records: {report.normalized_record_count}")
    print(f"Dataset report: {outputs['dataset_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
