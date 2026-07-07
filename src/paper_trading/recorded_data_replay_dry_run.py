"""
Recorded data replay dry-run player.

Evidence-only replay player for normalized recorded-data datasets. It converts
normalized replay records into a deterministic event stream for later paper
testing workflows. It never runs a strategy, never creates trade plans, never
connects to brokers, never requests live market data, and never places orders.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ReplayDryRunIssue:
    """One dry-run finding."""

    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class ReplayDryRunEvent:
    """A deterministic paper/simulation replay event."""

    event_index: int
    event_type: str
    source_path: str
    source_type: str
    row_number: int | None
    timestamp: str
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: float | None
    safety_mode: str


@dataclass(frozen=True)
class ReplayDryRunReport:
    """Dry-run replay report written by the CLI."""

    generated_at_utc: str
    dataset_path: str
    quality_gate_path: str
    output_directory: str
    status: str
    input_record_count: int
    replayed_event_count: int
    first_timestamp: str | None
    last_timestamp: str | None
    safety_notice: str
    issues: list[ReplayDryRunIssue]
    events: list[ReplayDryRunEvent]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data replay dry-run does "
        "not run strategies, create trade plans, connect to brokers, request live "
        "market data, place real orders, use real money, or prove profitability."
    )


def _issue(severity: str, code: str, count: int, message: str) -> ReplayDryRunIssue:
    return ReplayDryRunIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status_from_issues(issues: Sequence[ReplayDryRunIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


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


def _as_required_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _safe_records(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    records = payload.get("records", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, Mapping)]


def _load_dataset(dataset_path: Path) -> tuple[Mapping[str, Any] | None, list[ReplayDryRunIssue]]:
    if not dataset_path.exists():
        return None, [
            _issue(
                "fail",
                "dataset_missing",
                1,
                "Replay dataset JSON does not exist. Run the replay dataset normalizer first.",
            )
        ]

    try:
        payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "dataset_invalid_json",
                1,
                f"Replay dataset JSON could not be parsed safely: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "dataset_invalid_shape",
                1,
                "Replay dataset JSON must be an object with a records list.",
            )
        ]

    return payload, []


def _quality_gate_issues(quality_gate_path: Path) -> tuple[bool, list[ReplayDryRunIssue]]:
    if not quality_gate_path.exists():
        return False, [
            _issue(
                "info",
                "quality_gate_missing",
                1,
                "Replay quality gate report was not found; dry-run stayed evidence-only.",
            )
        ]

    try:
        payload = json.loads(quality_gate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [
            _issue(
                "warn",
                "quality_gate_invalid_json",
                1,
                f"Replay quality gate report could not be parsed safely: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return False, [
            _issue(
                "warn",
                "quality_gate_invalid_shape",
                1,
                "Replay quality gate report must be a JSON object.",
            )
        ]

    gate_status = str(payload.get("status") or "unknown").lower()
    if gate_status == "fail":
        return True, [
            _issue(
                "fail",
                "quality_gate_failed",
                1,
                "Replay quality gate status is fail, so dry-run event generation was blocked.",
            )
        ]

    if gate_status == "warn":
        return False, [
            _issue(
                "warn",
                "quality_gate_warn",
                1,
                "Replay quality gate status is warn; dry-run generated events with caution.",
            )
        ]

    if gate_status == "pass":
        return False, [
            _issue(
                "info",
                "quality_gate_pass",
                1,
                "Replay quality gate status is pass.",
            )
        ]

    return False, [
        _issue(
            "warn",
            "quality_gate_unknown_status",
            1,
            f"Replay quality gate status is unknown: {gate_status}.",
        )
    ]


def _event_from_record(record: Mapping[str, Any], event_index: int) -> ReplayDryRunEvent | None:
    timestamp = _as_required_text(record.get("timestamp"))
    close_price = _as_float(record.get("close"))

    if timestamp is None or close_price is None:
        return None

    return ReplayDryRunEvent(
        event_index=event_index,
        event_type="recorded_market_data_bar",
        source_path=str(record.get("source_path") or ""),
        source_type=str(record.get("source_type") or ""),
        row_number=_as_int(record.get("row_number")),
        timestamp=timestamp,
        open=_as_float(record.get("open")),
        high=_as_float(record.get("high")),
        low=_as_float(record.get("low")),
        close=close_price,
        volume=_as_float(record.get("volume")),
        safety_mode="paper_simulation_only",
    )


def build_replay_dry_run_report(
    *,
    dataset_path: Path,
    quality_gate_path: Path,
    output_dir: Path,
    max_records: int | None = None,
) -> ReplayDryRunReport:
    payload, issues = _load_dataset(dataset_path)
    gate_blocked, gate_issues = _quality_gate_issues(quality_gate_path)
    issues.extend(gate_issues)

    if payload is None:
        return ReplayDryRunReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            dataset_path=str(dataset_path),
            quality_gate_path=str(quality_gate_path),
            output_directory=str(output_dir),
            status="fail",
            input_record_count=0,
            replayed_event_count=0,
            first_timestamp=None,
            last_timestamp=None,
            safety_notice=safety_notice(),
            issues=issues,
            events=[],
        )

    records = _safe_records(payload)
    if max_records is not None and max_records >= 0:
        records = records[:max_records]

    if not records:
        issues.append(
            _issue(
                "fail",
                "no_replay_records",
                1,
                "Replay dataset has no normalized records available for dry-run.",
            )
        )

    if gate_blocked:
        return ReplayDryRunReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            dataset_path=str(dataset_path),
            quality_gate_path=str(quality_gate_path),
            output_directory=str(output_dir),
            status="fail",
            input_record_count=len(records),
            replayed_event_count=0,
            first_timestamp=None,
            last_timestamp=None,
            safety_notice=safety_notice(),
            issues=issues,
            events=[],
        )

    events: list[ReplayDryRunEvent] = []
    skipped_records = 0

    for record in records:
        event = _event_from_record(record, len(events) + 1)
        if event is None:
            skipped_records += 1
            continue
        events.append(event)

    if skipped_records:
        issues.append(
            _issue(
                "warn",
                "skipped_unplayable_records",
                skipped_records,
                f"{skipped_records} records were skipped because timestamp or close was missing.",
            )
        )

    if records and not events:
        issues.append(
            _issue(
                "fail",
                "no_playable_events",
                1,
                "Replay dataset records existed, but no playable dry-run events could be created.",
            )
        )

    first_timestamp = events[0].timestamp if events else None
    last_timestamp = events[-1].timestamp if events else None

    return ReplayDryRunReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dataset_path=str(dataset_path),
        quality_gate_path=str(quality_gate_path),
        output_directory=str(output_dir),
        status=_status_from_issues(issues),
        input_record_count=len(records),
        replayed_event_count=len(events),
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
        safety_notice=safety_notice(),
        issues=issues,
        events=events,
    )


def write_replay_dry_run_report(
    report: ReplayDryRunReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    report_json = output_dir / "dry_run_report.json"
    events_jsonl = output_dir / "dry_run_events.jsonl"
    report_txt = output_dir / "dry_run_report.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["issues"] = [asdict(issue) for issue in report.issues]
    report_data["events"] = [asdict(event) for event in report.events]

    report_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with events_jsonl.open("w", encoding="utf-8", newline="\n") as file_handle:
        for event in report.events:
            file_handle.write(json.dumps(asdict(event), sort_keys=True))
            file_handle.write("\n")

    lines = [
        "HQE Recorded Data Replay Dry-Run",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Dataset path: {report.dataset_path}",
        f"Quality gate path: {report.quality_gate_path}",
        f"Status: {report.status}",
        f"Input replay records: {report.input_record_count}",
        f"Replayed dry-run events: {report.replayed_event_count}",
        f"First timestamp: {report.first_timestamp}",
        f"Last timestamp: {report.last_timestamp}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: No dry-run issues found by this scaffold.")
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
            f"- {report_json}",
            f"- {events_jsonl}",
            f"- {report_txt}",
            f"- {manifest_json}",
            "",
            "This dry-run does not run strategy logic or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    report_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_replay_dry_run",
        "generated_at_utc": report.generated_at_utc,
        "dataset_path": report.dataset_path,
        "quality_gate_path": report.quality_gate_path,
        "status": report.status,
        "input_record_count": report.input_record_count,
        "replayed_event_count": report.replayed_event_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "dry_run_report_json": str(report_json),
            "dry_run_events_jsonl": str(events_jsonl),
            "dry_run_report_txt": str(report_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "dry_run_report_json": report_json,
        "dry_run_events_jsonl": events_jsonl,
        "dry_run_report_txt": report_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_replay_dry_run_report(
    *,
    dataset_path: Path,
    quality_gate_path: Path,
    output_dir: Path,
    max_records: int | None = None,
) -> tuple[ReplayDryRunReport, dict[str, Path]]:
    report = build_replay_dry_run_report(
        dataset_path=dataset_path,
        quality_gate_path=quality_gate_path,
        output_dir=output_dir,
        max_records=max_records,
    )
    outputs = write_replay_dry_run_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a paper-only dry-run event stream from a replay dataset."
    )
    parser.add_argument(
        "--dataset",
        default="reports/paper_trading/recorded_data_replay_dataset/dataset.json",
        help="Path to replay dataset JSON output.",
    )
    parser.add_argument(
        "--quality-gate",
        default="reports/paper_trading/recorded_data_replay_quality_gate/quality_gate.json",
        help="Path to replay quality gate JSON output.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_replay_dry_run",
        help="Directory where dry-run reports are written.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Optional maximum number of replay records to dry-run.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_replay_dry_run_report(
        dataset_path=Path(args.dataset),
        quality_gate_path=Path(args.quality_gate),
        output_dir=Path(args.output_dir),
        max_records=args.max_records,
    )

    print("HQE recorded data replay dry-run completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Input replay records: {report.input_record_count}")
    print(f"Replayed dry-run events: {report.replayed_event_count}")
    print(f"Dry-run report: {outputs['dry_run_report_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
