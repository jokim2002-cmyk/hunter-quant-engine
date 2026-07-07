"""
Recorded data paper strategy adapter dry-run consumer scaffold.

This module consumes adapter dry-run events as an audit-only stream after the
adapter evidence readiness gate. It does not execute strategy logic.

It never creates signals, creates trade plans, connects to brokers, requests
live market data, places orders, uses real money, calculates PnL, or proves
profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


FORBIDDEN_KEYS = {
    "broker",
    "broker_order_id",
    "exchange_order_id",
    "order",
    "order_id",
    "orders",
    "pnl",
    "profit",
    "profit_loss",
    "signal",
    "signals",
    "trade",
    "trade_plan",
    "trades",
}


@dataclass(frozen=True)
class AdapterDryRunConsumerIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class ConsumedAdapterDryRunEvent:
    consumption_index: int
    consumption_type: str
    source_event_index: int
    request_id: str
    scenario_id: str
    source_path: str
    source_type: str
    planned_bar_count: int
    first_timestamp: str | None
    last_timestamp: str | None
    consumer_mode: str
    strategy_execution_mode: str
    broker_execution_mode: str
    output_mode: str


@dataclass(frozen=True)
class AdapterDryRunConsumerReport:
    generated_at_utc: str
    adapter_evidence_readiness_path: str
    adapter_dry_run_events_path: str
    output_directory: str
    status: str
    ready_for_future_consumer_evidence: bool
    min_events_required: int
    min_total_planned_bars_required: int
    input_event_count: int
    consumed_event_count: int
    total_planned_bars: int
    safety_notice: str
    issues: list[AdapterDryRunConsumerIssue]
    consumed_events: list[ConsumedAdapterDryRunEvent]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter dry-run consumer scaffold "
        "does not execute strategy logic, create signals, create trade plans, "
        "connect to brokers, request live market data, place real orders, use "
        "real money, calculate PnL, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> AdapterDryRunConsumerIssue:
    return AdapterDryRunConsumerIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[AdapterDryRunConsumerIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _load_json_object(
    path: Path,
    missing_code: str,
    invalid_code: str,
) -> tuple[Mapping[str, Any] | None, list[AdapterDryRunConsumerIssue]]:
    if not path.exists():
        return None, [_issue("fail", missing_code, 1, f"Required JSON file missing: {path}")]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [_issue("fail", invalid_code, 1, f"JSON parse failed: {exc}")]

    if not isinstance(payload, Mapping):
        return None, [_issue("fail", invalid_code, 1, "JSON payload must be an object.")]

    return payload, []


def _load_jsonl_objects(path: Path) -> tuple[list[Mapping[str, Any]], list[AdapterDryRunConsumerIssue]]:
    if not path.exists():
        return [], [
            _issue(
                "fail",
                "adapter_dry_run_events_missing",
                1,
                f"Adapter dry-run events JSONL missing: {path}",
            )
        ]

    rows: list[Mapping[str, Any]] = []
    invalid_json = 0
    invalid_shape = 0

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                invalid_json += 1
                continue
            if not isinstance(payload, Mapping):
                invalid_shape += 1
                continue
            rows.append(payload)

    issues: list[AdapterDryRunConsumerIssue] = []
    if invalid_json:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_events_invalid_jsonl",
                invalid_json,
                f"{invalid_json} dry-run event lines are invalid JSON.",
            )
        )
    if invalid_shape:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_events_invalid_shape",
                invalid_shape,
                f"{invalid_shape} dry-run event lines are not JSON objects.",
            )
        )

    return rows, issues


def _readiness_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[AdapterDryRunConsumerIssue]:
    if payload is None:
        return []

    issues: list[AdapterDryRunConsumerIssue] = []
    readiness_status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_paper_strategy_adapter_evidence_release"))

    if readiness_status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "adapter_evidence_readiness_warn",
                1,
                "Adapter evidence readiness status is warn.",
            )
        )
    elif readiness_status != "pass":
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_readiness_not_pass",
                1,
                f"Adapter evidence readiness status is not pass: {readiness_status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_readiness_not_ready",
                1,
                "Adapter evidence readiness is not marked ready for future release.",
            )
        )

    bad = _forbidden(payload)
    if bad:
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_readiness_forbidden_fields",
                len(bad),
                "Adapter evidence readiness contains forbidden execution/trading/profit fields.",
            )
        )

    return issues


def _event_issues(event: Mapping[str, Any]) -> list[AdapterDryRunConsumerIssue]:
    issues: list[AdapterDryRunConsumerIssue] = []

    required = [
        event.get("event_index"),
        event.get("event_type"),
        event.get("request_id"),
        event.get("scenario_id"),
        event.get("source_path"),
        event.get("first_timestamp"),
        event.get("last_timestamp"),
    ]
    if any(value in (None, "") for value in required):
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_event_missing_required_fields",
                1,
                "Adapter dry-run event is missing identity/source/timestamp fields.",
            )
        )

    if (_as_int(event.get("planned_bar_count")) or 0) <= 0:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_event_zero_bars",
                1,
                "Adapter dry-run event has zero planned bars.",
            )
        )

    if (
        event.get("event_type") != "adapter_dry_run_request_received"
        or event.get("adapter_dry_run_mode") != "dry_run_no_strategy_execution"
        or event.get("strategy_execution_mode") != "not_executed_dry_run_only"
        or event.get("broker_execution_mode") != "broker_disabled"
        or event.get("output_mode") != "dry_run_event_manifest_only"
    ):
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_event_wrong_modes",
                1,
                "Adapter dry-run event is not dry-run-only/broker-disabled/manifest-only.",
            )
        )

    bad = _forbidden(event)
    if bad:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_event_forbidden_fields",
                len(bad),
                "Adapter dry-run event contains forbidden execution/trading/profit fields.",
            )
        )

    return issues


def _consume_event(index: int, event: Mapping[str, Any]) -> ConsumedAdapterDryRunEvent:
    return ConsumedAdapterDryRunEvent(
        consumption_index=index,
        consumption_type="adapter_dry_run_event_consumed_no_strategy_execution",
        source_event_index=_as_int(event.get("event_index")) or index,
        request_id=str(event.get("request_id") or ""),
        scenario_id=str(event.get("scenario_id") or ""),
        source_path=str(event.get("source_path") or ""),
        source_type=str(event.get("source_type") or ""),
        planned_bar_count=_as_int(event.get("planned_bar_count")) or 0,
        first_timestamp=event.get("first_timestamp"),
        last_timestamp=event.get("last_timestamp"),
        consumer_mode="consumer_audit_only",
        strategy_execution_mode="not_executed_consumer_only",
        broker_execution_mode="broker_disabled",
        output_mode="consumer_audit_manifest_only",
    )


def build_adapter_dry_run_consumer_report(
    *,
    adapter_evidence_readiness_path: Path,
    adapter_dry_run_events_path: Path,
    output_dir: Path,
    min_events: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
    max_events: int | None = None,
) -> AdapterDryRunConsumerReport:
    min_events = max(min_events, 0)
    min_total_planned_bars = max(min_total_planned_bars, 0)

    issues: list[AdapterDryRunConsumerIssue] = []

    readiness, readiness_load_issues = _load_json_object(
        adapter_evidence_readiness_path,
        "adapter_evidence_readiness_missing",
        "adapter_evidence_readiness_invalid_json",
    )
    events, event_load_issues = _load_jsonl_objects(adapter_dry_run_events_path)

    issues.extend(readiness_load_issues)
    issues.extend(event_load_issues)
    issues.extend(_readiness_issues(readiness, allow_warnings=allow_warnings))

    if max_events is not None:
        events = events[: max(max_events, 0)]

    consumed_events: list[ConsumedAdapterDryRunEvent] = []
    rejected_event_count = 0

    for event in events:
        event_issues = _event_issues(event)
        if event_issues:
            issues.extend(event_issues)
            rejected_event_count += 1
            continue
        consumed_events.append(_consume_event(len(consumed_events) + 1, event))

    total_planned_bars = sum(event.planned_bar_count for event in consumed_events)

    if len(consumed_events) < min_events:
        issues.append(
            _issue(
                "fail",
                "insufficient_consumed_events",
                min_events - len(consumed_events),
                (
                    "Consumed adapter dry-run event count below minimum. "
                    f"Required={min_events}, actual={len(consumed_events)}."
                ),
            )
        )

    if total_planned_bars < min_total_planned_bars:
        issues.append(
            _issue(
                "fail",
                "insufficient_total_planned_bars",
                min_total_planned_bars - total_planned_bars,
                (
                    "Consumed adapter dry-run total planned bars below minimum. "
                    f"Required={min_total_planned_bars}, actual={total_planned_bars}."
                ),
            )
        )

    if rejected_event_count and not consumed_events:
        issues.append(
            _issue(
                "fail",
                "no_valid_adapter_dry_run_events",
                rejected_event_count,
                "Adapter dry-run events existed, but none were valid for audit-only consumption.",
            )
        )

    status = _status(issues)

    return AdapterDryRunConsumerReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        adapter_evidence_readiness_path=str(adapter_evidence_readiness_path),
        adapter_dry_run_events_path=str(adapter_dry_run_events_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_consumer_evidence=status in {"pass", "warn"},
        min_events_required=min_events,
        min_total_planned_bars_required=min_total_planned_bars,
        input_event_count=len(events),
        consumed_event_count=len(consumed_events),
        total_planned_bars=total_planned_bars,
        safety_notice=safety_notice(),
        issues=issues,
        consumed_events=consumed_events,
    )


def write_adapter_dry_run_consumer_report(
    report: AdapterDryRunConsumerReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    consumer_json = output_dir / "paper_strategy_adapter_dry_run_consumer.json"
    consumed_events_jsonl = output_dir / "paper_strategy_adapter_dry_run_consumed_events.jsonl"
    consumer_txt = output_dir / "paper_strategy_adapter_dry_run_consumer.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["consumed_events"] = [asdict(event) for event in report.consumed_events]

    consumer_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with consumed_events_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for event in report.consumed_events:
            handle.write(json.dumps(asdict(event), sort_keys=True))
            handle.write("\n")

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Dry-Run Consumer",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future consumer evidence: {report.ready_for_future_consumer_evidence}",
        f"Input events: {report.input_event_count}",
        f"Consumed events: {report.consumed_event_count}",
        f"Total planned bars: {report.total_planned_bars}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Adapter dry-run events were consumed in audit-only mode.")
    else:
        for issue in report.issues:
            lines.append(f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}")

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {consumer_json}",
            f"- {consumed_events_jsonl}",
            f"- {consumer_txt}",
            f"- {manifest_json}",
            "",
            "This consumer does not execute strategy logic, create signals, calculate PnL, or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    consumer_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_adapter_dry_run_consumer",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_consumer_evidence": report.ready_for_future_consumer_evidence,
        "input_event_count": report.input_event_count,
        "consumed_event_count": report.consumed_event_count,
        "total_planned_bars": report.total_planned_bars,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_dry_run_consumer_json": str(consumer_json),
            "paper_strategy_adapter_dry_run_consumed_events_jsonl": str(consumed_events_jsonl),
            "paper_strategy_adapter_dry_run_consumer_txt": str(consumer_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_strategy_adapter_dry_run_consumer_json": consumer_json,
        "paper_strategy_adapter_dry_run_consumed_events_jsonl": consumed_events_jsonl,
        "paper_strategy_adapter_dry_run_consumer_txt": consumer_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_dry_run_consumer_report(
    *,
    adapter_evidence_readiness_path: Path,
    adapter_dry_run_events_path: Path,
    output_dir: Path,
    min_events: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
    max_events: int | None = None,
) -> tuple[AdapterDryRunConsumerReport, dict[str, Path]]:
    report = build_adapter_dry_run_consumer_report(
        adapter_evidence_readiness_path=adapter_evidence_readiness_path,
        adapter_dry_run_events_path=adapter_dry_run_events_path,
        output_dir=output_dir,
        min_events=min_events,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
        max_events=max_events,
    )
    outputs = write_adapter_dry_run_consumer_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consume no-execution adapter dry-run events in audit-only mode."
    )
    parser.add_argument(
        "--adapter-evidence-readiness",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_evidence_readiness/"
            "paper_strategy_adapter_evidence_readiness.json"
        ),
    )
    parser.add_argument(
        "--adapter-dry-run-events",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run/"
            "paper_strategy_adapter_dry_run_events.jsonl"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_consumer"
        ),
    )
    parser.add_argument("--min-events", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-events", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_dry_run_consumer_report(
        adapter_evidence_readiness_path=Path(args.adapter_evidence_readiness),
        adapter_dry_run_events_path=Path(args.adapter_dry_run_events),
        output_dir=Path(args.output_dir),
        min_events=args.min_events,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
        max_events=args.max_events,
    )

    print("HQE recorded data paper strategy adapter dry-run consumer completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Consumed events: {report.consumed_event_count}")
    print(f"Adapter dry-run consumer report: {outputs['paper_strategy_adapter_dry_run_consumer_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
