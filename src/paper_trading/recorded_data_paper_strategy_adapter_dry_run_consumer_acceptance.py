"""
Recorded data paper strategy adapter dry-run consumer acceptance gate.

Evidence-only gate for adapter dry-run consumer output. It verifies that
audit-only consumed events are structurally acceptable before future consumer
readiness/evidence modules can consume them.

This module never executes strategy logic, creates signals, creates trade plans,
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
class AdapterDryRunConsumerAcceptanceIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class AdapterDryRunConsumerAcceptanceReport:
    generated_at_utc: str
    consumer_report_path: str
    output_directory: str
    status: str
    accepted: bool
    allow_warnings: bool
    min_consumed_events_required: int
    min_total_planned_bars_required: int
    consumer_status: str
    ready_for_future_consumer_evidence: bool
    consumed_event_count: int
    total_planned_bars: int
    safety_notice: str
    issues: list[AdapterDryRunConsumerAcceptanceIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter dry-run consumer acceptance "
        "gate does not execute strategy logic, create signals, create trade plans, "
        "connect to brokers, request live market data, place real orders, use "
        "real money, calculate PnL, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> AdapterDryRunConsumerAcceptanceIssue:
    return AdapterDryRunConsumerAcceptanceIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[AdapterDryRunConsumerAcceptanceIssue]) -> str:
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


def _load_consumer_report(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[AdapterDryRunConsumerAcceptanceIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "adapter_dry_run_consumer_missing",
                1,
                "Adapter dry-run consumer JSON does not exist. Run Module NN first.",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "adapter_dry_run_consumer_invalid_json",
                1,
                f"Adapter dry-run consumer JSON could not be parsed safely: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "adapter_dry_run_consumer_invalid_shape",
                1,
                "Adapter dry-run consumer JSON must be an object.",
            )
        ]

    return payload, []


def _safe_consumed_events(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    events = payload.get("consumed_events", [])
    if not isinstance(events, list):
        return []
    return [event for event in events if isinstance(event, Mapping)]


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _consumer_status_issues(
    payload: Mapping[str, Any],
    *,
    allow_warnings: bool,
) -> list[AdapterDryRunConsumerAcceptanceIssue]:
    issues: list[AdapterDryRunConsumerAcceptanceIssue] = []
    consumer_status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_consumer_evidence"))

    if consumer_status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "adapter_dry_run_consumer_warn",
                1,
                "Adapter dry-run consumer status is warn.",
            )
        )
    elif consumer_status == "fail":
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_consumer_failed",
                1,
                "Adapter dry-run consumer status is fail.",
            )
        )
    elif consumer_status != "pass":
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_consumer_unknown_status",
                1,
                f"Adapter dry-run consumer status is unknown: {consumer_status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_consumer_not_ready",
                1,
                "Adapter dry-run consumer is not marked ready_for_future_consumer_evidence.",
            )
        )

    return issues


def _consumed_event_issues(
    events: Sequence[Mapping[str, Any]],
) -> tuple[list[AdapterDryRunConsumerAcceptanceIssue], int]:
    issues: list[AdapterDryRunConsumerAcceptanceIssue] = []
    total_bars = 0
    missing_required = 0
    wrong_modes = 0
    zero_bars = 0
    forbidden_count = 0

    for event in events:
        required = [
            event.get("consumption_index"),
            event.get("consumption_type"),
            event.get("source_event_index"),
            event.get("request_id"),
            event.get("scenario_id"),
            event.get("source_path"),
            event.get("first_timestamp"),
            event.get("last_timestamp"),
        ]
        if any(value in (None, "") for value in required):
            missing_required += 1

        planned_bar_count = _as_int(event.get("planned_bar_count")) or 0
        total_bars += planned_bar_count
        if planned_bar_count <= 0:
            zero_bars += 1

        if (
            event.get("consumption_type")
            != "adapter_dry_run_event_consumed_no_strategy_execution"
            or event.get("consumer_mode") != "consumer_audit_only"
            or event.get("strategy_execution_mode") != "not_executed_consumer_only"
            or event.get("broker_execution_mode") != "broker_disabled"
            or event.get("output_mode") != "consumer_audit_manifest_only"
        ):
            wrong_modes += 1

        forbidden_count += len(_forbidden(event))

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "consumed_event_missing_required_fields",
                missing_required,
                "One or more consumed events are missing identity/source/timestamp fields.",
            )
        )

    if zero_bars:
        issues.append(
            _issue(
                "fail",
                "consumed_event_zero_bars",
                zero_bars,
                "One or more consumed events have zero planned bars.",
            )
        )

    if wrong_modes:
        issues.append(
            _issue(
                "fail",
                "consumed_event_wrong_modes",
                wrong_modes,
                "One or more consumed events are not audit-only/broker-disabled/manifest-only.",
            )
        )

    if forbidden_count:
        issues.append(
            _issue(
                "fail",
                "consumed_event_forbidden_fields",
                forbidden_count,
                "Consumed events contain forbidden execution/trading/profit fields.",
            )
        )

    return issues, total_bars


def build_adapter_dry_run_consumer_acceptance_report(
    *,
    consumer_report_path: Path,
    output_dir: Path,
    min_consumed_events: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> AdapterDryRunConsumerAcceptanceReport:
    min_consumed_events = max(min_consumed_events, 0)
    min_total_planned_bars = max(min_total_planned_bars, 0)

    payload, issues = _load_consumer_report(consumer_report_path)

    if payload is None:
        status = _status(issues)
        return AdapterDryRunConsumerAcceptanceReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            consumer_report_path=str(consumer_report_path),
            output_directory=str(output_dir),
            status=status,
            accepted=False,
            allow_warnings=allow_warnings,
            min_consumed_events_required=min_consumed_events,
            min_total_planned_bars_required=min_total_planned_bars,
            consumer_status="unknown",
            ready_for_future_consumer_evidence=False,
            consumed_event_count=0,
            total_planned_bars=0,
            safety_notice=safety_notice(),
            issues=issues,
        )

    issues.extend(_consumer_status_issues(payload, allow_warnings=allow_warnings))

    forbidden_top_level = _forbidden(payload)
    if forbidden_top_level:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_consumer_forbidden_fields",
                len(forbidden_top_level),
                "Adapter dry-run consumer payload contains forbidden execution/trading/profit fields.",
            )
        )

    consumed_events = _safe_consumed_events(payload)
    consumed_event_issues, total_planned_bars = _consumed_event_issues(consumed_events)
    issues.extend(consumed_event_issues)

    if len(consumed_events) < min_consumed_events:
        issues.append(
            _issue(
                "fail",
                "insufficient_consumed_events",
                min_consumed_events - len(consumed_events),
                (
                    "Consumed event count below minimum. "
                    f"Required={min_consumed_events}, actual={len(consumed_events)}."
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
                    "Consumed event total planned bars below minimum. "
                    f"Required={min_total_planned_bars}, actual={total_planned_bars}."
                ),
            )
        )

    status = _status(issues)
    accepted = status == "pass" or (status == "warn" and allow_warnings)

    return AdapterDryRunConsumerAcceptanceReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        consumer_report_path=str(consumer_report_path),
        output_directory=str(output_dir),
        status=status,
        accepted=accepted,
        allow_warnings=allow_warnings,
        min_consumed_events_required=min_consumed_events,
        min_total_planned_bars_required=min_total_planned_bars,
        consumer_status=str(payload.get("status") or "unknown").lower(),
        ready_for_future_consumer_evidence=bool(
            payload.get("ready_for_future_consumer_evidence")
        ),
        consumed_event_count=len(consumed_events),
        total_planned_bars=total_planned_bars,
        safety_notice=safety_notice(),
        issues=issues,
    )


def write_adapter_dry_run_consumer_acceptance_report(
    report: AdapterDryRunConsumerAcceptanceReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    acceptance_json = output_dir / "paper_strategy_adapter_dry_run_consumer_acceptance.json"
    acceptance_txt = output_dir / "paper_strategy_adapter_dry_run_consumer_acceptance.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]

    acceptance_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Dry-Run Consumer Acceptance Gate",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Accepted for future consumer evidence: {report.accepted}",
        f"Allow warnings: {report.allow_warnings}",
        f"Consumer status: {report.consumer_status}",
        f"Ready for future consumer evidence: {report.ready_for_future_consumer_evidence}",
        f"Consumed events: {report.consumed_event_count}",
        f"Total planned bars: {report.total_planned_bars}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Adapter dry-run consumer meets this audit-only acceptance scaffold.")
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
            f"- {acceptance_json}",
            f"- {acceptance_txt}",
            f"- {manifest_json}",
            "",
            "This gate does not execute strategy logic, create signals, calculate PnL, or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    acceptance_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted": report.accepted,
        "consumed_event_count": report.consumed_event_count,
        "total_planned_bars": report.total_planned_bars,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_dry_run_consumer_acceptance_json": str(acceptance_json),
            "paper_strategy_adapter_dry_run_consumer_acceptance_txt": str(acceptance_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_adapter_dry_run_consumer_acceptance_json": acceptance_json,
        "paper_strategy_adapter_dry_run_consumer_acceptance_txt": acceptance_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_dry_run_consumer_acceptance_report(
    *,
    consumer_report_path: Path,
    output_dir: Path,
    min_consumed_events: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> tuple[AdapterDryRunConsumerAcceptanceReport, dict[str, Path]]:
    report = build_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=consumer_report_path,
        output_dir=output_dir,
        min_consumed_events=min_consumed_events,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )
    outputs = write_adapter_dry_run_consumer_acceptance_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate audit-only paper strategy adapter dry-run consumer output."
    )
    parser.add_argument(
        "--consumer-report",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_consumer/"
            "paper_strategy_adapter_dry_run_consumer.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance"
        ),
    )
    parser.add_argument("--min-consumed-events", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=Path(args.consumer_report),
        output_dir=Path(args.output_dir),
        min_consumed_events=args.min_consumed_events,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data paper strategy adapter dry-run consumer acceptance completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for future consumer evidence: {report.accepted}")
    print(f"Consumed events: {report.consumed_event_count}")
    print(
        "Adapter dry-run consumer acceptance report: "
        f"{outputs['paper_strategy_adapter_dry_run_consumer_acceptance_txt']}"
    )
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
