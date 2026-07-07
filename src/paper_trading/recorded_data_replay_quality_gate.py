"""
Recorded data replay quality gate.

Evidence-only audit for normalized replay datasets. This module checks whether
the replay dataset is structurally usable for later paper/simulation evidence
runs. It never connects to brokers, never requests live market data, and never
places orders.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


CORE_PRICE_FIELDS = ("open", "high", "low", "close")
REQUIRED_REPLAY_FIELDS = ("timestamp", "open", "high", "low", "close")


@dataclass(frozen=True)
class ReplayQualityIssue:
    """One quality-gate finding."""

    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class ReplayQualityReport:
    """Quality-gate report for a normalized replay dataset."""

    generated_at_utc: str
    dataset_path: str
    output_directory: str
    status: str
    source_count: int
    record_count: int
    safety_notice: str
    issues: list[ReplayQualityIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This replay quality gate does not "
        "connect to brokers, request live market data, place real orders, use "
        "real money, or prove profitability."
    )


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _as_timestamp_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_datetime(value: Any) -> datetime | None:
    text = _as_timestamp_text(value)
    if text is None:
        return None

    candidate = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _issue(severity: str, code: str, count: int, message: str) -> ReplayQualityIssue:
    return ReplayQualityIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _safe_records(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    records = payload.get("records", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, Mapping)]


def _safe_sources(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        return []
    return [source for source in sources if isinstance(source, Mapping)]


def _missing_field_issues(records: Sequence[Mapping[str, Any]]) -> list[ReplayQualityIssue]:
    issues: list[ReplayQualityIssue] = []

    for field_name in REQUIRED_REPLAY_FIELDS:
        count = sum(1 for record in records if record.get(field_name) in (None, ""))
        if count == 0:
            continue

        severity = "fail" if field_name in {"timestamp", "close"} else "warn"
        issues.append(
            _issue(
                severity,
                f"missing_{field_name}",
                count,
                f"{count} replay records are missing {field_name}.",
            )
        )

    volume_missing = sum(1 for record in records if record.get("volume") in (None, ""))
    if volume_missing:
        issues.append(
            _issue(
                "info",
                "missing_volume",
                volume_missing,
                f"{volume_missing} replay records are missing volume.",
            )
        )

    return issues


def _ohlc_sanity_issues(records: Sequence[Mapping[str, Any]]) -> list[ReplayQualityIssue]:
    invalid_ohlc = 0
    negative_volume = 0

    for record in records:
        open_price = _as_float(record.get("open"))
        high_price = _as_float(record.get("high"))
        low_price = _as_float(record.get("low"))
        close_price = _as_float(record.get("close"))
        volume = _as_float(record.get("volume"))

        if None not in (open_price, high_price, low_price, close_price):
            assert open_price is not None
            assert high_price is not None
            assert low_price is not None
            assert close_price is not None
            if high_price < max(open_price, low_price, close_price):
                invalid_ohlc += 1
            elif low_price > min(open_price, high_price, close_price):
                invalid_ohlc += 1

        if volume is not None and volume < 0:
            negative_volume += 1

    issues: list[ReplayQualityIssue] = []
    if invalid_ohlc:
        issues.append(
            _issue(
                "fail",
                "invalid_ohlc",
                invalid_ohlc,
                f"{invalid_ohlc} replay records have invalid OHLC relationships.",
            )
        )

    if negative_volume:
        issues.append(
            _issue(
                "fail",
                "negative_volume",
                negative_volume,
                f"{negative_volume} replay records have negative volume.",
            )
        )

    return issues


def _duplicate_issues(records: Sequence[Mapping[str, Any]]) -> list[ReplayQualityIssue]:
    seen: set[tuple[str, str, str]] = set()
    duplicate_count = 0

    for record in records:
        source_path = str(record.get("source_path") or "")
        timestamp = str(record.get("timestamp") or "")
        row_number = str(record.get("row_number") or "")

        key = (source_path, timestamp, row_number)
        if key in seen:
            duplicate_count += 1
        seen.add(key)

    if not duplicate_count:
        return []

    return [
        _issue(
            "warn",
            "duplicate_replay_rows",
            duplicate_count,
            f"{duplicate_count} duplicate source/timestamp/row replay records were found.",
        )
    ]


def _ordering_issues(records: Sequence[Mapping[str, Any]]) -> list[ReplayQualityIssue]:
    last_by_source: dict[str, datetime] = {}
    out_of_order = 0

    for record in records:
        source_path = str(record.get("source_path") or "")
        parsed = _parse_datetime(record.get("timestamp"))
        if parsed is None:
            continue

        previous = last_by_source.get(source_path)
        if previous is not None and parsed < previous:
            out_of_order += 1
        last_by_source[source_path] = parsed

    if not out_of_order:
        return []

    return [
        _issue(
            "warn",
            "out_of_order_timestamps",
            out_of_order,
            f"{out_of_order} replay records are out of timestamp order within a source.",
        )
    ]


def _source_issues(sources: Sequence[Mapping[str, Any]]) -> list[ReplayQualityIssue]:
    error_sources = 0
    skipped_sources = 0
    skipped_rows = 0

    for source in sources:
        status = str(source.get("status") or "").lower()
        if status == "error":
            error_sources += 1
        elif status == "skipped":
            skipped_sources += 1

        skipped = _as_float(source.get("skipped_records"))
        if skipped:
            skipped_rows += int(skipped)

    issues: list[ReplayQualityIssue] = []
    if error_sources:
        issues.append(
            _issue(
                "fail",
                "source_parse_errors",
                error_sources,
                f"{error_sources} source files could not be parsed safely.",
            )
        )

    if skipped_rows:
        issues.append(
            _issue(
                "warn",
                "skipped_source_rows",
                skipped_rows,
                f"{skipped_rows} source rows were skipped during normalization.",
            )
        )

    if skipped_sources:
        issues.append(
            _issue(
                "info",
                "skipped_sources",
                skipped_sources,
                f"{skipped_sources} source files were discovered but skipped.",
            )
        )

    return issues


def _status_from_issues(issues: Sequence[ReplayQualityIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def audit_dataset_payload(
    payload: Mapping[str, Any],
    *,
    dataset_path: Path,
    output_dir: Path,
) -> ReplayQualityReport:
    records = _safe_records(payload)
    sources = _safe_sources(payload)

    issues: list[ReplayQualityIssue] = []
    if not records:
        issues.append(
            _issue(
                "fail",
                "no_replay_records",
                1,
                "Replay dataset has no normalized records.",
            )
        )

    issues.extend(_missing_field_issues(records))
    issues.extend(_ohlc_sanity_issues(records))
    issues.extend(_duplicate_issues(records))
    issues.extend(_ordering_issues(records))
    issues.extend(_source_issues(sources))

    return ReplayQualityReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dataset_path=str(dataset_path),
        output_directory=str(output_dir),
        status=_status_from_issues(issues),
        source_count=len(sources),
        record_count=len(records),
        safety_notice=safety_notice(),
        issues=issues,
    )


def build_quality_gate_report(
    *,
    dataset_path: Path,
    output_dir: Path,
) -> ReplayQualityReport:
    if not dataset_path.exists():
        return ReplayQualityReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            dataset_path=str(dataset_path),
            output_directory=str(output_dir),
            status="fail",
            source_count=0,
            record_count=0,
            safety_notice=safety_notice(),
            issues=[
                _issue(
                    "fail",
                    "dataset_missing",
                    1,
                    "Replay dataset JSON does not exist. Run the replay dataset normalizer first.",
                )
            ],
        )

    try:
        payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ReplayQualityReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            dataset_path=str(dataset_path),
            output_directory=str(output_dir),
            status="fail",
            source_count=0,
            record_count=0,
            safety_notice=safety_notice(),
            issues=[
                _issue(
                    "fail",
                    "dataset_invalid_json",
                    1,
                    f"Replay dataset JSON could not be parsed safely: {exc}",
                )
            ],
        )

    if not isinstance(payload, Mapping):
        return ReplayQualityReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            dataset_path=str(dataset_path),
            output_directory=str(output_dir),
            status="fail",
            source_count=0,
            record_count=0,
            safety_notice=safety_notice(),
            issues=[
                _issue(
                    "fail",
                    "dataset_invalid_shape",
                    1,
                    "Replay dataset JSON must be an object with records and sources.",
                )
            ],
        )

    return audit_dataset_payload(
        payload,
        dataset_path=dataset_path,
        output_dir=output_dir,
    )


def write_quality_gate_report(
    report: ReplayQualityReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    quality_json = output_dir / "quality_gate.json"
    quality_txt = output_dir / "quality_gate.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["issues"] = [asdict(issue) for issue in report.issues]

    quality_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Replay Quality Gate",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Dataset path: {report.dataset_path}",
        f"Status: {report.status}",
        f"Source count: {report.source_count}",
        f"Replay record count: {report.record_count}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: No quality issues found by this scaffold.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: "
                f"{issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {quality_json}",
            f"- {quality_txt}",
            f"- {manifest_json}",
            "",
            "This report is not a profitability claim.",
        ]
    )
    quality_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_replay_quality_gate",
        "generated_at_utc": report.generated_at_utc,
        "dataset_path": report.dataset_path,
        "status": report.status,
        "source_count": report.source_count,
        "record_count": report.record_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "quality_gate_json": str(quality_json),
            "quality_gate_txt": str(quality_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "quality_gate_json": quality_json,
        "quality_gate_txt": quality_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_quality_gate_report(
    *,
    dataset_path: Path,
    output_dir: Path,
) -> tuple[ReplayQualityReport, dict[str, Path]]:
    report = build_quality_gate_report(dataset_path=dataset_path, output_dir=output_dir)
    outputs = write_quality_gate_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a paper-only normalized recorded-data replay dataset."
    )
    parser.add_argument(
        "--dataset",
        default="reports/paper_trading/recorded_data_replay_dataset/dataset.json",
        help="Path to replay dataset JSON output.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_replay_quality_gate",
        help="Directory where quality-gate reports are written.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_quality_gate_report(
        dataset_path=Path(args.dataset),
        output_dir=Path(args.output_dir),
    )

    print("HQE recorded data replay quality gate completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Source files: {report.source_count}")
    print(f"Replay records: {report.record_count}")
    print(f"Quality report: {outputs['quality_gate_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
