"""
Recorded data strategy decision acceptance gate.

Module WW in the fast-track v1.0 Testing Edition path.

This module validates LONG / SHORT / NEUTRAL strategy decision audit output
before future CE/PE paper trade-plan simulation.

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
    "trades",
}


@dataclass(frozen=True)
class StrategyDecisionAcceptanceIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class StrategyDecisionAcceptanceReport:
    generated_at_utc: str
    decision_audit_path: str
    output_directory: str
    status: str
    accepted_for_future_paper_trade_plan_simulator: bool
    min_decisions_required: int
    min_non_neutral_decisions_required: int
    decision_event_count: int
    long_count: int
    short_count: int
    neutral_count: int
    non_neutral_count: int
    safety_notice: str
    issues: list[StrategyDecisionAcceptanceIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation strategy decision acceptance gate only. LONG maps to "
        "future CE buy paper plan only, SHORT maps to future PE buy paper plan "
        "only, and NEUTRAL maps to no trade. This module does not create trade "
        "plans, connect to brokers, request live market data, place real orders, "
        "use real money, calculate PnL, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> StrategyDecisionAcceptanceIssue:
    return StrategyDecisionAcceptanceIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[StrategyDecisionAcceptanceIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


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


def _load_decision_audit(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[StrategyDecisionAcceptanceIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "decision_audit_missing",
                1,
                f"Strategy decision audit report missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "decision_audit_invalid_json",
                1,
                f"Strategy decision audit JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "decision_audit_invalid_shape",
                1,
                "Strategy decision audit report must be a JSON object.",
            )
        ]

    return payload, []


def _decision_audit_report_issues(
    payload: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[StrategyDecisionAcceptanceIssue]:
    if payload is None:
        return []

    issues: list[StrategyDecisionAcceptanceIssue] = []
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
                "Strategy decision audit report contains forbidden broker/order/trade/profit fields.",
            )
        )

    return issues


def _decision_events(
    payload: Mapping[str, Any] | None,
) -> tuple[list[Mapping[str, Any]], list[StrategyDecisionAcceptanceIssue]]:
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

    issues: list[StrategyDecisionAcceptanceIssue] = []
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


def _event_issues(event: Mapping[str, Any]) -> list[StrategyDecisionAcceptanceIssue]:
    issues: list[StrategyDecisionAcceptanceIssue] = []

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
                    (
                        "Decision event option-buy mapping is not aligned with "
                        "LONG=CE, SHORT=PE, NEUTRAL=no trade."
                    ),
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

    if event.get("timestamp") in (None, ""):
        issues.append(
            _issue(
                "fail",
                "decision_event_missing_timestamp",
                1,
                "Decision event must include timestamp.",
            )
        )

    forbidden = _forbidden(event)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "decision_event_forbidden_fields",
                len(forbidden),
                "Decision event contains forbidden broker/order/trade/profit fields.",
            )
        )

    return issues


def _count_report_mismatches(
    payload: Mapping[str, Any] | None,
    *,
    long_count: int,
    short_count: int,
    neutral_count: int,
    decision_event_count: int,
) -> list[StrategyDecisionAcceptanceIssue]:
    if payload is None:
        return []

    expected_counts = {
        "decision_event_count": decision_event_count,
        "long_count": long_count,
        "short_count": short_count,
        "neutral_count": neutral_count,
    }

    mismatches = 0
    for key, expected in expected_counts.items():
        actual = _to_int(payload.get(key))
        if actual is not None and actual != expected:
            mismatches += 1

    if not mismatches:
        return []

    return [
        _issue(
            "fail",
            "decision_audit_count_mismatch",
            mismatches,
            "Decision audit top-level counts do not match decision_events.",
        )
    ]


def build_strategy_decision_acceptance_report(
    *,
    decision_audit_path: Path,
    output_dir: Path,
    min_decisions: int = 1,
    min_non_neutral_decisions: int = 0,
    allow_warnings: bool = False,
) -> StrategyDecisionAcceptanceReport:
    min_decisions = max(min_decisions, 0)
    min_non_neutral_decisions = max(min_non_neutral_decisions, 0)

    issues: list[StrategyDecisionAcceptanceIssue] = []

    decision_audit, load_issues = _load_decision_audit(decision_audit_path)
    issues.extend(load_issues)
    issues.extend(
        _decision_audit_report_issues(
            decision_audit,
            allow_warnings=allow_warnings,
        )
    )

    decision_events, event_load_issues = _decision_events(decision_audit)
    issues.extend(event_load_issues)

    valid_decisions: list[str] = []
    for event in decision_events:
        event_issues = _event_issues(event)
        issues.extend(event_issues)
        decision = str(event.get("decision") or "")
        if decision in VALID_DECISIONS:
            valid_decisions.append(decision)

    long_count = sum(1 for decision in valid_decisions if decision == "LONG")
    short_count = sum(1 for decision in valid_decisions if decision == "SHORT")
    neutral_count = sum(1 for decision in valid_decisions if decision == "NEUTRAL")
    non_neutral_count = long_count + short_count

    issues.extend(
        _count_report_mismatches(
            decision_audit,
            long_count=long_count,
            short_count=short_count,
            neutral_count=neutral_count,
            decision_event_count=len(decision_events),
        )
    )

    if len(decision_events) < min_decisions:
        issues.append(
            _issue(
                "fail",
                "insufficient_strategy_decisions",
                min_decisions - len(decision_events),
                (
                    "Strategy decision event count below minimum. "
                    f"Required={min_decisions}, actual={len(decision_events)}."
                ),
            )
        )

    if non_neutral_count < min_non_neutral_decisions:
        issues.append(
            _issue(
                "fail",
                "insufficient_non_neutral_strategy_decisions",
                min_non_neutral_decisions - non_neutral_count,
                (
                    "Non-neutral strategy decision count below minimum. "
                    f"Required={min_non_neutral_decisions}, actual={non_neutral_count}."
                ),
            )
        )

    status = _status(issues)

    return StrategyDecisionAcceptanceReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        decision_audit_path=str(decision_audit_path),
        output_directory=str(output_dir),
        status=status,
        accepted_for_future_paper_trade_plan_simulator=status in {"pass", "warn"},
        min_decisions_required=min_decisions,
        min_non_neutral_decisions_required=min_non_neutral_decisions,
        decision_event_count=len(decision_events),
        long_count=long_count,
        short_count=short_count,
        neutral_count=neutral_count,
        non_neutral_count=non_neutral_count,
        safety_notice=safety_notice(),
        issues=issues,
    )


def write_strategy_decision_acceptance_report(
    report: StrategyDecisionAcceptanceReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    acceptance_json = output_dir / "strategy_decision_acceptance.json"
    acceptance_txt = output_dir / "strategy_decision_acceptance.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]

    acceptance_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Strategy Decision Acceptance Gate",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        (
            "Accepted for future paper trade-plan simulator: "
            f"{report.accepted_for_future_paper_trade_plan_simulator}"
        ),
        f"Decision events: {report.decision_event_count}",
        f"LONG count: {report.long_count}",
        f"SHORT count: {report.short_count}",
        f"NEUTRAL count: {report.neutral_count}",
        f"Non-neutral count: {report.non_neutral_count}",
        "",
        "Accepted mapping:",
        "- LONG = future CE buy paper plan only.",
        "- SHORT = future PE buy paper plan only.",
        "- NEUTRAL = no trade.",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Strategy decision audit accepted for future paper trade-plan simulator.")
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
            "This gate does not create CE/PE trade plans.",
            "This gate does not calculate PnL or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    acceptance_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_strategy_decision_acceptance",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted_for_future_paper_trade_plan_simulator": (
            report.accepted_for_future_paper_trade_plan_simulator
        ),
        "decision_event_count": report.decision_event_count,
        "long_count": report.long_count,
        "short_count": report.short_count,
        "neutral_count": report.neutral_count,
        "non_neutral_count": report.non_neutral_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "strategy_decision_acceptance_json": str(acceptance_json),
            "strategy_decision_acceptance_txt": str(acceptance_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "strategy_decision_acceptance_json": acceptance_json,
        "strategy_decision_acceptance_txt": acceptance_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_decision_acceptance_report(
    *,
    decision_audit_path: Path,
    output_dir: Path,
    min_decisions: int = 1,
    min_non_neutral_decisions: int = 0,
    allow_warnings: bool = False,
) -> tuple[StrategyDecisionAcceptanceReport, dict[str, Path]]:
    report = build_strategy_decision_acceptance_report(
        decision_audit_path=decision_audit_path,
        output_dir=output_dir,
        min_decisions=min_decisions,
        min_non_neutral_decisions=min_non_neutral_decisions,
        allow_warnings=allow_warnings,
    )
    outputs = write_strategy_decision_acceptance_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Accept LONG / SHORT / NEUTRAL strategy decision audit output."
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
        default="reports/paper_trading/recorded_data_strategy_decision_acceptance",
    )
    parser.add_argument("--min-decisions", type=int, default=1)
    parser.add_argument("--min-non-neutral-decisions", type=int, default=0)
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_strategy_decision_acceptance_report(
        decision_audit_path=Path(args.decision_audit),
        output_dir=Path(args.output_dir),
        min_decisions=args.min_decisions,
        min_non_neutral_decisions=args.min_non_neutral_decisions,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data strategy decision acceptance completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Accepted decisions: "
        f"LONG={report.long_count}, SHORT={report.short_count}, "
        f"NEUTRAL={report.neutral_count}"
    )
    print(
        "Strategy decision acceptance report: "
        f"{outputs['strategy_decision_acceptance_txt']}"
    )
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
