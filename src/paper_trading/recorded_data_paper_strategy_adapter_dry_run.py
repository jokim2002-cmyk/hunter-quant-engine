"""
Recorded data paper strategy adapter dry-run scaffold.

This module converts accepted adapter request manifests into deterministic
adapter dry-run events for a future paper/simulation adapter phase.

It never executes strategy logic, creates signals, creates trade plans,
connects to brokers, requests live market data, places orders, uses real money,
calculates PnL, or proves profitability.
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
class AdapterDryRunIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class AdapterDryRunEvent:
    event_index: int
    event_type: str
    request_id: str
    scenario_id: str
    source_path: str
    source_type: str
    planned_bar_count: int
    first_timestamp: str | None
    last_timestamp: str | None
    adapter_dry_run_mode: str
    strategy_execution_mode: str
    broker_execution_mode: str
    output_mode: str


@dataclass(frozen=True)
class AdapterDryRunReport:
    generated_at_utc: str
    adapter_readiness_path: str
    adapter_requests_path: str
    output_directory: str
    status: str
    ready_for_future_adapter_evidence: bool
    min_requests_required: int
    min_total_planned_bars_required: int
    request_count: int
    dry_run_event_count: int
    total_planned_bars: int
    safety_notice: str
    issues: list[AdapterDryRunIssue]
    dry_run_events: list[AdapterDryRunEvent]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter dry-run scaffold does not "
        "execute strategy logic, create signals, create trade plans, connect to "
        "brokers, request live market data, place real orders, use real money, "
        "calculate PnL, or prove profitability."
    )


def _issue(severity: str, code: str, count: int, message: str) -> AdapterDryRunIssue:
    return AdapterDryRunIssue(severity=severity, code=code, count=count, message=message)


def _status(issues: Sequence[AdapterDryRunIssue]) -> str:
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


def _load_json_object(
    path: Path,
    missing_code: str,
    invalid_code: str,
) -> tuple[Mapping[str, Any] | None, list[AdapterDryRunIssue]]:
    if not path.exists():
        return None, [_issue("fail", missing_code, 1, f"Required JSON file missing: {path}")]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [_issue("fail", invalid_code, 1, f"JSON parse failed: {exc}")]

    if not isinstance(payload, Mapping):
        return None, [_issue("fail", invalid_code, 1, "JSON payload must be an object.")]

    return payload, []


def _load_jsonl_objects(path: Path) -> tuple[list[Mapping[str, Any]], list[AdapterDryRunIssue]]:
    if not path.exists():
        return [], [
            _issue(
                "fail",
                "adapter_requests_missing",
                1,
                f"Adapter requests JSONL missing: {path}",
            )
        ]

    rows: list[Mapping[str, Any]] = []
    issues: list[AdapterDryRunIssue] = []
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

    if invalid_json:
        issues.append(
            _issue(
                "fail",
                "adapter_requests_invalid_jsonl",
                invalid_json,
                f"{invalid_json} adapter request lines are invalid JSON.",
            )
        )

    if invalid_shape:
        issues.append(
            _issue(
                "fail",
                "adapter_requests_invalid_shape",
                invalid_shape,
                f"{invalid_shape} adapter request lines are not JSON objects.",
            )
        )

    return rows, issues


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _readiness_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[AdapterDryRunIssue]:
    if payload is None:
        return []

    issues: list[AdapterDryRunIssue] = []
    readiness_status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_adapter_dry_run"))

    if readiness_status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "adapter_readiness_warn",
                1,
                "Adapter readiness status is warn.",
            )
        )
    elif readiness_status != "pass":
        issues.append(
            _issue(
                "fail",
                "adapter_readiness_not_pass",
                1,
                f"Adapter readiness status is not pass: {readiness_status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "adapter_readiness_not_ready",
                1,
                "Adapter readiness is not marked ready_for_future_adapter_dry_run.",
            )
        )

    bad = _forbidden(payload)
    if bad:
        issues.append(
            _issue(
                "fail",
                "adapter_readiness_forbidden_fields",
                len(bad),
                "Adapter readiness payload contains forbidden execution/trading/profit fields.",
            )
        )

    return issues


def _validate_request(request: Mapping[str, Any]) -> list[AdapterDryRunIssue]:
    issues: list[AdapterDryRunIssue] = []

    required = [
        request.get("request_id"),
        request.get("scenario_id"),
        request.get("source_path"),
        request.get("first_timestamp"),
        request.get("last_timestamp"),
    ]
    if any(value in (None, "") for value in required):
        issues.append(
            _issue(
                "fail",
                "adapter_request_missing_required_fields",
                1,
                "Adapter request is missing identity/source/timestamp fields.",
            )
        )

    if (_as_int(request.get("planned_bar_count")) or 0) <= 0:
        issues.append(
            _issue(
                "fail",
                "adapter_request_zero_bars",
                1,
                "Adapter request has zero planned bars.",
            )
        )

    if (
        request.get("adapter_mode") != "contract_only_no_strategy_execution"
        or request.get("strategy_execution_mode") != "not_executed_contract_only"
        or request.get("broker_execution_mode") != "broker_disabled"
        or request.get("output_mode") != "adapter_request_manifest_only"
    ):
        issues.append(
            _issue(
                "fail",
                "adapter_request_wrong_modes",
                1,
                "Adapter request is not contract-only/broker-disabled/manifest-only.",
            )
        )

    bad = _forbidden(request)
    if bad:
        issues.append(
            _issue(
                "fail",
                "adapter_request_forbidden_fields",
                len(bad),
                "Adapter request contains forbidden execution/trading/profit fields.",
            )
        )

    return issues


def _event_from_request(index: int, request: Mapping[str, Any]) -> AdapterDryRunEvent:
    return AdapterDryRunEvent(
        event_index=index,
        event_type="adapter_dry_run_request_received",
        request_id=str(request.get("request_id") or ""),
        scenario_id=str(request.get("scenario_id") or ""),
        source_path=str(request.get("source_path") or ""),
        source_type=str(request.get("source_type") or ""),
        planned_bar_count=_as_int(request.get("planned_bar_count")) or 0,
        first_timestamp=request.get("first_timestamp"),
        last_timestamp=request.get("last_timestamp"),
        adapter_dry_run_mode="dry_run_no_strategy_execution",
        strategy_execution_mode="not_executed_dry_run_only",
        broker_execution_mode="broker_disabled",
        output_mode="dry_run_event_manifest_only",
    )


def build_adapter_dry_run_report(
    *,
    adapter_readiness_path: Path,
    adapter_requests_path: Path,
    output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
    max_requests: int | None = None,
) -> AdapterDryRunReport:
    min_requests = max(min_requests, 0)
    min_total_planned_bars = max(min_total_planned_bars, 0)

    issues: list[AdapterDryRunIssue] = []

    readiness, readiness_issues = _load_json_object(
        adapter_readiness_path,
        "adapter_readiness_missing",
        "adapter_readiness_invalid_json",
    )
    requests, request_load_issues = _load_jsonl_objects(adapter_requests_path)

    issues.extend(readiness_issues)
    issues.extend(request_load_issues)
    issues.extend(_readiness_issues(readiness, allow_warnings=allow_warnings))

    if max_requests is not None:
        requests = requests[: max(max_requests, 0)]

    dry_run_events: list[AdapterDryRunEvent] = []
    request_issue_count = 0

    for request in requests:
        request_issues = _validate_request(request)
        if request_issues:
            issues.extend(request_issues)
            request_issue_count += 1
            continue
        dry_run_events.append(_event_from_request(len(dry_run_events) + 1, request))

    total_planned_bars = sum(event.planned_bar_count for event in dry_run_events)

    if len(dry_run_events) < min_requests:
        issues.append(
            _issue(
                "fail",
                "insufficient_dry_run_events",
                min_requests - len(dry_run_events),
                (
                    "Adapter dry-run event count below minimum. "
                    f"Required={min_requests}, actual={len(dry_run_events)}."
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
                    "Adapter dry-run total planned bars below minimum. "
                    f"Required={min_total_planned_bars}, actual={total_planned_bars}."
                ),
            )
        )

    if request_issue_count and not dry_run_events:
        issues.append(
            _issue(
                "fail",
                "no_valid_adapter_requests",
                request_issue_count,
                "Adapter requests existed, but none were valid for dry-run event creation.",
            )
        )

    status = _status(issues)

    return AdapterDryRunReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        adapter_readiness_path=str(adapter_readiness_path),
        adapter_requests_path=str(adapter_requests_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_adapter_evidence=status in {"pass", "warn"},
        min_requests_required=min_requests,
        min_total_planned_bars_required=min_total_planned_bars,
        request_count=len(requests),
        dry_run_event_count=len(dry_run_events),
        total_planned_bars=total_planned_bars,
        safety_notice=safety_notice(),
        issues=issues,
        dry_run_events=dry_run_events,
    )


def write_adapter_dry_run_report(
    report: AdapterDryRunReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    dry_run_json = output_dir / "paper_strategy_adapter_dry_run.json"
    events_jsonl = output_dir / "paper_strategy_adapter_dry_run_events.jsonl"
    dry_run_txt = output_dir / "paper_strategy_adapter_dry_run.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["dry_run_events"] = [asdict(event) for event in report.dry_run_events]

    dry_run_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with events_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for event in report.dry_run_events:
            handle.write(json.dumps(asdict(event), sort_keys=True))
            handle.write("\n")

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Dry-Run",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future adapter evidence: {report.ready_for_future_adapter_evidence}",
        f"Requests read: {report.request_count}",
        f"Dry-run events: {report.dry_run_event_count}",
        f"Total planned bars: {report.total_planned_bars}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Adapter dry-run events were created without executing strategy logic.")
    else:
        for issue in report.issues:
            lines.append(f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}")

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {dry_run_json}",
            f"- {events_jsonl}",
            f"- {dry_run_txt}",
            f"- {manifest_json}",
            "",
            "This dry-run does not execute strategy logic, create signals, calculate PnL, or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    dry_run_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_adapter_dry_run",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_adapter_evidence": report.ready_for_future_adapter_evidence,
        "dry_run_event_count": report.dry_run_event_count,
        "total_planned_bars": report.total_planned_bars,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_dry_run_json": str(dry_run_json),
            "paper_strategy_adapter_dry_run_events_jsonl": str(events_jsonl),
            "paper_strategy_adapter_dry_run_txt": str(dry_run_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_strategy_adapter_dry_run_json": dry_run_json,
        "paper_strategy_adapter_dry_run_events_jsonl": events_jsonl,
        "paper_strategy_adapter_dry_run_txt": dry_run_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_dry_run_report(
    *,
    adapter_readiness_path: Path,
    adapter_requests_path: Path,
    output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
    max_requests: int | None = None,
) -> tuple[AdapterDryRunReport, dict[str, Path]]:
    report = build_adapter_dry_run_report(
        adapter_readiness_path=adapter_readiness_path,
        adapter_requests_path=adapter_requests_path,
        output_dir=output_dir,
        min_requests=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
        max_requests=max_requests,
    )
    return report, write_adapter_dry_run_report(report, output_dir)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a no-execution paper strategy adapter dry-run.")
    parser.add_argument(
        "--adapter-readiness",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_readiness/paper_strategy_adapter_readiness.json",
    )
    parser.add_argument(
        "--adapter-requests",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_contract/paper_strategy_adapter_requests.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_dry_run",
    )
    parser.add_argument("--min-requests", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-requests", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_dry_run_report(
        adapter_readiness_path=Path(args.adapter_readiness),
        adapter_requests_path=Path(args.adapter_requests),
        output_dir=Path(args.output_dir),
        min_requests=args.min_requests,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
        max_requests=args.max_requests,
    )

    print("HQE recorded data paper strategy adapter dry-run completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Dry-run events: {report.dry_run_event_count}")
    print(f"Adapter dry-run report: {outputs['paper_strategy_adapter_dry_run_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
