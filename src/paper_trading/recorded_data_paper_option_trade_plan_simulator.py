"""
Recorded data paper option trade-plan simulator.

Module XX in the fast-track v1.0 Testing Edition path.

This module converts accepted LONG / SHORT / NEUTRAL decision audit events into
paper-only option buy trade plans.

Safety mapping:
- LONG -> CE buy paper plan only.
- SHORT -> PE buy paper plan only.
- NEUTRAL -> no trade.

This module does not simulate fills, connect to brokers, request live market
data, place orders, use real money, calculate PnL, or prove profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


VALID_DECISIONS = {"LONG", "SHORT", "NEUTRAL"}

EXPECTED_DECISION_MODES = {
    "decision_mode": "smc_parameter_aligned_decision_audit_only",
    "execution_mode": "paper_backtest_decision_audit_only",
    "trade_plan_mode": "trade_plans_not_created",
    "broker_execution_mode": "broker_disabled",
    "output_mode": "decision_audit_manifest_only",
}

EXPECTED_OPTION_MAPPING = {
    "LONG": "future_CE_buy_paper_plan_only",
    "SHORT": "future_PE_buy_paper_plan_only",
    "NEUTRAL": "no_trade",
}

FORBIDDEN_KEYS = {
    "broker",
    "broker_order_id",
    "entry_fill",
    "exchange_order_id",
    "exit_fill",
    "fill",
    "fills",
    "live_data",
    "order",
    "order_id",
    "orders",
    "pnl",
    "position",
    "positions",
    "profit",
    "profit_loss",
    "real_money",
    "trade",
    "trades",
}


@dataclass(frozen=True)
class PaperOptionTradePlanIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperOptionTradePlan:
    paper_trade_plan_index: int
    event_type: str
    paper_trade_plan_id: str
    source_decision_event_index: int | None
    source_path: str
    source_type: str
    source_row_number: int | None
    timestamp: str
    decision: str
    option_type: str
    option_action: str
    option_buy_mapping: str
    underlying_symbol: str
    underlying_close_reference: float
    quantity_lots: int
    lot_size: int
    stop_loss_points: float
    target_points: float
    max_holding_bars: int
    plan_mode: str
    execution_mode: str
    fill_mode: str
    broker_execution_mode: str
    order_mode: str
    output_mode: str


@dataclass(frozen=True)
class PaperOptionTradePlanReport:
    generated_at_utc: str
    decision_acceptance_path: str
    decision_audit_path: str
    output_directory: str
    status: str
    ready_for_future_paper_fill_simulator: bool
    min_plans_required: int
    decision_event_count: int
    paper_trade_plan_count: int
    long_plan_count: int
    short_plan_count: int
    neutral_no_trade_count: int
    safety_notice: str
    issues: list[PaperOptionTradePlanIssue]
    paper_trade_plans: list[PaperOptionTradePlan]


def safety_notice() -> str:
    return (
        "Paper/simulation option trade-plan simulator only. LONG creates a CE "
        "buy paper plan, SHORT creates a PE buy paper plan, and NEUTRAL creates "
        "no trade. This module does not simulate fills, connect to brokers, "
        "request live market data, place real orders, use real money, calculate "
        "PnL, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> PaperOptionTradePlanIssue:
    return PaperOptionTradePlanIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[PaperOptionTradePlanIssue]) -> str:
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
) -> tuple[Mapping[str, Any] | None, list[PaperOptionTradePlanIssue]]:
    if not path.exists():
        return None, [_issue("fail", missing_code, 1, f"Required JSON file missing: {path}")]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [_issue("fail", invalid_code, 1, f"JSON parse failed: {exc}")]

    if not isinstance(payload, Mapping):
        return None, [_issue("fail", invalid_code, 1, "JSON payload must be an object.")]

    return payload, []


def _acceptance_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperOptionTradePlanIssue]:
    if payload is None:
        return []

    issues: list[PaperOptionTradePlanIssue] = []
    status = str(payload.get("status") or "unknown").lower()
    accepted = bool(payload.get("accepted_for_future_paper_trade_plan_simulator"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "decision_acceptance_warn",
                1,
                "Strategy decision acceptance status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "decision_acceptance_not_pass",
                1,
                f"Strategy decision acceptance status is not pass: {status}.",
            )
        )

    if not accepted:
        issues.append(
            _issue(
                "fail",
                "decision_acceptance_not_accepted",
                1,
                "Strategy decision acceptance did not accept output for future paper trade-plan simulator.",
            )
        )

    forbidden = _forbidden(payload)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "decision_acceptance_forbidden_fields",
                len(forbidden),
                "Decision acceptance contains forbidden broker/order/fill/trade/profit fields.",
            )
        )

    return issues


def _decision_audit_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[PaperOptionTradePlanIssue]:
    if payload is None:
        return []

    issues: list[PaperOptionTradePlanIssue] = []
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
                "Strategy decision audit is not ready for future paper trade-plan simulator.",
            )
        )

    forbidden = _forbidden(payload)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "decision_audit_forbidden_fields",
                len(forbidden),
                "Decision audit contains forbidden broker/order/fill/trade/profit fields.",
            )
        )

    return issues


def _decision_events(
    payload: Mapping[str, Any] | None,
) -> tuple[list[Mapping[str, Any]], list[PaperOptionTradePlanIssue]]:
    if payload is None:
        return [], []

    raw_events = payload.get("decision_events")
    if not isinstance(raw_events, list):
        return [], [
            _issue(
                "fail",
                "decision_events_missing",
                1,
                "Strategy decision audit report must include decision_events list.",
            )
        ]

    events: list[Mapping[str, Any]] = []
    invalid_shape = 0
    for event in raw_events:
        if isinstance(event, Mapping):
            events.append(event)
        else:
            invalid_shape += 1

    issues: list[PaperOptionTradePlanIssue] = []
    if invalid_shape:
        issues.append(
            _issue(
                "fail",
                "decision_events_invalid_shape",
                invalid_shape,
                f"{invalid_shape} decision events are not JSON objects.",
            )
        )

    return events, issues


def _decision_event_issues(event: Mapping[str, Any]) -> list[PaperOptionTradePlanIssue]:
    issues: list[PaperOptionTradePlanIssue] = []

    if str(event.get("event_type") or "") != "strategy_decision_audit":
        issues.append(
            _issue(
                "fail",
                "decision_event_wrong_type",
                1,
                "Decision event type must be strategy_decision_audit.",
            )
        )

    decision = str(event.get("decision") or "")
    if decision not in VALID_DECISIONS:
        issues.append(
            _issue(
                "fail",
                "decision_event_invalid_decision",
                1,
                "Decision must be LONG, SHORT, or NEUTRAL.",
            )
        )
    else:
        expected_mapping = EXPECTED_OPTION_MAPPING[decision]
        if str(event.get("option_buy_mapping") or "") != expected_mapping:
            issues.append(
                _issue(
                    "fail",
                    "decision_event_wrong_option_mapping",
                    1,
                    "Decision mapping must be LONG=CE, SHORT=PE, NEUTRAL=no trade.",
                )
            )

    wrong_modes = [
        key
        for key, expected in EXPECTED_DECISION_MODES.items()
        if str(event.get(key) or "") != expected
    ]
    if wrong_modes:
        issues.append(
            _issue(
                "fail",
                "decision_event_wrong_modes",
                len(wrong_modes),
                "Decision event has wrong safety/mode fields.",
            )
        )

    close = _to_float(event.get("close"))
    if event.get("timestamp") in (None, "") or close is None:
        issues.append(
            _issue(
                "fail",
                "decision_event_missing_required_fields",
                1,
                "Decision event must include timestamp and numeric close.",
            )
        )

    forbidden = _forbidden(event)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "decision_event_forbidden_fields",
                len(forbidden),
                "Decision event contains forbidden broker/order/fill/trade/profit fields.",
            )
        )

    return issues


def _plan_for_decision(
    *,
    plan_index: int,
    event: Mapping[str, Any],
    underlying_symbol: str,
    quantity_lots: int,
    lot_size: int,
    stop_loss_points: float,
    target_points: float,
    max_holding_bars: int,
) -> PaperOptionTradePlan | None:
    decision = str(event.get("decision") or "")
    if decision == "NEUTRAL":
        return None

    option_type = "CE" if decision == "LONG" else "PE"
    close = _to_float(event.get("close"))
    if close is None:
        raise ValueError("Paper option trade plan requires numeric close.")

    return PaperOptionTradePlan(
        paper_trade_plan_index=plan_index,
        event_type="paper_option_trade_plan_created",
        paper_trade_plan_id=f"PAPER-OPTION-PLAN-{plan_index:06d}",
        source_decision_event_index=_to_int(event.get("decision_event_index")),
        source_path=str(event.get("source_path") or ""),
        source_type=str(event.get("source_type") or ""),
        source_row_number=_to_int(event.get("source_row_number")),
        timestamp=str(event.get("timestamp") or ""),
        decision=decision,
        option_type=option_type,
        option_action="BUY",
        option_buy_mapping=EXPECTED_OPTION_MAPPING[decision],
        underlying_symbol=underlying_symbol,
        underlying_close_reference=close,
        quantity_lots=max(quantity_lots, 1),
        lot_size=max(lot_size, 1),
        stop_loss_points=max(float(stop_loss_points), 0.0),
        target_points=max(float(target_points), 0.0),
        max_holding_bars=max(max_holding_bars, 1),
        plan_mode="paper_option_buy_plan_only",
        execution_mode="paper_backtest_plan_only",
        fill_mode="fills_not_simulated",
        broker_execution_mode="broker_disabled",
        order_mode="orders_not_created",
        output_mode="paper_trade_plan_manifest_only",
    )


def build_paper_option_trade_plan_report(
    *,
    decision_acceptance_path: Path,
    decision_audit_path: Path,
    output_dir: Path,
    min_plans: int = 1,
    underlying_symbol: str = "NIFTY",
    quantity_lots: int = 1,
    lot_size: int = 50,
    stop_loss_points: float = 20.0,
    target_points: float = 40.0,
    max_holding_bars: int = 3,
    allow_warnings: bool = False,
    max_decisions: int | None = None,
) -> PaperOptionTradePlanReport:
    min_plans = max(min_plans, 0)

    issues: list[PaperOptionTradePlanIssue] = []

    acceptance, acceptance_load_issues = _load_json_object(
        decision_acceptance_path,
        "decision_acceptance_missing",
        "decision_acceptance_invalid_json",
    )
    decision_audit, decision_audit_load_issues = _load_json_object(
        decision_audit_path,
        "decision_audit_missing",
        "decision_audit_invalid_json",
    )

    issues.extend(acceptance_load_issues)
    issues.extend(decision_audit_load_issues)
    issues.extend(_acceptance_issues(acceptance, allow_warnings=allow_warnings))
    issues.extend(_decision_audit_issues(decision_audit, allow_warnings=allow_warnings))

    decision_events, event_load_issues = _decision_events(decision_audit)
    issues.extend(event_load_issues)

    if max_decisions is not None:
        decision_events = decision_events[: max(max_decisions, 0)]

    paper_trade_plans: list[PaperOptionTradePlan] = []
    neutral_no_trade_count = 0
    rejected_events = 0

    for event in decision_events:
        event_issues = _decision_event_issues(event)
        if event_issues:
            issues.extend(event_issues)
            rejected_events += 1
            continue

        if str(event.get("decision") or "") == "NEUTRAL":
            neutral_no_trade_count += 1
            continue

        plan = _plan_for_decision(
            plan_index=len(paper_trade_plans) + 1,
            event=event,
            underlying_symbol=underlying_symbol,
            quantity_lots=quantity_lots,
            lot_size=lot_size,
            stop_loss_points=stop_loss_points,
            target_points=target_points,
            max_holding_bars=max_holding_bars,
        )
        if plan is not None:
            paper_trade_plans.append(plan)

    if len(paper_trade_plans) < min_plans:
        issues.append(
            _issue(
                "fail",
                "insufficient_paper_option_trade_plans",
                min_plans - len(paper_trade_plans),
                (
                    "Paper option trade-plan count below minimum. "
                    f"Required={min_plans}, actual={len(paper_trade_plans)}."
                ),
            )
        )

    if rejected_events and not paper_trade_plans and neutral_no_trade_count == 0:
        issues.append(
            _issue(
                "fail",
                "no_valid_decision_events",
                rejected_events,
                "Decision events existed, but none were valid for paper option trade-plan simulation.",
            )
        )

    long_plan_count = sum(1 for plan in paper_trade_plans if plan.decision == "LONG")
    short_plan_count = sum(1 for plan in paper_trade_plans if plan.decision == "SHORT")
    status = _status(issues)

    return PaperOptionTradePlanReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        decision_acceptance_path=str(decision_acceptance_path),
        decision_audit_path=str(decision_audit_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_paper_fill_simulator=status in {"pass", "warn"},
        min_plans_required=min_plans,
        decision_event_count=len(decision_events),
        paper_trade_plan_count=len(paper_trade_plans),
        long_plan_count=long_plan_count,
        short_plan_count=short_plan_count,
        neutral_no_trade_count=neutral_no_trade_count,
        safety_notice=safety_notice(),
        issues=issues,
        paper_trade_plans=paper_trade_plans,
    )


def write_paper_option_trade_plan_report(
    report: PaperOptionTradePlanReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_json = output_dir / "paper_option_trade_plan_simulator.json"
    plans_jsonl = output_dir / "paper_option_trade_plans.jsonl"
    plan_txt = output_dir / "paper_option_trade_plan_simulator.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["paper_trade_plans"] = [asdict(plan) for plan in report.paper_trade_plans]

    plan_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with plans_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for plan in report.paper_trade_plans:
            handle.write(json.dumps(asdict(plan), sort_keys=True))
            handle.write("\n")

    lines = [
        "HQE Recorded Data Paper Option Trade-Plan Simulator",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future paper fill simulator: {report.ready_for_future_paper_fill_simulator}",
        f"Decision events: {report.decision_event_count}",
        f"Paper option trade plans: {report.paper_trade_plan_count}",
        f"LONG/CE plans: {report.long_plan_count}",
        f"SHORT/PE plans: {report.short_plan_count}",
        f"NEUTRAL no-trade decisions: {report.neutral_no_trade_count}",
        "",
        "Plan mapping:",
        "- LONG = CE BUY paper plan only.",
        "- SHORT = PE BUY paper plan only.",
        "- NEUTRAL = no trade.",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Paper option trade plans are ready for future fill simulator.")
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
            f"- {plan_json}",
            f"- {plans_jsonl}",
            f"- {plan_txt}",
            f"- {manifest_json}",
            "",
            "This simulator does not simulate fills.",
            "This simulator does not calculate PnL or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    plan_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_option_trade_plan_simulator",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_paper_fill_simulator": report.ready_for_future_paper_fill_simulator,
        "decision_event_count": report.decision_event_count,
        "paper_trade_plan_count": report.paper_trade_plan_count,
        "long_plan_count": report.long_plan_count,
        "short_plan_count": report.short_plan_count,
        "neutral_no_trade_count": report.neutral_no_trade_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_option_trade_plan_simulator_json": str(plan_json),
            "paper_option_trade_plans_jsonl": str(plans_jsonl),
            "paper_option_trade_plan_simulator_txt": str(plan_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_option_trade_plan_simulator_json": plan_json,
        "paper_option_trade_plans_jsonl": plans_jsonl,
        "paper_option_trade_plan_simulator_txt": plan_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_option_trade_plan_report(
    *,
    decision_acceptance_path: Path,
    decision_audit_path: Path,
    output_dir: Path,
    min_plans: int = 1,
    underlying_symbol: str = "NIFTY",
    quantity_lots: int = 1,
    lot_size: int = 50,
    stop_loss_points: float = 20.0,
    target_points: float = 40.0,
    max_holding_bars: int = 3,
    allow_warnings: bool = False,
    max_decisions: int | None = None,
) -> tuple[PaperOptionTradePlanReport, dict[str, Path]]:
    report = build_paper_option_trade_plan_report(
        decision_acceptance_path=decision_acceptance_path,
        decision_audit_path=decision_audit_path,
        output_dir=output_dir,
        min_plans=min_plans,
        underlying_symbol=underlying_symbol,
        quantity_lots=quantity_lots,
        lot_size=lot_size,
        stop_loss_points=stop_loss_points,
        target_points=target_points,
        max_holding_bars=max_holding_bars,
        allow_warnings=allow_warnings,
        max_decisions=max_decisions,
    )
    outputs = write_paper_option_trade_plan_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build CE/PE paper option buy trade plans from accepted strategy decisions."
    )
    parser.add_argument(
        "--decision-acceptance",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_decision_acceptance/"
            "strategy_decision_acceptance.json"
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
        default="reports/paper_trading/recorded_data_paper_option_trade_plan_simulator",
    )
    parser.add_argument("--min-plans", type=int, default=1)
    parser.add_argument("--underlying-symbol", default="NIFTY")
    parser.add_argument("--quantity-lots", type=int, default=1)
    parser.add_argument("--lot-size", type=int, default=50)
    parser.add_argument("--stop-loss-points", type=float, default=20.0)
    parser.add_argument("--target-points", type=float, default=40.0)
    parser.add_argument("--max-holding-bars", type=int, default=3)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--max-decisions", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_paper_option_trade_plan_report(
        decision_acceptance_path=Path(args.decision_acceptance),
        decision_audit_path=Path(args.decision_audit),
        output_dir=Path(args.output_dir),
        min_plans=args.min_plans,
        underlying_symbol=args.underlying_symbol,
        quantity_lots=args.quantity_lots,
        lot_size=args.lot_size,
        stop_loss_points=args.stop_loss_points,
        target_points=args.target_points,
        max_holding_bars=args.max_holding_bars,
        allow_warnings=args.allow_warnings,
        max_decisions=args.max_decisions,
    )

    print("HQE recorded data paper option trade-plan simulator completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Paper plans: "
        f"CE={report.long_plan_count}, PE={report.short_plan_count}, "
        f"NEUTRAL-no-trade={report.neutral_no_trade_count}"
    )
    print(
        "Paper option trade-plan simulator report: "
        f"{outputs['paper_option_trade_plan_simulator_txt']}"
    )
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
