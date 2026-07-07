"""
Recorded data strategy replay sandbox.

First v1.0 Testing Edition backtest phase module.

This module converts recorded-data strategy input bars into deterministic
strategy replay sandbox events. It prepares safe inputs for future
LONG / SHORT / NEUTRAL decision audit modules.

This module does not generate signals, create trade plans, connect to brokers,
request live market data, place orders, use real money, calculate PnL, or prove
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
class StrategyReplaySandboxIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class StrategyReplaySandboxEvent:
    sandbox_event_index: int
    event_type: str
    source_path: str
    source_type: str
    source_row_number: int | None
    timestamp: str
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: float | None
    data_mode: str
    replay_mode: str
    strategy_execution_mode: str
    signal_mode: str
    trade_plan_mode: str
    broker_execution_mode: str
    output_mode: str


@dataclass(frozen=True)
class StrategyReplaySandboxReport:
    generated_at_utc: str
    consumer_evidence_readiness_path: str
    strategy_input_bars_path: str
    output_directory: str
    status: str
    ready_for_future_strategy_decision_audit: bool
    min_bars_required: int
    input_bar_count: int
    sandbox_event_count: int
    safety_notice: str
    issues: list[StrategyReplaySandboxIssue]
    sandbox_events: list[StrategyReplaySandboxEvent]


def safety_notice() -> str:
    return (
        "Paper/simulation backtest sandbox only. This module does not generate "
        "signals, create trade plans, connect to brokers, request live market "
        "data, place real orders, use real money, calculate PnL, or prove "
        "profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> StrategyReplaySandboxIssue:
    return StrategyReplaySandboxIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[StrategyReplaySandboxIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_int(value: Any) -> int | None:
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
) -> tuple[Mapping[str, Any] | None, list[StrategyReplaySandboxIssue]]:
    if not path.exists():
        return None, [_issue("fail", missing_code, 1, f"Required JSON file missing: {path}")]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [_issue("fail", invalid_code, 1, f"JSON parse failed: {exc}")]

    if not isinstance(payload, Mapping):
        return None, [_issue("fail", invalid_code, 1, "JSON payload must be an object.")]

    return payload, []


def _load_jsonl_objects(path: Path) -> tuple[list[Mapping[str, Any]], list[StrategyReplaySandboxIssue]]:
    if not path.exists():
        return [], [
            _issue(
                "fail",
                "strategy_input_bars_missing",
                1,
                f"Strategy input bars JSONL missing: {path}",
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

    issues: list[StrategyReplaySandboxIssue] = []
    if invalid_json:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bars_invalid_jsonl",
                invalid_json,
                f"{invalid_json} strategy input bar lines are invalid JSON.",
            )
        )
    if invalid_shape:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bars_invalid_shape",
                invalid_shape,
                f"{invalid_shape} strategy input bar lines are not JSON objects.",
            )
        )

    return rows, issues


def _readiness_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[StrategyReplaySandboxIssue]:
    if payload is None:
        return []

    status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_consumer_evidence_release"))

    issues: list[StrategyReplaySandboxIssue] = []

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "consumer_evidence_readiness_warn",
                1,
                "Consumer evidence readiness status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "consumer_evidence_readiness_not_pass",
                1,
                f"Consumer evidence readiness status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "consumer_evidence_readiness_not_ready",
                1,
                "Consumer evidence readiness is not ready for future release.",
            )
        )

    forbidden = _forbidden(payload)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "consumer_evidence_readiness_forbidden_fields",
                len(forbidden),
                "Consumer evidence readiness contains forbidden execution/trading/profit fields.",
            )
        )

    return issues


def _bar_issues(bar: Mapping[str, Any]) -> list[StrategyReplaySandboxIssue]:
    issues: list[StrategyReplaySandboxIssue] = []

    timestamp = bar.get("timestamp")
    close = _to_float(bar.get("close"))

    if timestamp in (None, "") or close is None:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bar_missing_required_fields",
                1,
                "Strategy input bar must include timestamp and close.",
            )
        )

    data_mode = str(bar.get("data_mode") or "")
    execution_mode = str(bar.get("execution_mode") or "")
    if data_mode != "recorded_replay" or execution_mode != "paper_simulation_only":
        issues.append(
            _issue(
                "fail",
                "strategy_input_bar_wrong_modes",
                1,
                "Strategy input bar must be recorded_replay and paper_simulation_only.",
            )
        )

    forbidden = _forbidden(bar)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bar_forbidden_fields",
                len(forbidden),
                "Strategy input bar contains forbidden execution/trading/profit fields.",
            )
        )

    return issues


def _sandbox_event(index: int, bar: Mapping[str, Any]) -> StrategyReplaySandboxEvent:
    return StrategyReplaySandboxEvent(
        sandbox_event_index=index,
        event_type="strategy_replay_bar_available",
        source_path=str(bar.get("source_path") or ""),
        source_type=str(bar.get("source_type") or ""),
        source_row_number=_to_int(bar.get("source_row_number") or bar.get("row_number")),
        timestamp=str(bar.get("timestamp") or ""),
        open=_to_float(bar.get("open")),
        high=_to_float(bar.get("high")),
        low=_to_float(bar.get("low")),
        close=_to_float(bar.get("close")) or 0.0,
        volume=_to_float(bar.get("volume")),
        data_mode="recorded_replay",
        replay_mode="strategy_replay_sandbox",
        strategy_execution_mode="not_executed_sandbox_only",
        signal_mode="signals_not_generated",
        trade_plan_mode="trade_plans_not_created",
        broker_execution_mode="broker_disabled",
        output_mode="sandbox_event_manifest_only",
    )


def build_strategy_replay_sandbox_report(
    *,
    consumer_evidence_readiness_path: Path,
    strategy_input_bars_path: Path,
    output_dir: Path,
    min_bars: int = 1,
    allow_warnings: bool = False,
    max_bars: int | None = None,
) -> StrategyReplaySandboxReport:
    min_bars = max(min_bars, 0)

    issues: list[StrategyReplaySandboxIssue] = []

    readiness, readiness_issues = _load_json_object(
        consumer_evidence_readiness_path,
        "consumer_evidence_readiness_missing",
        "consumer_evidence_readiness_invalid_json",
    )
    bars, bar_load_issues = _load_jsonl_objects(strategy_input_bars_path)

    issues.extend(readiness_issues)
    issues.extend(bar_load_issues)
    issues.extend(_readiness_issues(readiness, allow_warnings=allow_warnings))

    if max_bars is not None:
        bars = bars[: max(max_bars, 0)]

    sandbox_events: list[StrategyReplaySandboxEvent] = []
    rejected_bar_count = 0

    for bar in bars:
        bar_issues = _bar_issues(bar)
        if bar_issues:
            issues.extend(bar_issues)
            rejected_bar_count += 1
            continue
        sandbox_events.append(_sandbox_event(len(sandbox_events) + 1, bar))

    if len(sandbox_events) < min_bars:
        issues.append(
            _issue(
                "fail",
                "insufficient_strategy_replay_sandbox_bars",
                min_bars - len(sandbox_events),
                (
                    "Strategy replay sandbox event count below minimum. "
                    f"Required={min_bars}, actual={len(sandbox_events)}."
                ),
            )
        )

    if rejected_bar_count and not sandbox_events:
        issues.append(
            _issue(
                "fail",
                "no_valid_strategy_input_bars",
                rejected_bar_count,
                "Strategy input bars existed, but none were valid for sandbox replay.",
            )
        )

    status = _status(issues)

    return StrategyReplaySandboxReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        consumer_evidence_readiness_path=str(consumer_evidence_readiness_path),
        strategy_input_bars_path=str(strategy_input_bars_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_strategy_decision_audit=status in {"pass", "warn"},
        min_bars_required=min_bars,
        input_bar_count=len(bars),
        sandbox_event_count=len(sandbox_events),
        safety_notice=safety_notice(),
        issues=issues,
        sandbox_events=sandbox_events,
    )


def write_strategy_replay_sandbox_report(
    report: StrategyReplaySandboxReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    sandbox_json = output_dir / "strategy_replay_sandbox.json"
    sandbox_events_jsonl = output_dir / "strategy_replay_sandbox_events.jsonl"
    sandbox_txt = output_dir / "strategy_replay_sandbox.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["sandbox_events"] = [asdict(event) for event in report.sandbox_events]

    sandbox_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with sandbox_events_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for event in report.sandbox_events:
            handle.write(json.dumps(asdict(event), sort_keys=True))
            handle.write("\n")

    lines = [
        "HQE Recorded Data Strategy Replay Sandbox",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        (
            "Ready for future strategy decision audit: "
            f"{report.ready_for_future_strategy_decision_audit}"
        ),
        f"Input bars: {report.input_bar_count}",
        f"Sandbox events: {report.sandbox_event_count}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Strategy replay sandbox events are ready for future decision audit.")
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
            f"- {sandbox_json}",
            f"- {sandbox_events_jsonl}",
            f"- {sandbox_txt}",
            f"- {manifest_json}",
            "",
            "This sandbox does not generate LONG/SHORT/NEUTRAL signals.",
            "This sandbox does not create trade plans, calculate PnL, or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    sandbox_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_strategy_replay_sandbox",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_strategy_decision_audit": (
            report.ready_for_future_strategy_decision_audit
        ),
        "input_bar_count": report.input_bar_count,
        "sandbox_event_count": report.sandbox_event_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "strategy_replay_sandbox_json": str(sandbox_json),
            "strategy_replay_sandbox_events_jsonl": str(sandbox_events_jsonl),
            "strategy_replay_sandbox_txt": str(sandbox_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "strategy_replay_sandbox_json": sandbox_json,
        "strategy_replay_sandbox_events_jsonl": sandbox_events_jsonl,
        "strategy_replay_sandbox_txt": sandbox_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_replay_sandbox_report(
    *,
    consumer_evidence_readiness_path: Path,
    strategy_input_bars_path: Path,
    output_dir: Path,
    min_bars: int = 1,
    allow_warnings: bool = False,
    max_bars: int | None = None,
) -> tuple[StrategyReplaySandboxReport, dict[str, Path]]:
    report = build_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=consumer_evidence_readiness_path,
        strategy_input_bars_path=strategy_input_bars_path,
        output_dir=output_dir,
        min_bars=min_bars,
        allow_warnings=allow_warnings,
        max_bars=max_bars,
    )
    outputs = write_strategy_replay_sandbox_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build recorded-data strategy replay sandbox events."
    )
    parser.add_argument(
        "--consumer-evidence-readiness",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness/"
            "paper_strategy_adapter_dry_run_consumer_evidence_readiness.json"
        ),
    )
    parser.add_argument(
        "--strategy-input-bars",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_input_contract/"
            "strategy_input_bars.jsonl"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_strategy_replay_sandbox",
    )
    parser.add_argument("--min-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-bars", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_strategy_replay_sandbox_report(
        consumer_evidence_readiness_path=Path(args.consumer_evidence_readiness),
        strategy_input_bars_path=Path(args.strategy_input_bars),
        output_dir=Path(args.output_dir),
        min_bars=args.min_bars,
        allow_warnings=args.allow_warnings,
        max_bars=args.max_bars,
    )

    print("HQE recorded data strategy replay sandbox completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Sandbox events: {report.sandbox_event_count}")
    print(f"Strategy replay sandbox report: {outputs['strategy_replay_sandbox_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
