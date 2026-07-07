"""
Recorded data paper fill and exit simulator.

Module YY in the fast-track v1.0 Testing Edition path.

This module converts CE/PE paper option trade plans into deterministic paper
entry/exit fill lifecycle events using recorded decision audit close references.

Safety mapping:
- LONG / CE BUY paper plan benefits when underlying close moves up.
- SHORT / PE BUY paper plan benefits when underlying close moves down.
- NEUTRAL has no trade plan and remains out of fill simulation.

This module does not connect to brokers, request live market data, place orders,
use real money, calculate account PnL, or prove profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPECTED_PLAN_MODES = {
    "event_type": "paper_option_trade_plan_created",
    "option_action": "BUY",
    "plan_mode": "paper_option_buy_plan_only",
    "execution_mode": "paper_backtest_plan_only",
    "fill_mode": "fills_not_simulated",
    "broker_execution_mode": "broker_disabled",
    "order_mode": "orders_not_created",
    "output_mode": "paper_trade_plan_manifest_only",
}

FORBIDDEN_KEYS = {
    "broker",
    "broker_order_id",
    "exchange_order_id",
    "live_order",
    "order",
    "order_id",
    "orders",
    "pnl",
    "profit",
    "profit_loss",
    "real_money",
}


@dataclass(frozen=True)
class PaperFillExitIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperFillExitLifecycle:
    paper_fill_exit_index: int
    event_type: str
    paper_fill_exit_id: str
    source_paper_trade_plan_id: str
    source_paper_trade_plan_index: int | None
    source_decision_event_index: int | None
    underlying_symbol: str
    decision: str
    option_type: str
    option_action: str
    entry_timestamp: str
    exit_timestamp: str
    entry_underlying_close_reference: float
    exit_underlying_close_reference: float
    entry_option_price_reference: float
    exit_option_price_reference: float
    option_points_result: float
    exit_reason: str
    holding_bars: int
    quantity_lots: int
    lot_size: int
    stop_loss_points: float
    target_points: float
    lifecycle_mode: str
    fill_mode: str
    broker_execution_mode: str
    order_mode: str
    account_pnl_mode: str
    output_mode: str


@dataclass(frozen=True)
class PaperFillExitReport:
    generated_at_utc: str
    trade_plan_report_path: str
    decision_audit_path: str
    output_directory: str
    status: str
    ready_for_future_backtest_ledger: bool
    min_lifecycles_required: int
    paper_trade_plan_count: int
    paper_fill_exit_lifecycle_count: int
    ce_lifecycle_count: int
    pe_lifecycle_count: int
    target_exit_count: int
    stop_loss_exit_count: int
    time_exit_count: int
    safety_notice: str
    issues: list[PaperFillExitIssue]
    paper_fill_exit_lifecycles: list[PaperFillExitLifecycle]


def safety_notice() -> str:
    return (
        "Paper/simulation fill and exit simulator only. This module creates "
        "deterministic paper entry/exit lifecycle references for CE/PE BUY paper "
        "plans. It does not connect to brokers, request live market data, place "
        "real orders, use real money, calculate account PnL, or prove profitability."
    )


def _issue(severity: str, code: str, count: int, message: str) -> PaperFillExitIssue:
    return PaperFillExitIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperFillExitIssue]) -> str:
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
) -> tuple[Mapping[str, Any] | None, list[PaperFillExitIssue]]:
    if not path.exists():
        return None, [_issue("fail", missing_code, 1, f"Required JSON file missing: {path}")]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [_issue("fail", invalid_code, 1, f"JSON parse failed: {exc}")]

    if not isinstance(payload, Mapping):
        return None, [_issue("fail", invalid_code, 1, "JSON payload must be an object.")]

    return payload, []


def _trade_plan_report_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperFillExitIssue]:
    if payload is None:
        return []

    issues: list[PaperFillExitIssue] = []
    status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_paper_fill_simulator"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "trade_plan_report_warn",
                1,
                "Paper option trade-plan simulator status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "trade_plan_report_not_pass",
                1,
                f"Paper option trade-plan simulator status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "trade_plan_report_not_ready",
                1,
                "Paper option trade-plan simulator is not ready for future fill simulator.",
            )
        )

    forbidden = _forbidden(payload)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "trade_plan_report_forbidden_fields",
                len(forbidden),
                "Trade-plan report contains forbidden broker/order/profit fields.",
            )
        )

    return issues


def _decision_audit_report_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperFillExitIssue]:
    if payload is None:
        return []

    issues: list[PaperFillExitIssue] = []
    status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_paper_trade_plan_simulator"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "decision_audit_warn",
                1,
                "Strategy decision audit status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "decision_audit_not_pass",
                1,
                f"Strategy decision audit status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "decision_audit_not_ready",
                1,
                "Strategy decision audit is not ready for paper trade-plan simulation.",
            )
        )

    forbidden = _forbidden(payload)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "decision_audit_forbidden_fields",
                len(forbidden),
                "Decision audit contains forbidden broker/order/profit fields.",
            )
        )

    return issues


def _paper_trade_plans(
    payload: Mapping[str, Any] | None,
) -> tuple[list[Mapping[str, Any]], list[PaperFillExitIssue]]:
    if payload is None:
        return [], []

    raw_plans = payload.get("paper_trade_plans")
    if not isinstance(raw_plans, list):
        return [], [
            _issue(
                "fail",
                "paper_trade_plans_missing",
                1,
                "Trade-plan report must include paper_trade_plans list.",
            )
        ]

    plans: list[Mapping[str, Any]] = []
    invalid_shape = 0
    for plan in raw_plans:
        if isinstance(plan, Mapping):
            plans.append(plan)
        else:
            invalid_shape += 1

    issues: list[PaperFillExitIssue] = []
    if invalid_shape:
        issues.append(
            _issue(
                "fail",
                "paper_trade_plans_invalid_shape",
                invalid_shape,
                f"{invalid_shape} paper trade plans are not JSON objects.",
            )
        )

    return plans, issues


def _decision_events_by_index(
    payload: Mapping[str, Any] | None,
) -> tuple[dict[int, Mapping[str, Any]], list[PaperFillExitIssue]]:
    if payload is None:
        return {}, []

    raw_events = payload.get("decision_events")
    if not isinstance(raw_events, list):
        return {}, [
            _issue(
                "fail",
                "decision_events_missing",
                1,
                "Decision audit report must include decision_events list.",
            )
        ]

    events: dict[int, Mapping[str, Any]] = {}
    invalid_shape = 0
    missing_index = 0

    for event in raw_events:
        if not isinstance(event, Mapping):
            invalid_shape += 1
            continue
        index = _to_int(event.get("decision_event_index"))
        if index is None:
            missing_index += 1
            continue
        events[index] = event

    issues: list[PaperFillExitIssue] = []
    if invalid_shape:
        issues.append(
            _issue(
                "fail",
                "decision_events_invalid_shape",
                invalid_shape,
                f"{invalid_shape} decision events are not JSON objects.",
            )
        )
    if missing_index:
        issues.append(
            _issue(
                "fail",
                "decision_events_missing_index",
                missing_index,
                f"{missing_index} decision events are missing decision_event_index.",
            )
        )

    return events, issues


def _plan_issues(plan: Mapping[str, Any]) -> list[PaperFillExitIssue]:
    issues: list[PaperFillExitIssue] = []

    wrong_modes = [
        key
        for key, expected in EXPECTED_PLAN_MODES.items()
        if str(plan.get(key) or "") != expected
    ]
    if wrong_modes:
        issues.append(
            _issue(
                "fail",
                "paper_trade_plan_wrong_modes",
                len(wrong_modes),
                "Paper trade plan has wrong safety/mode fields.",
            )
        )

    decision = str(plan.get("decision") or "")
    option_type = str(plan.get("option_type") or "")
    option_action = str(plan.get("option_action") or "")

    if decision not in {"LONG", "SHORT"}:
        issues.append(
            _issue(
                "fail",
                "paper_trade_plan_invalid_decision",
                1,
                "Paper trade plan decision must be LONG or SHORT.",
            )
        )

    if decision == "LONG" and option_type != "CE":
        issues.append(
            _issue(
                "fail",
                "paper_trade_plan_wrong_option_type",
                1,
                "LONG paper trade plan must use CE.",
            )
        )

    if decision == "SHORT" and option_type != "PE":
        issues.append(
            _issue(
                "fail",
                "paper_trade_plan_wrong_option_type",
                1,
                "SHORT paper trade plan must use PE.",
            )
        )

    if option_action != "BUY":
        issues.append(
            _issue(
                "fail",
                "paper_trade_plan_wrong_action",
                1,
                "Paper trade plan action must be BUY only.",
            )
        )

    source_index = _to_int(plan.get("source_decision_event_index"))
    entry_reference = _to_float(plan.get("underlying_close_reference"))
    if source_index is None or entry_reference is None or plan.get("timestamp") in (None, ""):
        issues.append(
            _issue(
                "fail",
                "paper_trade_plan_missing_required_fields",
                1,
                "Paper trade plan must include source decision index, timestamp, and underlying close reference.",
            )
        )

    forbidden = _forbidden(plan)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "paper_trade_plan_forbidden_fields",
                len(forbidden),
                "Paper trade plan contains forbidden broker/order/profit fields.",
            )
        )

    return issues


def _future_decision_events(
    *,
    source_index: int,
    decision_events: Mapping[int, Mapping[str, Any]],
    max_holding_bars: int,
) -> list[Mapping[str, Any]]:
    future: list[Mapping[str, Any]] = []

    for index in range(source_index + 1, source_index + max(max_holding_bars, 1) + 1):
        event = decision_events.get(index)
        if event is not None:
            future.append(event)

    return future


def _option_move_for_plan(
    *,
    decision: str,
    entry_underlying: float,
    current_underlying: float,
) -> float:
    if decision == "LONG":
        return current_underlying - entry_underlying
    return entry_underlying - current_underlying


def _simulate_exit(
    *,
    plan: Mapping[str, Any],
    decision_events: Mapping[int, Mapping[str, Any]],
    default_option_price_reference: float,
) -> tuple[float, float, str, str, int]:
    decision = str(plan.get("decision") or "")
    source_index = _to_int(plan.get("source_decision_event_index")) or 0
    entry_underlying = _to_float(plan.get("underlying_close_reference")) or 0.0
    stop_loss_points = max(_to_float(plan.get("stop_loss_points")) or 0.0, 0.0)
    target_points = max(_to_float(plan.get("target_points")) or 0.0, 0.0)
    max_holding_bars = max(_to_int(plan.get("max_holding_bars")) or 1, 1)

    future_events = _future_decision_events(
        source_index=source_index,
        decision_events=decision_events,
        max_holding_bars=max_holding_bars,
    )

    if not future_events:
        return (
            entry_underlying,
            default_option_price_reference,
            "same_bar_exit_no_future_decision_event",
            str(plan.get("timestamp") or ""),
            0,
        )

    last_close = entry_underlying
    last_timestamp = str(plan.get("timestamp") or "")
    last_holding_bars = 0

    for holding_bars, event in enumerate(future_events, start=1):
        close = _to_float(event.get("close"))
        if close is None:
            continue

        timestamp = str(event.get("timestamp") or last_timestamp)
        move = _option_move_for_plan(
            decision=decision,
            entry_underlying=entry_underlying,
            current_underlying=close,
        )

        last_close = close
        last_timestamp = timestamp
        last_holding_bars = holding_bars

        if target_points and move >= target_points:
            return (
                close,
                default_option_price_reference + target_points,
                "target_points_reached",
                timestamp,
                holding_bars,
            )

        if stop_loss_points and move <= -stop_loss_points:
            return (
                close,
                max(default_option_price_reference - stop_loss_points, 0.0),
                "stop_loss_points_reached",
                timestamp,
                holding_bars,
            )

    final_move = _option_move_for_plan(
        decision=decision,
        entry_underlying=entry_underlying,
        current_underlying=last_close,
    )
    exit_option_price = max(default_option_price_reference + final_move, 0.0)

    return (
        last_close,
        exit_option_price,
        "max_holding_bars_reached",
        last_timestamp,
        last_holding_bars,
    )


def _lifecycle_for_plan(
    *,
    index: int,
    plan: Mapping[str, Any],
    decision_events: Mapping[int, Mapping[str, Any]],
    default_option_price_reference: float,
) -> PaperFillExitLifecycle:
    entry_underlying = _to_float(plan.get("underlying_close_reference"))
    if entry_underlying is None:
        raise ValueError("Paper fill lifecycle requires underlying close reference.")

    exit_underlying, exit_option_price, exit_reason, exit_timestamp, holding_bars = _simulate_exit(
        plan=plan,
        decision_events=decision_events,
        default_option_price_reference=default_option_price_reference,
    )

    return PaperFillExitLifecycle(
        paper_fill_exit_index=index,
        event_type="paper_option_fill_exit_lifecycle_created",
        paper_fill_exit_id=f"PAPER-FILL-EXIT-{index:06d}",
        source_paper_trade_plan_id=str(plan.get("paper_trade_plan_id") or ""),
        source_paper_trade_plan_index=_to_int(plan.get("paper_trade_plan_index")),
        source_decision_event_index=_to_int(plan.get("source_decision_event_index")),
        underlying_symbol=str(plan.get("underlying_symbol") or "NIFTY"),
        decision=str(plan.get("decision") or ""),
        option_type=str(plan.get("option_type") or ""),
        option_action="BUY",
        entry_timestamp=str(plan.get("timestamp") or ""),
        exit_timestamp=exit_timestamp,
        entry_underlying_close_reference=entry_underlying,
        exit_underlying_close_reference=exit_underlying,
        entry_option_price_reference=max(default_option_price_reference, 0.0),
        exit_option_price_reference=exit_option_price,
        option_points_result=exit_option_price - max(default_option_price_reference, 0.0),
        exit_reason=exit_reason,
        holding_bars=holding_bars,
        quantity_lots=max(_to_int(plan.get("quantity_lots")) or 1, 1),
        lot_size=max(_to_int(plan.get("lot_size")) or 1, 1),
        stop_loss_points=max(_to_float(plan.get("stop_loss_points")) or 0.0, 0.0),
        target_points=max(_to_float(plan.get("target_points")) or 0.0, 0.0),
        lifecycle_mode="paper_fill_exit_lifecycle_only",
        fill_mode="paper_fills_simulated_from_recorded_replay_references",
        broker_execution_mode="broker_disabled",
        order_mode="orders_not_created",
        account_pnl_mode="account_pnl_not_calculated",
        output_mode="paper_fill_exit_manifest_only",
    )


def build_paper_fill_exit_report(
    *,
    trade_plan_report_path: Path,
    decision_audit_path: Path,
    output_dir: Path,
    min_lifecycles: int = 1,
    default_option_price_reference: float = 100.0,
    allow_warnings: bool = False,
    max_plans: int | None = None,
) -> PaperFillExitReport:
    min_lifecycles = max(min_lifecycles, 0)
    default_option_price_reference = max(float(default_option_price_reference), 0.0)

    issues: list[PaperFillExitIssue] = []

    trade_plan_report, trade_plan_load_issues = _load_json_object(
        trade_plan_report_path,
        "trade_plan_report_missing",
        "trade_plan_report_invalid_json",
    )
    decision_audit, decision_audit_load_issues = _load_json_object(
        decision_audit_path,
        "decision_audit_missing",
        "decision_audit_invalid_json",
    )

    issues.extend(trade_plan_load_issues)
    issues.extend(decision_audit_load_issues)
    issues.extend(_trade_plan_report_issues(trade_plan_report, allow_warnings=allow_warnings))
    issues.extend(_decision_audit_report_issues(decision_audit, allow_warnings=allow_warnings))

    plans, plan_load_issues = _paper_trade_plans(trade_plan_report)
    decision_events, decision_event_issues = _decision_events_by_index(decision_audit)

    issues.extend(plan_load_issues)
    issues.extend(decision_event_issues)

    if max_plans is not None:
        plans = plans[: max(max_plans, 0)]

    lifecycles: list[PaperFillExitLifecycle] = []
    rejected_plans = 0

    for plan in plans:
        plan_issues = _plan_issues(plan)
        if plan_issues:
            issues.extend(plan_issues)
            rejected_plans += 1
            continue

        lifecycle = _lifecycle_for_plan(
            index=len(lifecycles) + 1,
            plan=plan,
            decision_events=decision_events,
            default_option_price_reference=default_option_price_reference,
        )
        lifecycles.append(lifecycle)

    if len(lifecycles) < min_lifecycles:
        issues.append(
            _issue(
                "fail",
                "insufficient_paper_fill_exit_lifecycles",
                min_lifecycles - len(lifecycles),
                (
                    "Paper fill/exit lifecycle count below minimum. "
                    f"Required={min_lifecycles}, actual={len(lifecycles)}."
                ),
            )
        )

    if rejected_plans and not lifecycles:
        issues.append(
            _issue(
                "fail",
                "no_valid_paper_trade_plans",
                rejected_plans,
                "Paper trade plans existed, but none were valid for fill/exit simulation.",
            )
        )

    status = _status(issues)

    return PaperFillExitReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        trade_plan_report_path=str(trade_plan_report_path),
        decision_audit_path=str(decision_audit_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_backtest_ledger=status in {"pass", "warn"},
        min_lifecycles_required=min_lifecycles,
        paper_trade_plan_count=len(plans),
        paper_fill_exit_lifecycle_count=len(lifecycles),
        ce_lifecycle_count=sum(1 for lifecycle in lifecycles if lifecycle.option_type == "CE"),
        pe_lifecycle_count=sum(1 for lifecycle in lifecycles if lifecycle.option_type == "PE"),
        target_exit_count=sum(1 for lifecycle in lifecycles if lifecycle.exit_reason == "target_points_reached"),
        stop_loss_exit_count=sum(1 for lifecycle in lifecycles if lifecycle.exit_reason == "stop_loss_points_reached"),
        time_exit_count=sum(1 for lifecycle in lifecycles if lifecycle.exit_reason in {"max_holding_bars_reached", "same_bar_exit_no_future_decision_event"}),
        safety_notice=safety_notice(),
        issues=issues,
        paper_fill_exit_lifecycles=lifecycles,
    )


def write_paper_fill_exit_report(
    report: PaperFillExitReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    fill_exit_json = output_dir / "paper_fill_exit_simulator.json"
    lifecycles_jsonl = output_dir / "paper_fill_exit_lifecycles.jsonl"
    fill_exit_txt = output_dir / "paper_fill_exit_simulator.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["paper_fill_exit_lifecycles"] = [
        asdict(lifecycle) for lifecycle in report.paper_fill_exit_lifecycles
    ]

    fill_exit_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with lifecycles_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for lifecycle in report.paper_fill_exit_lifecycles:
            handle.write(json.dumps(asdict(lifecycle), sort_keys=True))
            handle.write("\n")

    lines = [
        "HQE Recorded Data Paper Fill and Exit Simulator",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future backtest ledger: {report.ready_for_future_backtest_ledger}",
        f"Paper trade plans: {report.paper_trade_plan_count}",
        f"Paper fill/exit lifecycles: {report.paper_fill_exit_lifecycle_count}",
        f"CE lifecycles: {report.ce_lifecycle_count}",
        f"PE lifecycles: {report.pe_lifecycle_count}",
        f"Target exits: {report.target_exit_count}",
        f"Stop-loss exits: {report.stop_loss_exit_count}",
        f"Time/same-bar exits: {report.time_exit_count}",
        "",
        "Safety mapping:",
        "- CE BUY paper lifecycle comes from LONG decisions.",
        "- PE BUY paper lifecycle comes from SHORT decisions.",
        "- Broker execution remains disabled.",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Paper fill/exit lifecycles are ready for future backtest ledger.")
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
            f"- {fill_exit_json}",
            f"- {lifecycles_jsonl}",
            f"- {fill_exit_txt}",
            f"- {manifest_json}",
            "",
            "This simulator does not connect to a broker or create orders.",
            "This simulator does not calculate account PnL.",
            "This report is not a profitability claim.",
        ]
    )
    fill_exit_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_fill_exit_simulator",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_backtest_ledger": report.ready_for_future_backtest_ledger,
        "paper_trade_plan_count": report.paper_trade_plan_count,
        "paper_fill_exit_lifecycle_count": report.paper_fill_exit_lifecycle_count,
        "ce_lifecycle_count": report.ce_lifecycle_count,
        "pe_lifecycle_count": report.pe_lifecycle_count,
        "target_exit_count": report.target_exit_count,
        "stop_loss_exit_count": report.stop_loss_exit_count,
        "time_exit_count": report.time_exit_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_fill_exit_simulator_json": str(fill_exit_json),
            "paper_fill_exit_lifecycles_jsonl": str(lifecycles_jsonl),
            "paper_fill_exit_simulator_txt": str(fill_exit_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_fill_exit_simulator_json": fill_exit_json,
        "paper_fill_exit_lifecycles_jsonl": lifecycles_jsonl,
        "paper_fill_exit_simulator_txt": fill_exit_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_fill_exit_report(
    *,
    trade_plan_report_path: Path,
    decision_audit_path: Path,
    output_dir: Path,
    min_lifecycles: int = 1,
    default_option_price_reference: float = 100.0,
    allow_warnings: bool = False,
    max_plans: int | None = None,
) -> tuple[PaperFillExitReport, dict[str, Path]]:
    report = build_paper_fill_exit_report(
        trade_plan_report_path=trade_plan_report_path,
        decision_audit_path=decision_audit_path,
        output_dir=output_dir,
        min_lifecycles=min_lifecycles,
        default_option_price_reference=default_option_price_reference,
        allow_warnings=allow_warnings,
        max_plans=max_plans,
    )
    outputs = write_paper_fill_exit_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper fill/exit lifecycles from CE/PE paper option trade plans."
    )
    parser.add_argument(
        "--trade-plan-report",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_option_trade_plan_simulator/"
            "paper_option_trade_plan_simulator.json"
        ),
    )
    parser.add_argument(
        "--decision-audit",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_decision_audit/"
            "strategy_decision_audit.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_paper_fill_exit_simulator",
    )
    parser.add_argument("--min-lifecycles", type=int, default=1)
    parser.add_argument("--default-option-price-reference", type=float, default=100.0)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-plans", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_paper_fill_exit_report(
        trade_plan_report_path=Path(args.trade_plan_report),
        decision_audit_path=Path(args.decision_audit),
        output_dir=Path(args.output_dir),
        min_lifecycles=args.min_lifecycles,
        default_option_price_reference=args.default_option_price_reference,
        allow_warnings=args.allow_warnings,
        max_plans=args.max_plans,
    )

    print("HQE recorded data paper fill and exit simulator completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Paper fill/exit lifecycles: "
        f"CE={report.ce_lifecycle_count}, PE={report.pe_lifecycle_count}, "
        f"total={report.paper_fill_exit_lifecycle_count}"
    )
    print(
        "Paper fill/exit simulator report: "
        f"{outputs['paper_fill_exit_simulator_txt']}"
    )
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
