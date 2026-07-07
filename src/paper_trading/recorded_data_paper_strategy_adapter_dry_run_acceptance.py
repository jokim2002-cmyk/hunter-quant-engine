"""
Recorded data paper strategy adapter dry-run acceptance gate.

Evidence-only acceptance gate for adapter dry-run output. It verifies that
dry-run events are structurally acceptable before future paper/simulation
adapter evidence modules consume them.

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
class AdapterDryRunAcceptanceIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class AdapterDryRunAcceptanceReport:
    generated_at_utc: str
    adapter_dry_run_path: str
    output_directory: str
    status: str
    accepted: bool
    allow_warnings: bool
    min_events_required: int
    min_total_planned_bars_required: int
    dry_run_status: str
    ready_for_future_adapter_evidence: bool
    event_count: int
    total_planned_bars: int
    safety_notice: str
    issues: list[AdapterDryRunAcceptanceIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter dry-run acceptance gate "
        "does not execute strategy logic, create signals, create trade plans, "
        "connect to brokers, request live market data, place real orders, use "
        "real money, calculate PnL, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> AdapterDryRunAcceptanceIssue:
    return AdapterDryRunAcceptanceIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[AdapterDryRunAcceptanceIssue]) -> str:
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


def _load_dry_run(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[AdapterDryRunAcceptanceIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "adapter_dry_run_missing",
                1,
                "Adapter dry-run JSON does not exist. Run Module GG first.",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "adapter_dry_run_invalid_json",
                1,
                f"Adapter dry-run JSON could not be parsed safely: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "adapter_dry_run_invalid_shape",
                1,
                "Adapter dry-run JSON must be an object.",
            )
        ]

    return payload, []


def _safe_events(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    events = payload.get("dry_run_events", [])
    if not isinstance(events, list):
        return []
    return [event for event in events if isinstance(event, Mapping)]


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _dry_run_status_issues(
    payload: Mapping[str, Any],
    *,
    allow_warnings: bool,
) -> list[AdapterDryRunAcceptanceIssue]:
    issues: list[AdapterDryRunAcceptanceIssue] = []
    dry_run_status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_adapter_evidence"))

    if dry_run_status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "adapter_dry_run_warn",
                1,
                "Adapter dry-run status is warn.",
            )
        )
    elif dry_run_status == "fail":
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_failed",
                1,
                "Adapter dry-run status is fail.",
            )
        )
    elif dry_run_status != "pass":
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_unknown_status",
                1,
                f"Adapter dry-run status is unknown: {dry_run_status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_not_ready",
                1,
                "Adapter dry-run is not marked ready_for_future_adapter_evidence.",
            )
        )

    return issues


def _event_issues(
    events: Sequence[Mapping[str, Any]],
) -> tuple[list[AdapterDryRunAcceptanceIssue], int]:
    issues: list[AdapterDryRunAcceptanceIssue] = []
    total_bars = 0
    missing_required = 0
    wrong_modes = 0
    zero_bars = 0
    forbidden_count = 0

    for event in events:
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
            missing_required += 1

        planned_bar_count = _as_int(event.get("planned_bar_count")) or 0
        total_bars += planned_bar_count
        if planned_bar_count <= 0:
            zero_bars += 1

        if (
            event.get("event_type") != "adapter_dry_run_request_received"
            or event.get("adapter_dry_run_mode") != "dry_run_no_strategy_execution"
            or event.get("strategy_execution_mode") != "not_executed_dry_run_only"
            or event.get("broker_execution_mode") != "broker_disabled"
            or event.get("output_mode") != "dry_run_event_manifest_only"
        ):
            wrong_modes += 1

        forbidden_count += len(_forbidden(event))

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_event_missing_required_fields",
                missing_required,
                "One or more dry-run events are missing identity/source/timestamp fields.",
            )
        )

    if zero_bars:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_event_zero_bars",
                zero_bars,
                "One or more dry-run events have zero planned bars.",
            )
        )

    if wrong_modes:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_event_wrong_modes",
                wrong_modes,
                "One or more dry-run events are not dry-run-only/broker-disabled/manifest-only.",
            )
        )

    if forbidden_count:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_event_forbidden_fields",
                forbidden_count,
                "Dry-run events contain forbidden execution/trading/profit fields.",
            )
        )

    return issues, total_bars


def build_adapter_dry_run_acceptance_report(
    *,
    adapter_dry_run_path: Path,
    output_dir: Path,
    min_events: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> AdapterDryRunAcceptanceReport:
    min_events = max(min_events, 0)
    min_total_planned_bars = max(min_total_planned_bars, 0)

    payload, issues = _load_dry_run(adapter_dry_run_path)

    if payload is None:
        status = _status(issues)
        return AdapterDryRunAcceptanceReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            adapter_dry_run_path=str(adapter_dry_run_path),
            output_directory=str(output_dir),
            status=status,
            accepted=False,
            allow_warnings=allow_warnings,
            min_events_required=min_events,
            min_total_planned_bars_required=min_total_planned_bars,
            dry_run_status="unknown",
            ready_for_future_adapter_evidence=False,
            event_count=0,
            total_planned_bars=0,
            safety_notice=safety_notice(),
            issues=issues,
        )

    issues.extend(_dry_run_status_issues(payload, allow_warnings=allow_warnings))

    forbidden_top_level = _forbidden(payload)
    if forbidden_top_level:
        issues.append(
            _issue(
                "fail",
                "adapter_dry_run_forbidden_fields",
                len(forbidden_top_level),
                "Adapter dry-run payload contains forbidden execution/trading/profit fields.",
            )
        )

    events = _safe_events(payload)
    event_issues, total_planned_bars = _event_issues(events)
    issues.extend(event_issues)

    if len(events) < min_events:
        issues.append(
            _issue(
                "fail",
                "insufficient_dry_run_events",
                min_events - len(events),
                (
                    "Adapter dry-run event count below minimum. "
                    f"Required={min_events}, actual={len(events)}."
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

    status = _status(issues)
    accepted = status == "pass" or (status == "warn" and allow_warnings)

    return AdapterDryRunAcceptanceReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        adapter_dry_run_path=str(adapter_dry_run_path),
        output_directory=str(output_dir),
        status=status,
        accepted=accepted,
        allow_warnings=allow_warnings,
        min_events_required=min_events,
        min_total_planned_bars_required=min_total_planned_bars,
        dry_run_status=str(payload.get("status") or "unknown").lower(),
        ready_for_future_adapter_evidence=bool(
            payload.get("ready_for_future_adapter_evidence")
        ),
        event_count=len(events),
        total_planned_bars=total_planned_bars,
        safety_notice=safety_notice(),
        issues=issues,
    )


def write_adapter_dry_run_acceptance_report(
    report: AdapterDryRunAcceptanceReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    acceptance_json = output_dir / "paper_strategy_adapter_dry_run_acceptance.json"
    acceptance_txt = output_dir / "paper_strategy_adapter_dry_run_acceptance.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]

    acceptance_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Dry-Run Acceptance Gate",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Accepted for future adapter evidence: {report.accepted}",
        f"Allow warnings: {report.allow_warnings}",
        f"Dry-run status: {report.dry_run_status}",
        f"Ready for future adapter evidence: {report.ready_for_future_adapter_evidence}",
        f"Dry-run events: {report.event_count}",
        f"Total planned bars: {report.total_planned_bars}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Adapter dry-run meets this no-execution acceptance scaffold.")
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
        "report_type": "recorded_data_paper_strategy_adapter_dry_run_acceptance",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted": report.accepted,
        "event_count": report.event_count,
        "total_planned_bars": report.total_planned_bars,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_dry_run_acceptance_json": str(acceptance_json),
            "paper_strategy_adapter_dry_run_acceptance_txt": str(acceptance_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_adapter_dry_run_acceptance_json": acceptance_json,
        "paper_strategy_adapter_dry_run_acceptance_txt": acceptance_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_dry_run_acceptance_report(
    *,
    adapter_dry_run_path: Path,
    output_dir: Path,
    min_events: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> tuple[AdapterDryRunAcceptanceReport, dict[str, Path]]:
    report = build_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=adapter_dry_run_path,
        output_dir=output_dir,
        min_events=min_events,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )
    outputs = write_adapter_dry_run_acceptance_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate no-execution paper strategy adapter dry-run output."
    )
    parser.add_argument(
        "--adapter-dry-run",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run/"
            "paper_strategy_adapter_dry_run.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_acceptance"
        ),
    )
    parser.add_argument("--min-events", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=Path(args.adapter_dry_run),
        output_dir=Path(args.output_dir),
        min_events=args.min_events,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data paper strategy adapter dry-run acceptance completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for future adapter evidence: {report.accepted}")
    print(f"Dry-run events: {report.event_count}")
    print(
        "Adapter dry-run acceptance report: "
        f"{outputs['paper_strategy_adapter_dry_run_acceptance_txt']}"
    )
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
