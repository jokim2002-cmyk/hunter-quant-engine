"""
Recorded data strategy input contract.

Evidence-only adapter from recorded replay dry-run events into a future
paper-strategy replay input contract. This module only prepares structurally
safe bars for a later paper/simulation strategy phase.

It never runs strategies, creates signals, creates trade plans, connects to
brokers, requests live market data, places orders, uses real money, or proves
profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPECTED_EVENT_TYPE = "recorded_market_data_bar"
FORBIDDEN_EXECUTION_KEYS = {
    "broker",
    "broker_order_id",
    "exchange_order_id",
    "order",
    "order_id",
    "order_type",
    "orders",
    "pnl",
    "profit",
    "profit_loss",
    "quantity",
    "signal",
    "side",
    "trade",
    "trade_plan",
    "trades",
}


@dataclass(frozen=True)
class StrategyInputContractIssue:
    """One strategy input contract finding."""

    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class StrategyInputBar:
    """A future paper-strategy replay input bar."""

    bar_index: int
    timestamp: str
    source_path: str
    source_type: str
    source_row_number: int | None
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: float | None
    data_mode: str
    execution_mode: str


@dataclass(frozen=True)
class StrategyInputContractReport:
    """Contract report for future paper-strategy replay inputs."""

    generated_at_utc: str
    dry_run_events_path: str
    output_directory: str
    status: str
    min_bars_required: int
    input_event_count: int
    accepted_bar_count: int
    first_timestamp: str | None
    last_timestamp: str | None
    safety_notice: str
    issues: list[StrategyInputContractIssue]
    bars: list[StrategyInputBar]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data strategy input "
        "contract does not run strategies, create signals, create trade plans, "
        "connect to brokers, request live market data, place real orders, use "
        "real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> StrategyInputContractIssue:
    return StrategyInputContractIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status_from_issues(issues: Sequence[StrategyInputContractIssue]) -> str:
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


def _as_required_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _load_dry_run_events(
    dry_run_events_path: Path,
) -> tuple[list[Mapping[str, Any]], list[StrategyInputContractIssue]]:
    if not dry_run_events_path.exists():
        return [], [
            _issue(
                "fail",
                "dry_run_events_missing",
                1,
                "Replay dry-run events JSONL does not exist. Run the replay readiness gate first.",
            )
        ]

    events: list[Mapping[str, Any]] = []
    issues: list[StrategyInputContractIssue] = []
    invalid_json_lines = 0
    invalid_shape_lines = 0

    with dry_run_events_path.open("r", encoding="utf-8") as file_handle:
        for line in file_handle:
            text = line.strip()
            if not text:
                continue

            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                invalid_json_lines += 1
                continue

            if not isinstance(payload, Mapping):
                invalid_shape_lines += 1
                continue

            events.append(payload)

    if invalid_json_lines:
        issues.append(
            _issue(
                "fail",
                "dry_run_events_invalid_jsonl",
                invalid_json_lines,
                f"{invalid_json_lines} dry-run event lines are invalid JSON.",
            )
        )

    if invalid_shape_lines:
        issues.append(
            _issue(
                "fail",
                "dry_run_events_invalid_shape",
                invalid_shape_lines,
                f"{invalid_shape_lines} dry-run event lines are not JSON objects.",
            )
        )

    return events, issues


def _forbidden_keys_in_event(event: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in event.keys()
        if str(key).strip().lower() in FORBIDDEN_EXECUTION_KEYS
    }


def _bar_from_event(
    event: Mapping[str, Any],
    bar_index: int,
) -> tuple[StrategyInputBar | None, list[StrategyInputContractIssue]]:
    issues: list[StrategyInputContractIssue] = []

    event_type = str(event.get("event_type") or "").strip()
    if event_type != EXPECTED_EVENT_TYPE:
        issues.append(
            _issue(
                "warn",
                "unexpected_event_type",
                1,
                f"Unexpected dry-run event type: {event_type or 'missing'}.",
            )
        )
        return None, issues

    forbidden_keys = _forbidden_keys_in_event(event)
    if forbidden_keys:
        issues.append(
            _issue(
                "fail",
                "forbidden_execution_fields",
                len(forbidden_keys),
                (
                    "Dry-run event contains execution/trading fields that are not "
                    f"allowed in this input contract: {', '.join(sorted(forbidden_keys))}."
                ),
            )
        )

    timestamp = _as_required_text(event.get("timestamp"))
    close_price = _as_float(event.get("close"))

    missing_required = []
    if timestamp is None:
        missing_required.append("timestamp")
    if close_price is None:
        missing_required.append("close")

    if missing_required:
        issues.append(
            _issue(
                "warn",
                "unplayable_contract_event",
                1,
                f"Dry-run event missing required contract fields: {', '.join(missing_required)}.",
            )
        )
        return None, issues

    assert timestamp is not None
    assert close_price is not None

    return StrategyInputBar(
        bar_index=bar_index,
        timestamp=timestamp,
        source_path=str(event.get("source_path") or ""),
        source_type=str(event.get("source_type") or ""),
        source_row_number=_as_int(event.get("row_number")),
        open=_as_float(event.get("open")),
        high=_as_float(event.get("high")),
        low=_as_float(event.get("low")),
        close=close_price,
        volume=_as_float(event.get("volume")),
        data_mode="recorded_replay",
        execution_mode="paper_simulation_only",
    ), issues


def build_strategy_input_contract_report(
    *,
    dry_run_events_path: Path,
    output_dir: Path,
    min_bars: int = 1,
    max_events: int | None = None,
) -> StrategyInputContractReport:
    """Build a future paper-strategy input contract from dry-run events."""

    normalized_min_bars = max(min_bars, 0)
    events, issues = _load_dry_run_events(dry_run_events_path)

    if max_events is not None and max_events >= 0:
        events = events[:max_events]

    if not events:
        issues.append(
            _issue(
                "fail",
                "no_dry_run_events",
                1,
                "No dry-run events were available for strategy input contract generation.",
            )
        )

    bars: list[StrategyInputBar] = []
    for event in events:
        bar, bar_issues = _bar_from_event(event, len(bars) + 1)
        issues.extend(bar_issues)
        if bar is not None:
            bars.append(bar)

    if len(bars) < normalized_min_bars:
        issues.append(
            _issue(
                "fail",
                "insufficient_contract_bars",
                normalized_min_bars - len(bars),
                (
                    "Accepted strategy input bars are below the configured minimum. "
                    f"Required={normalized_min_bars}, actual={len(bars)}."
                ),
            )
        )

    first_timestamp = bars[0].timestamp if bars else None
    last_timestamp = bars[-1].timestamp if bars else None

    return StrategyInputContractReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dry_run_events_path=str(dry_run_events_path),
        output_directory=str(output_dir),
        status=_status_from_issues(issues),
        min_bars_required=normalized_min_bars,
        input_event_count=len(events),
        accepted_bar_count=len(bars),
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
        safety_notice=safety_notice(),
        issues=issues,
        bars=bars,
    )


def write_strategy_input_contract_report(
    report: StrategyInputContractReport,
    output_dir: Path,
) -> dict[str, Path]:
    """Write strategy input contract reports."""

    output_dir.mkdir(parents=True, exist_ok=True)

    contract_json = output_dir / "strategy_input_contract.json"
    bars_jsonl = output_dir / "strategy_input_bars.jsonl"
    contract_txt = output_dir / "strategy_input_contract.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["issues"] = [asdict(issue) for issue in report.issues]
    report_data["bars"] = [asdict(bar) for bar in report.bars]

    contract_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with bars_jsonl.open("w", encoding="utf-8", newline="\n") as file_handle:
        for bar in report.bars:
            file_handle.write(json.dumps(asdict(bar), sort_keys=True))
            file_handle.write("\n")

    lines = [
        "HQE Recorded Data Strategy Input Contract",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Dry-run events path: {report.dry_run_events_path}",
        f"Status: {report.status}",
        f"Minimum bars required: {report.min_bars_required}",
        f"Input events: {report.input_event_count}",
        f"Accepted bars: {report.accepted_bar_count}",
        f"First timestamp: {report.first_timestamp}",
        f"Last timestamp: {report.last_timestamp}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Dry-run events satisfy this strategy input contract scaffold.")
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
            f"- {contract_json}",
            f"- {bars_jsonl}",
            f"- {contract_txt}",
            f"- {manifest_json}",
            "",
            "This contract does not run strategy logic, create signals, or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    contract_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_strategy_input_contract",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "min_bars_required": report.min_bars_required,
        "input_event_count": report.input_event_count,
        "accepted_bar_count": report.accepted_bar_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "strategy_input_contract_json": str(contract_json),
            "strategy_input_bars_jsonl": str(bars_jsonl),
            "strategy_input_contract_txt": str(contract_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "strategy_input_contract_json": contract_json,
        "strategy_input_bars_jsonl": bars_jsonl,
        "strategy_input_contract_txt": contract_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_input_contract_report(
    *,
    dry_run_events_path: Path,
    output_dir: Path,
    min_bars: int = 1,
    max_events: int | None = None,
) -> tuple[StrategyInputContractReport, dict[str, Path]]:
    report = build_strategy_input_contract_report(
        dry_run_events_path=dry_run_events_path,
        output_dir=output_dir,
        min_bars=min_bars,
        max_events=max_events,
    )
    outputs = write_strategy_input_contract_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a paper-only strategy input contract from replay dry-run events."
    )
    parser.add_argument(
        "--dry-run-events",
        default="reports/paper_trading/recorded_data_replay_dry_run/dry_run_events.jsonl",
        help="Path to recorded-data replay dry-run events JSONL.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_strategy_input_contract",
        help="Directory where strategy input contract reports are written.",
    )
    parser.add_argument(
        "--min-bars",
        type=int,
        default=1,
        help="Minimum accepted bars required for pass status.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Optional maximum dry-run events to contract-check.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_strategy_input_contract_report(
        dry_run_events_path=Path(args.dry_run_events),
        output_dir=Path(args.output_dir),
        min_bars=args.min_bars,
        max_events=args.max_events,
    )

    print("HQE recorded data strategy input contract completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Input events: {report.input_event_count}")
    print(f"Accepted bars: {report.accepted_bar_count}")
    print(f"Contract report: {outputs['strategy_input_contract_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
