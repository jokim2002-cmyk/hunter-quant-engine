"""
Recorded Data Evidence Inventory

Scans local recorded/historical data folders and writes an evidence-readiness
inventory report.

Paper/evidence pipeline only.
No broker code. No live market data. No real orders.
This is not a profitability claim.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_RECORDED_DATA_ROOTS = (
    Path("data") / "recorded",
    Path("data") / "live_recording",
)
DEFAULT_RECORDED_DATA_INVENTORY_OUTPUT_DIR = (
    Path("reports") / "paper_trading" / "recorded_data_inventory"
)
SUPPORTED_RECORDED_DATA_SUFFIXES = (".csv", ".json", ".jsonl", ".parquet")


@dataclass(frozen=True)
class RecordedDataFileRecord:
    """
    One supported recorded-data file discovered locally.
    """

    path: str
    suffix: str
    size_bytes: int
    is_empty: bool


@dataclass(frozen=True)
class RecordedDataInventoryPaths:
    """
    Files written by the recorded-data inventory.
    """

    output_dir: Path
    inventory_json: Path
    inventory_text: Path
    manifest_json: Path


@dataclass(frozen=True)
class RecordedDataInventoryReport:
    """
    Recorded-data inventory report.
    """

    generated_at: str
    inventory_version: int
    inventory_source: str
    paper_evidence_pipeline_only: bool
    no_broker_orders: bool
    no_live_market_data: bool
    no_real_orders: bool
    not_a_profitability_claim: bool
    scanned_roots: tuple[str, ...]
    missing_roots: tuple[str, ...]
    supported_suffixes: tuple[str, ...]
    file_count: int
    empty_file_count: int
    total_size_bytes: int
    files: tuple[RecordedDataFileRecord, ...]
    passed: bool
    blocking_reasons: tuple[str, ...]


def run_recorded_data_inventory(
    data_roots: Iterable[str | Path] = DEFAULT_RECORDED_DATA_ROOTS,
    *,
    output_dir: str | Path = DEFAULT_RECORDED_DATA_INVENTORY_OUTPUT_DIR,
    generated_at: datetime | None = None,
) -> tuple[RecordedDataInventoryReport, RecordedDataInventoryPaths]:
    """
    Scan recorded-data roots and write inventory outputs.
    """
    report = build_recorded_data_inventory_report(
        data_roots,
        generated_at=generated_at,
    )
    paths = write_recorded_data_inventory_report(report, output_dir)
    return report, paths


def build_recorded_data_inventory_report(
    data_roots: Iterable[str | Path] = DEFAULT_RECORDED_DATA_ROOTS,
    *,
    generated_at: datetime | None = None,
) -> RecordedDataInventoryReport:
    """
    Build recorded-data inventory report.
    """
    roots = tuple(Path(root) for root in data_roots)
    generated = generated_at or datetime.now(timezone.utc)

    missing_roots = tuple(str(root) for root in roots if not root.exists())
    files = tuple(_discover_supported_files(roots))
    empty_file_count = sum(1 for record in files if record.is_empty)
    total_size_bytes = sum(record.size_bytes for record in files)

    blocking_reasons = _build_blocking_reasons(
        roots=roots,
        files=files,
        empty_file_count=empty_file_count,
    )

    return RecordedDataInventoryReport(
        generated_at=generated.isoformat(),
        inventory_version=1,
        inventory_source="recorded_data_evidence_inventory",
        paper_evidence_pipeline_only=True,
        no_broker_orders=True,
        no_live_market_data=True,
        no_real_orders=True,
        not_a_profitability_claim=True,
        scanned_roots=tuple(str(root) for root in roots),
        missing_roots=missing_roots,
        supported_suffixes=SUPPORTED_RECORDED_DATA_SUFFIXES,
        file_count=len(files),
        empty_file_count=empty_file_count,
        total_size_bytes=total_size_bytes,
        files=files,
        passed=not blocking_reasons,
        blocking_reasons=tuple(blocking_reasons),
    )


def write_recorded_data_inventory_report(
    report: RecordedDataInventoryReport,
    output_dir: str | Path = DEFAULT_RECORDED_DATA_INVENTORY_OUTPUT_DIR,
) -> RecordedDataInventoryPaths:
    """
    Write recorded-data inventory files under reports/.
    """
    safe_output_dir = _ensure_reports_output_dir(output_dir)
    safe_output_dir.mkdir(parents=True, exist_ok=True)

    paths = RecordedDataInventoryPaths(
        output_dir=safe_output_dir,
        inventory_json=safe_output_dir / "inventory.json",
        inventory_text=safe_output_dir / "inventory.txt",
        manifest_json=safe_output_dir / "manifest.json",
    )

    _write_json(paths.inventory_json, recorded_data_inventory_report_to_dict(report))
    paths.inventory_text.write_text(
        format_recorded_data_inventory_report(report),
        encoding="utf-8",
    )
    _write_json(paths.manifest_json, recorded_data_inventory_manifest_to_dict(paths))

    return paths


def recorded_data_inventory_report_to_dict(
    report: RecordedDataInventoryReport,
) -> dict[str, Any]:
    """
    Convert inventory report to JSON-safe dict.
    """
    payload = asdict(report)
    payload["scanned_roots"] = list(report.scanned_roots)
    payload["missing_roots"] = list(report.missing_roots)
    payload["supported_suffixes"] = list(report.supported_suffixes)
    payload["blocking_reasons"] = list(report.blocking_reasons)
    payload["files"] = [asdict(record) for record in report.files]
    return payload


def recorded_data_inventory_manifest_to_dict(
    paths: RecordedDataInventoryPaths,
) -> dict[str, Any]:
    """
    Convert output paths to manifest form.
    """
    return {
        "manifest_version": 1,
        "manifest_source": "recorded_data_evidence_inventory",
        "paper_evidence_pipeline_only": True,
        "no_broker_orders": True,
        "no_live_market_data": True,
        "no_real_orders": True,
        "output_dir": str(paths.output_dir),
        "files": {
            "inventory_json": str(paths.inventory_json),
            "inventory_text": str(paths.inventory_text),
            "manifest_json": str(paths.manifest_json),
        },
    }


def format_recorded_data_inventory_report(
    report: RecordedDataInventoryReport,
) -> str:
    """
    Format inventory report for terminal/text display.
    """
    lines = [
        "Hunter Quant Engine - Recorded Data Evidence Inventory",
        "paper/evidence pipeline only",
        "no broker",
        "no live market data",
        "no real orders",
        "not a profitability claim",
        "",
        f"generated at: {report.generated_at}",
        f"passed gates: {report.passed}",
        "",
        "Scan Summary",
        f"scanned roots: {len(report.scanned_roots)}",
        f"missing roots: {len(report.missing_roots)}",
        f"supported file count: {report.file_count}",
        f"empty file count: {report.empty_file_count}",
        f"total size bytes: {report.total_size_bytes}",
        "",
        "Scanned Roots",
    ]

    lines.extend(f"- {root}" for root in report.scanned_roots)

    lines.append("")
    lines.append("Supported Files")
    if report.files:
        lines.extend(
            f"- {record.path} ({record.suffix}, {record.size_bytes} bytes)"
            for record in report.files
        )
    else:
        lines.append("- none")

    lines.append("")
    lines.append("Blocking Reasons")
    if report.blocking_reasons:
        lines.extend(f"- {reason}" for reason in report.blocking_reasons)
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def main() -> int:
    """
    CLI entrypoint.
    """
    report, paths = run_recorded_data_inventory()
    print(format_recorded_data_inventory_report(report), end="")
    print(f"inventory json: {paths.inventory_json}")
    print(f"inventory text: {paths.inventory_text}")
    return 0 if report.passed else 1


def _discover_supported_files(
    roots: tuple[Path, ...],
) -> Iterable[RecordedDataFileRecord]:
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue

            suffix = path.suffix.lower()
            if suffix not in SUPPORTED_RECORDED_DATA_SUFFIXES:
                continue

            size_bytes = path.stat().st_size
            yield RecordedDataFileRecord(
                path=path.as_posix(),
                suffix=suffix,
                size_bytes=size_bytes,
                is_empty=size_bytes == 0,
            )


def _build_blocking_reasons(
    *,
    roots: tuple[Path, ...],
    files: tuple[RecordedDataFileRecord, ...],
    empty_file_count: int,
) -> list[str]:
    reasons: list[str] = []

    if not roots:
        reasons.append("no data roots configured")

    if not any(root.exists() and root.is_dir() for root in roots):
        reasons.append("no recorded data roots exist")

    if not files:
        reasons.append("no supported recorded data files found")

    if empty_file_count:
        reasons.append(f"empty recorded data files found: {empty_file_count}")

    return reasons


def _ensure_reports_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    if "reports" not in path.parts:
        raise ValueError("recorded data inventory output must be under reports/")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
