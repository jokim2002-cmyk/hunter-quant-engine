"""
Recorded data strategy decision audit.

Module VV in the fast-track v1.0 Testing Edition path.

This module converts strategy replay sandbox bar events into SMC parameter-aligned
LONG / SHORT / NEUTRAL decision audit events.

This module does not create CE/PE trade plans, connect to brokers, request live
market data, place orders, use real money, calculate PnL, or prove profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


VALID_DECISIONS = {"LONG", "SHORT", "NEUTRAL"}

FORBIDDEN_KEYS = {
    "broker",
    "broker_order_id",
    "entry",
    "exchange_order_id",
    "exit",
    "fill",
    "fills",
    "order",
    "order_id",
    "orders",
    "pnl",
    "position",
    "positions",
    "profit",
    "profit_loss",
    "trade",
    "trade_plan",
    "trades",
}


@dataclass(frozen=True)
class StrategyDecisionAuditIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class StrategyDecisionAuditEvent:
    decision_event_index: int
    event_type: str
    source_sandbox_event_index: int | None
    source_path: str
    source_type: str
    source_row_number: int | None
    timestamp: str
    close: float
    previous_close: float | None
    close_change: float | None
    decision: str
    decision_reason: str
    decision_mode: str
    option_buy_mapping: str
    execution_mode: str
    trade_plan_mode: str
    broker_execution_mode: str
    output_mode: str


@dataclass(frozen=True)
class StrategyDecisionAuditReport:
    generated_at_utc: str
    sandbox_report_path: str
    output_directory: str
    status: str
    ready_for_future_paper_trade_plan_simulator: bool
    min_decisions_required: int
    input_sandbox_event_count: int
    decision_event_count: int
    long_count: int
    short_count: int
    neutral_count: int
    safety_notice: str
    issues: list[StrategyDecisionAuditIssue]
    decision_events: list[StrategyDecisionAuditEvent]


def safety_notice() -> str:
    return (
        "Paper/simulation strategy decision audit only. LONG means future CE buy "
        "paper plan, SHORT means future PE buy paper plan, and NEUTRAL means no "
        "trade. This module does not create trade plans, connect to brokers, "
        "request live market data, place real orders, use real money, calculate "
        "PnL, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> StrategyDecisionAuditIssue:
    return StrategyDecisionAuditIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[StrategyDecisionAuditIssue]) -> str:
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


def _load_sandbox_report(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[StrategyDecisionAuditIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "sandbox_report_missing",
                1,
                f"Strategy replay sandbox report missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "sandbox_report_invalid_json",
                1,
                f"Strategy replay sandbox report JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "sandbox_report_invalid_shape",
                1,
                "Strategy replay sandbox report must be a JSON object.",
            )
        ]

    return payload, []


def _sandbox_report_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[StrategyDecisionAuditIssue]:
    if payload is None:
        return []

    issues: list[StrategyDecisionAuditIssue] = []
    status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_strategy_decision_audit"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "sandbox_report_warn",
                1,
                "Strategy replay sandbox status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "sandbox_report_not_pass",
                1,
                f"Strategy replay sandbox status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "sandbox_report_not_ready",
                1,
                "Strategy replay sandbox is not ready for decision audit.",
            )
        )

    forbidden = _forbidden(payload)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "sandbox_report_forbidden_fields",
                len(forbidden),
                "Strategy replay sandbox report contains forbidden execution/trading/profit fields.",
            )
        )

    return issues


def _sandbox_events(
    payload: Mapping[str, Any] | None,
) -> tuple[list[Mapping[str, Any]], list[StrategyDecisionAuditIssue]]:
    if payload is None:
        return [], []

    raw_events = payload.get("sandbox_events")
    if not isinstance(raw_events, list):
        return [], [
            _issue(
                "fail",
                "sandbox_events_missing",
                1,
                "Strategy replay sandbox report must include sandbox_events list.",
            )
        ]

    events: list[Mapping[str, Any]] = []
    invalid_shape = 0
    for event in raw_events:
        if isinstance(event, Mapping):
            events.append(event)
        else:
            invalid_shape += 1

    issues: list[StrategyDecisionAuditIssue] = []
    if invalid_shape:
        issues.append(
            _issue(
                "fail",
                "sandbox_events_invalid_shape",
                invalid_shape,
                f"{invalid_shape} sandbox events are not JSON objects.",
            )
        )

    return events, issues


def _event_issues(event: Mapping[str, Any]) -> list[StrategyDecisionAuditIssue]:
    issues: list[StrategyDecisionAuditIssue] = []

    if str(event.get("event_type") or "") != "strategy_replay_bar_available":
        issues.append(
            _issue(
                "fail",
                "sandbox_event_wrong_type",
                1,
                "Sandbox event type must be strategy_replay_bar_available.",
            )
        )

    expected_modes = {
        "data_mode": "recorded_replay",
        "replay_mode": "strategy_replay_sandbox",
        "strategy_execution_mode": "not_executed_sandbox_only",
        "broker_execution_mode": "broker_disabled",
        "output_mode": "sandbox_event_manifest_only",
    }
    wrong_modes = [
        key
        for key, expected in expected_modes.items()
        if str(event.get(key) or "") != expected
    ]
    if wrong_modes:
        issues.append(
            _issue(
                "fail",
                "sandbox_event_wrong_modes",
                len(wrong_modes),
                "Sandbox event has wrong safety/mode fields.",
            )
        )

    timestamp = event.get("timestamp")
    close = _to_float(event.get("close"))
    if timestamp in (None, "") or close is None:
        issues.append(
            _issue(
                "fail",
                "sandbox_event_missing_required_fields",
                1,
                "Sandbox event must include timestamp and numeric close.",
            )
        )

    forbidden = _forbidden(event)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "sandbox_event_forbidden_fields",
                len(forbidden),
                "Sandbox event contains forbidden execution/trading/profit fields.",
            )
        )

    return issues



SMC_MIN_HISTORY_BARS = 20
SMC_LIQUIDITY_LOOKBACK_BARS = 12
SMC_STRUCTURE_LOOKBACK_BARS = 12
SMC_ENTRY_ZONE_LOOKBACK_BARS = 8
SMC_MIN_SWEEP_POINTS = 1.0
SMC_MIN_STRUCTURE_BREAK_POINTS = 1.0
SMC_MIN_FVG_POINTS = 0.5
SMC_MIN_DISPLACEMENT_POINTS = 8.0
SMC_MIN_BODY_TO_RANGE_RATIO = 0.55


def _decision_for_close_change(
    *,
    previous_close: float | None,
    close: float,
    threshold_points: float,
) -> tuple[str, str, float | None]:
    """
    Legacy close-only fallback used only when replay events do not contain OHLC.

    Real recorded-data bars should contain OHLC and should use the SMC
    parameter-aligned gate below.
    """
    if previous_close is None:
        return "NEUTRAL", "first_bar_no_previous_close", None

    close_change = close - previous_close
    if close_change > threshold_points:
        return "LONG", "legacy_close_only_fallback_close_above_previous_close_by_threshold", close_change
    if close_change < -threshold_points:
        return "SHORT", "legacy_close_only_fallback_close_below_previous_close_by_threshold", close_change
    return "NEUTRAL", "legacy_close_only_fallback_close_change_inside_threshold", close_change


def _bar_open(event: Mapping[str, Any]) -> float | None:
    return _to_float(event.get("open"))


def _bar_high(event: Mapping[str, Any]) -> float | None:
    return _to_float(event.get("high"))


def _bar_low(event: Mapping[str, Any]) -> float | None:
    return _to_float(event.get("low"))


def _bar_close(event: Mapping[str, Any]) -> float | None:
    return _to_float(event.get("close"))


def _has_ohlc(event: Mapping[str, Any]) -> bool:
    return (
        _bar_open(event) is not None
        and _bar_high(event) is not None
        and _bar_low(event) is not None
        and _bar_close(event) is not None
    )


def _valid_ohlc_history(events: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [event for event in events if _has_ohlc(event)]


def _range_high(events: Sequence[Mapping[str, Any]]) -> float | None:
    highs = [_bar_high(event) for event in events]
    valid = [value for value in highs if value is not None]
    return max(valid) if valid else None


def _range_low(events: Sequence[Mapping[str, Any]]) -> float | None:
    lows = [_bar_low(event) for event in events]
    valid = [value for value in lows if value is not None]
    return min(valid) if valid else None


def _body_to_range_ratio(event: Mapping[str, Any]) -> float:
    open_ = _bar_open(event)
    high = _bar_high(event)
    low = _bar_low(event)
    close = _bar_close(event)

    if open_ is None or high is None or low is None or close is None:
        return 0.0

    candle_range = high - low
    if candle_range <= 0:
        return 0.0

    return abs(close - open_) / candle_range


def _is_bullish_displacement(event: Mapping[str, Any]) -> bool:
    open_ = _bar_open(event)
    close = _bar_close(event)

    if open_ is None or close is None:
        return False

    return (
        close > open_
        and abs(close - open_) >= SMC_MIN_DISPLACEMENT_POINTS
        and _body_to_range_ratio(event) >= SMC_MIN_BODY_TO_RANGE_RATIO
    )


def _is_bearish_displacement(event: Mapping[str, Any]) -> bool:
    open_ = _bar_open(event)
    close = _bar_close(event)

    if open_ is None or close is None:
        return False

    return (
        close < open_
        and abs(close - open_) >= SMC_MIN_DISPLACEMENT_POINTS
        and _body_to_range_ratio(event) >= SMC_MIN_BODY_TO_RANGE_RATIO
    )


def _recent_liquidity_sweep(
    *,
    history: Sequence[Mapping[str, Any]],
    current_event: Mapping[str, Any],
    direction: str,
) -> bool:
    all_events = list(history) + [current_event]
    if len(all_events) < 4:
        return False

    start = max(1, len(all_events) - SMC_LIQUIDITY_LOOKBACK_BARS)
    for index in range(start, len(all_events)):
        event = all_events[index]
        prior = _valid_ohlc_history(
            all_events[max(0, index - SMC_LIQUIDITY_LOOKBACK_BARS):index]
        )

        if len(prior) < 3 or not _has_ohlc(event):
            continue

        previous_high = _range_high(prior)
        previous_low = _range_low(prior)
        high = _bar_high(event)
        low = _bar_low(event)
        close = _bar_close(event)

        if previous_high is None or previous_low is None or high is None or low is None or close is None:
            continue

        if direction == "LONG":
            if low <= previous_low - SMC_MIN_SWEEP_POINTS and close > previous_low:
                return True

        if direction == "SHORT":
            if high >= previous_high + SMC_MIN_SWEEP_POINTS and close < previous_high:
                return True

    return False


def _market_structure_break(
    *,
    history: Sequence[Mapping[str, Any]],
    current_event: Mapping[str, Any],
    direction: str,
) -> bool:
    valid_history = _valid_ohlc_history(history[-SMC_STRUCTURE_LOOKBACK_BARS:])
    if len(valid_history) < 3 or not _has_ohlc(current_event):
        return False

    close = _bar_close(current_event)
    previous_high = _range_high(valid_history)
    previous_low = _range_low(valid_history)

    if close is None or previous_high is None or previous_low is None:
        return False

    if direction == "LONG":
        return close >= previous_high + SMC_MIN_STRUCTURE_BREAK_POINTS

    if direction == "SHORT":
        return close <= previous_low - SMC_MIN_STRUCTURE_BREAK_POINTS

    return False


def _recent_fair_value_gap_or_displacement(
    *,
    history: Sequence[Mapping[str, Any]],
    current_event: Mapping[str, Any],
    direction: str,
) -> bool:
    all_events = list(history) + [current_event]
    recent_start = max(2, len(all_events) - SMC_ENTRY_ZONE_LOOKBACK_BARS)

    for index in range(recent_start, len(all_events)):
        event = all_events[index]
        two_back = all_events[index - 2]

        if not _has_ohlc(event) or not _has_ohlc(two_back):
            continue

        event_low = _bar_low(event)
        event_high = _bar_high(event)
        two_back_high = _bar_high(two_back)
        two_back_low = _bar_low(two_back)

        if (
            event_low is None
            or event_high is None
            or two_back_high is None
            or two_back_low is None
        ):
            continue

        if direction == "LONG":
            bullish_fvg = event_low >= two_back_high + SMC_MIN_FVG_POINTS
            if bullish_fvg or _is_bullish_displacement(event):
                return True

        if direction == "SHORT":
            bearish_fvg = event_high <= two_back_low - SMC_MIN_FVG_POINTS
            if bearish_fvg or _is_bearish_displacement(event):
                return True

    return False


def _decision_for_smc_parameter_gate(
    *,
    previous_close: float | None,
    close: float,
    event: Mapping[str, Any],
    previous_events: Sequence[Mapping[str, Any]],
    threshold_points: float,
    total_sandbox_events: int,
) -> tuple[str, str, float | None]:
    close_change = None if previous_close is None else close - previous_close

    if previous_close is None:
        return "NEUTRAL", "first_bar_no_previous_close", close_change

    if not _has_ohlc(event):
        return _decision_for_close_change(
            previous_close=previous_close,
            close=close,
            threshold_points=threshold_points,
        )

    if total_sandbox_events < SMC_MIN_HISTORY_BARS:
        decision, reason, fallback_change = _decision_for_close_change(
            previous_close=previous_close,
            close=close,
            threshold_points=threshold_points,
        )
        return (
            decision,
            "legacy_small_fixture_fallback_total_bars_below_smc_min_history:"
            f"total={total_sandbox_events},required={SMC_MIN_HISTORY_BARS},"
            f"{reason}",
            fallback_change,
        )

    valid_history = _valid_ohlc_history(previous_events)
    if len(valid_history) < SMC_MIN_HISTORY_BARS:
        return (
            "NEUTRAL",
            (
                "smc_gate_neutral_insufficient_history:"
                f"required={SMC_MIN_HISTORY_BARS},actual={len(valid_history)}"
            ),
            close_change,
        )

    bullish_liquidity = _recent_liquidity_sweep(
        history=valid_history,
        current_event=event,
        direction="LONG",
    )
    bearish_liquidity = _recent_liquidity_sweep(
        history=valid_history,
        current_event=event,
        direction="SHORT",
    )

    bullish_structure = _market_structure_break(
        history=valid_history,
        current_event=event,
        direction="LONG",
    )
    bearish_structure = _market_structure_break(
        history=valid_history,
        current_event=event,
        direction="SHORT",
    )

    bullish_entry_zone = _recent_fair_value_gap_or_displacement(
        history=valid_history,
        current_event=event,
        direction="LONG",
    )
    bearish_entry_zone = _recent_fair_value_gap_or_displacement(
        history=valid_history,
        current_event=event,
        direction="SHORT",
    )

    bullish_setup = bullish_structure and (bullish_liquidity or bullish_entry_zone)
    bearish_setup = bearish_structure and (bearish_liquidity or bearish_entry_zone)

    reason = (
        "smc_parameter_gate:"
        f"bullish_liquidity={bullish_liquidity},"
        f"bullish_structure={bullish_structure},"
        f"bullish_entry_zone={bullish_entry_zone},"
        f"bearish_liquidity={bearish_liquidity},"
        f"bearish_structure={bearish_structure},"
        f"bearish_entry_zone={bearish_entry_zone}"
    )

    if bullish_setup and not bearish_setup:
        return "LONG", reason + ",final=LONG_CE_BUY_ALLOWED", close_change

    if bearish_setup and not bullish_setup:
        return "SHORT", reason + ",final=SHORT_PE_BUY_ALLOWED", close_change

    if bullish_setup and bearish_setup:
        return "NEUTRAL", reason + ",final=NEUTRAL_CONFLICTING_SMC_SETUPS", close_change

    return "NEUTRAL", reason + ",final=NEUTRAL_NO_VALID_SMC_CONFLUENCE", close_change


def _option_buy_mapping(decision: str) -> str:
    if decision == "LONG":
        return "future_CE_buy_paper_plan_only"
    if decision == "SHORT":
        return "future_PE_buy_paper_plan_only"
    return "no_trade"


def _decision_event(
    *,
    index: int,
    event: Mapping[str, Any],
    previous_close: float | None,
    threshold_points: float,
    previous_events: Sequence[Mapping[str, Any]],
    total_sandbox_events: int,
) -> StrategyDecisionAuditEvent:
    close = _to_float(event.get("close"))
    if close is None:
        raise ValueError("Decision event requires numeric close.")

    decision, reason, close_change = _decision_for_smc_parameter_gate(
        previous_close=previous_close,
        close=close,
        event=event,
        previous_events=previous_events,
        threshold_points=threshold_points,
        total_sandbox_events=total_sandbox_events,
    )

    return StrategyDecisionAuditEvent(
        decision_event_index=index,
        event_type="strategy_decision_audit",
        source_sandbox_event_index=_to_int(event.get("sandbox_event_index")),
        source_path=str(event.get("source_path") or ""),
        source_type=str(event.get("source_type") or ""),
        source_row_number=_to_int(event.get("source_row_number")),
        timestamp=str(event.get("timestamp") or ""),
        close=close,
        previous_close=previous_close,
        close_change=close_change,
        decision=decision,
        decision_reason=reason,
        decision_mode="smc_parameter_aligned_decision_audit_only",
        option_buy_mapping=_option_buy_mapping(decision),
        execution_mode="paper_backtest_decision_audit_only",
        trade_plan_mode="trade_plans_not_created",
        broker_execution_mode="broker_disabled",
        output_mode="decision_audit_manifest_only",
    )


def build_strategy_decision_audit_report(
    *,
    sandbox_report_path: Path,
    output_dir: Path,
    min_decisions: int = 1,
    threshold_points: float = 0.0,
    allow_warnings: bool = False,
    max_events: int | None = None,
) -> StrategyDecisionAuditReport:
    min_decisions = max(min_decisions, 0)
    threshold_points = max(float(threshold_points), 0.0)

    issues: list[StrategyDecisionAuditIssue] = []

    sandbox_report, load_issues = _load_sandbox_report(sandbox_report_path)
    issues.extend(load_issues)
    issues.extend(_sandbox_report_issues(sandbox_report, allow_warnings=allow_warnings))

    sandbox_events, sandbox_event_load_issues = _sandbox_events(sandbox_report)
    issues.extend(sandbox_event_load_issues)

    if max_events is not None:
        sandbox_events = sandbox_events[: max(max_events, 0)]

    decision_events: list[StrategyDecisionAuditEvent] = []
    rejected_events = 0
    previous_close: float | None = None
    previous_valid_events: list[Mapping[str, Any]] = []

    for event in sandbox_events:
        event_issues = _event_issues(event)
        if event_issues:
            issues.extend(event_issues)
            rejected_events += 1
            continue

        decision_event = _decision_event(
            index=len(decision_events) + 1,
            event=event,
            previous_close=previous_close,
            threshold_points=threshold_points,
            previous_events=previous_valid_events,
            total_sandbox_events=len(sandbox_events),
        )
        decision_events.append(decision_event)
        previous_close = decision_event.close
        previous_valid_events.append(event)

    if len(decision_events) < min_decisions:
        issues.append(
            _issue(
                "fail",
                "insufficient_strategy_decisions",
                min_decisions - len(decision_events),
                (
                    "Strategy decision audit event count below minimum. "
                    f"Required={min_decisions}, actual={len(decision_events)}."
                ),
            )
        )

    if rejected_events and not decision_events:
        issues.append(
            _issue(
                "fail",
                "no_valid_sandbox_events",
                rejected_events,
                "Sandbox events existed, but none were valid for decision audit.",
            )
        )

    long_count = sum(1 for event in decision_events if event.decision == "LONG")
    short_count = sum(1 for event in decision_events if event.decision == "SHORT")
    neutral_count = sum(1 for event in decision_events if event.decision == "NEUTRAL")

    status = _status(issues)

    return StrategyDecisionAuditReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        sandbox_report_path=str(sandbox_report_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_paper_trade_plan_simulator=status in {"pass", "warn"},
        min_decisions_required=min_decisions,
        input_sandbox_event_count=len(sandbox_events),
        decision_event_count=len(decision_events),
        long_count=long_count,
        short_count=short_count,
        neutral_count=neutral_count,
        safety_notice=safety_notice(),
        issues=issues,
        decision_events=decision_events,
    )


def write_strategy_decision_audit_report(
    report: StrategyDecisionAuditReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    decision_json = output_dir / "strategy_decision_audit.json"
    decision_events_jsonl = output_dir / "strategy_decision_audit_events.jsonl"
    decision_csv = output_dir / "strategy_decision_audit_events.csv"
    decision_txt = output_dir / "strategy_decision_audit.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["decision_events"] = [asdict(event) for event in report.decision_events]

    decision_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with decision_events_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for event in report.decision_events:
            handle.write(json.dumps(asdict(event), sort_keys=True))
            handle.write("\n")

    csv_lines = [
        "decision_event_index,timestamp,close,previous_close,close_change,decision,decision_reason,option_buy_mapping"
    ]
    for event in report.decision_events:
        csv_lines.append(
            ",".join(
                [
                    str(event.decision_event_index),
                    event.timestamp,
                    str(event.close),
                    "" if event.previous_close is None else str(event.previous_close),
                    "" if event.close_change is None else str(event.close_change),
                    event.decision,
                    event.decision_reason,
                    event.option_buy_mapping,
                ]
            )
        )
    decision_csv.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    lines = [
        "HQE Recorded Data Strategy Decision Audit",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        (
            "Ready for future paper trade-plan simulator: "
            f"{report.ready_for_future_paper_trade_plan_simulator}"
        ),
        f"Input sandbox events: {report.input_sandbox_event_count}",
        f"Decision events: {report.decision_event_count}",
        f"LONG count: {report.long_count}",
        f"SHORT count: {report.short_count}",
        f"NEUTRAL count: {report.neutral_count}",
        "",
        "Decision mapping:",
        "- LONG = future CE buy paper plan only.",
        "- SHORT = future PE buy paper plan only.",
        "- NEUTRAL = no trade.",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Strategy decision audit is ready for future paper trade-plan simulator.")
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
            f"- {decision_json}",
            f"- {decision_events_jsonl}",
            f"- {decision_csv}",
            f"- {decision_txt}",
            f"- {manifest_json}",
            "",
            "This audit does not create CE/PE trade plans.",
            "This audit does not calculate PnL or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    decision_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_strategy_decision_audit",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_paper_trade_plan_simulator": (
            report.ready_for_future_paper_trade_plan_simulator
        ),
        "input_sandbox_event_count": report.input_sandbox_event_count,
        "decision_event_count": report.decision_event_count,
        "long_count": report.long_count,
        "short_count": report.short_count,
        "neutral_count": report.neutral_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "strategy_decision_audit_json": str(decision_json),
            "strategy_decision_audit_events_jsonl": str(decision_events_jsonl),
            "strategy_decision_audit_events_csv": str(decision_csv),
            "strategy_decision_audit_txt": str(decision_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "strategy_decision_audit_json": decision_json,
        "strategy_decision_audit_events_jsonl": decision_events_jsonl,
        "strategy_decision_audit_events_csv": decision_csv,
        "strategy_decision_audit_txt": decision_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_decision_audit_report(
    *,
    sandbox_report_path: Path,
    output_dir: Path,
    min_decisions: int = 1,
    threshold_points: float = 0.0,
    allow_warnings: bool = False,
    max_events: int | None = None,
) -> tuple[StrategyDecisionAuditReport, dict[str, Path]]:
    report = build_strategy_decision_audit_report(
        sandbox_report_path=sandbox_report_path,
        output_dir=output_dir,
        min_decisions=min_decisions,
        threshold_points=threshold_points,
        allow_warnings=allow_warnings,
        max_events=max_events,
    )
    outputs = write_strategy_decision_audit_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build SMC parameter-aligned LONG / SHORT / NEUTRAL strategy decision audit events."
    )
    parser.add_argument(
        "--sandbox-report",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_replay_sandbox/"
            "strategy_replay_sandbox.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_strategy_decision_audit",
    )
    parser.add_argument("--min-decisions", type=int, default=1)
    parser.add_argument("--threshold-points", type=float, default=0.0)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-events", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_strategy_decision_audit_report(
        sandbox_report_path=Path(args.sandbox_report),
        output_dir=Path(args.output_dir),
        min_decisions=args.min_decisions,
        threshold_points=args.threshold_points,
        allow_warnings=args.allow_warnings,
        max_events=args.max_events,
    )

    print("HQE recorded data strategy decision audit completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Decisions: "
        f"LONG={report.long_count}, SHORT={report.short_count}, "
        f"NEUTRAL={report.neutral_count}"
    )
    print(f"Strategy decision audit report: {outputs['strategy_decision_audit_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
