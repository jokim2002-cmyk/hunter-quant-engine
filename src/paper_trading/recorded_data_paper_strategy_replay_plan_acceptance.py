"""
Recorded data paper strategy replay plan acceptance gate.

Evidence-only acceptance gate for the no-execution paper strategy replay plan.
It verifies that a replay plan is structurally acceptable before any future
paper/simulation strategy replay module is allowed to consume it.

This module never runs strategies, creates signals, creates trade plans,
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


FORBIDDEN_PLAN_KEYS = {
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
class ReplayPlanAcceptanceIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class ReplayPlanAcceptanceReport:
    generated_at_utc: str
    replay_plan_path: str
    output_directory: str
    status: str
    accepted: bool
    allow_warnings: bool
    min_scenario_plans_required: int
    min_total_planned_bars_required: int
    plan_status: str
    ready_to_plan: bool
    scenario_count: int
    total_planned_bars: int
    safety_notice: str
    issues: list[ReplayPlanAcceptanceIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data paper strategy replay "
        "plan acceptance gate does not run strategies, create signals, create "
        "trade plans, connect to brokers, request live market data, place real "
        "orders, use real money, calculate PnL, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> ReplayPlanAcceptanceIssue:
    return ReplayPlanAcceptanceIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status_from_issues(issues: Sequence[ReplayPlanAcceptanceIssue]) -> str:
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


def _load_plan(
    replay_plan_path: Path,
) -> tuple[Mapping[str, Any] | None, list[ReplayPlanAcceptanceIssue]]:
    if not replay_plan_path.exists():
        return None, [
            _issue(
                "fail",
                "replay_plan_missing",
                1,
                "Paper strategy replay plan JSON does not exist. Run Module AA first.",
            )
        ]

    try:
        payload = json.loads(replay_plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "replay_plan_invalid_json",
                1,
                f"Paper strategy replay plan JSON could not be parsed safely: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "replay_plan_invalid_shape",
                1,
                "Paper strategy replay plan JSON must be an object.",
            )
        ]

    return payload, []


def _safe_scenario_plans(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    scenario_plans = payload.get("scenario_plans", [])
    if not isinstance(scenario_plans, list):
        return []
    return [plan for plan in scenario_plans if isinstance(plan, Mapping)]


def _forbidden_keys(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_PLAN_KEYS
    }


def _check_plan_status(
    payload: Mapping[str, Any],
    *,
    allow_warnings: bool,
) -> list[ReplayPlanAcceptanceIssue]:
    issues: list[ReplayPlanAcceptanceIssue] = []
    plan_status = str(payload.get("status") or "unknown").lower()
    ready_to_plan = bool(payload.get("ready_to_plan"))

    if plan_status == "fail":
        issues.append(
            _issue(
                "fail",
                "replay_plan_failed",
                1,
                "Paper strategy replay plan status is fail.",
            )
        )
    elif plan_status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "replay_plan_warn",
                1,
                "Paper strategy replay plan status is warn.",
            )
        )
    elif plan_status != "pass":
        issues.append(
            _issue(
                "fail",
                "replay_plan_unknown_status",
                1,
                f"Paper strategy replay plan status is unknown: {plan_status}.",
            )
        )

    if not ready_to_plan:
        issues.append(
            _issue(
                "fail",
                "replay_plan_not_ready",
                1,
                "Paper strategy replay plan is not marked ready_to_plan.",
            )
        )

    return issues


def _check_scenario_plan_fields(
    scenario_plans: Sequence[Mapping[str, Any]],
) -> tuple[list[ReplayPlanAcceptanceIssue], int]:
    issues: list[ReplayPlanAcceptanceIssue] = []
    total_planned_bars = 0
    missing_required = 0
    wrong_modes = 0
    forbidden_count = 0
    zero_bar_count = 0

    for plan in scenario_plans:
        planned_bar_count = _as_int(plan.get("planned_bar_count")) or 0
        total_planned_bars += planned_bar_count

        required_values = [
            plan.get("scenario_id"),
            plan.get("source_path"),
            plan.get("first_timestamp"),
            plan.get("last_timestamp"),
        ]
        if any(value in (None, "") for value in required_values):
            missing_required += 1

        if planned_bar_count <= 0:
            zero_bar_count += 1

        strategy_mode = str(plan.get("strategy_execution_mode") or "").strip()
        broker_mode = str(plan.get("broker_execution_mode") or "").strip()
        output_mode = str(plan.get("output_mode") or "").strip()
        if (
            strategy_mode != "not_executed_planning_only"
            or broker_mode != "broker_disabled"
            or output_mode != "plan_manifest_only"
        ):
            wrong_modes += 1

        forbidden_count += len(_forbidden_keys(plan))

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "scenario_plan_missing_required_fields",
                missing_required,
                "One or more scenario plans are missing identity/source/timestamp fields.",
            )
        )

    if zero_bar_count:
        issues.append(
            _issue(
                "fail",
                "scenario_plan_zero_bars",
                zero_bar_count,
                "One or more scenario plans have zero planned bars.",
            )
        )

    if wrong_modes:
        issues.append(
            _issue(
                "fail",
                "scenario_plan_wrong_modes",
                wrong_modes,
                "One or more scenario plans are not no-execution/broker-disabled/manifest-only.",
            )
        )

    if forbidden_count:
        issues.append(
            _issue(
                "fail",
                "scenario_plan_forbidden_fields",
                forbidden_count,
                "Scenario plans contain forbidden execution/trading/profit fields.",
            )
        )

    return issues, total_planned_bars


def build_replay_plan_acceptance_report(
    *,
    replay_plan_path: Path,
    output_dir: Path,
    min_scenario_plans: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> ReplayPlanAcceptanceReport:
    normalized_min_plans = max(min_scenario_plans, 0)
    normalized_min_bars = max(min_total_planned_bars, 0)

    payload, issues = _load_plan(replay_plan_path)

    if payload is None:
        status = _status_from_issues(issues)
        return ReplayPlanAcceptanceReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            replay_plan_path=str(replay_plan_path),
            output_directory=str(output_dir),
            status=status,
            accepted=False,
            allow_warnings=allow_warnings,
            min_scenario_plans_required=normalized_min_plans,
            min_total_planned_bars_required=normalized_min_bars,
            plan_status="unknown",
            ready_to_plan=False,
            scenario_count=0,
            total_planned_bars=0,
            safety_notice=safety_notice(),
            issues=issues,
        )

    issues.extend(_check_plan_status(payload, allow_warnings=allow_warnings))

    forbidden_top_level = _forbidden_keys(payload)
    if forbidden_top_level:
        issues.append(
            _issue(
                "fail",
                "replay_plan_forbidden_fields",
                len(forbidden_top_level),
                "Replay plan payload contains forbidden execution/trading/profit fields.",
            )
        )

    scenario_plans = _safe_scenario_plans(payload)
    scenario_issues, total_planned_bars = _check_scenario_plan_fields(scenario_plans)
    issues.extend(scenario_issues)

    if len(scenario_plans) < normalized_min_plans:
        issues.append(
            _issue(
                "fail",
                "insufficient_scenario_plans",
                normalized_min_plans - len(scenario_plans),
                (
                    "Replay plan has fewer scenario plans than required. "
                    f"Required={normalized_min_plans}, actual={len(scenario_plans)}."
                ),
            )
        )

    if total_planned_bars < normalized_min_bars:
        issues.append(
            _issue(
                "fail",
                "insufficient_total_planned_bars",
                normalized_min_bars - total_planned_bars,
                (
                    "Replay plan has fewer total planned bars than required. "
                    f"Required={normalized_min_bars}, actual={total_planned_bars}."
                ),
            )
        )

    status = _status_from_issues(issues)
    accepted = status == "pass" or (status == "warn" and allow_warnings)

    return ReplayPlanAcceptanceReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        replay_plan_path=str(replay_plan_path),
        output_directory=str(output_dir),
        status=status,
        accepted=accepted,
        allow_warnings=allow_warnings,
        min_scenario_plans_required=normalized_min_plans,
        min_total_planned_bars_required=normalized_min_bars,
        plan_status=str(payload.get("status") or "unknown").lower(),
        ready_to_plan=bool(payload.get("ready_to_plan")),
        scenario_count=len(scenario_plans),
        total_planned_bars=total_planned_bars,
        safety_notice=safety_notice(),
        issues=issues,
    )


def write_replay_plan_acceptance_report(
    report: ReplayPlanAcceptanceReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    acceptance_json = output_dir / "paper_strategy_replay_plan_acceptance.json"
    acceptance_txt = output_dir / "paper_strategy_replay_plan_acceptance.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["issues"] = [asdict(issue) for issue in report.issues]

    acceptance_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Replay Plan Acceptance Gate",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Replay plan path: {report.replay_plan_path}",
        f"Status: {report.status}",
        f"Accepted for future paper strategy replay: {report.accepted}",
        f"Allow warnings: {report.allow_warnings}",
        f"Minimum scenario plans required: {report.min_scenario_plans_required}",
        f"Minimum total planned bars required: {report.min_total_planned_bars_required}",
        f"Plan status: {report.plan_status}",
        f"Ready to plan: {report.ready_to_plan}",
        f"Scenario plans: {report.scenario_count}",
        f"Total planned bars: {report.total_planned_bars}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Replay plan meets this no-execution acceptance scaffold.")
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
            "This gate only checks structural replay-plan readiness.",
            "This report is not a profitability claim.",
        ]
    )
    acceptance_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_replay_plan_acceptance",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted": report.accepted,
        "allow_warnings": report.allow_warnings,
        "min_scenario_plans_required": report.min_scenario_plans_required,
        "min_total_planned_bars_required": report.min_total_planned_bars_required,
        "scenario_count": report.scenario_count,
        "total_planned_bars": report.total_planned_bars,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_replay_plan_acceptance_json": str(acceptance_json),
            "paper_strategy_replay_plan_acceptance_txt": str(acceptance_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_replay_plan_acceptance_json": acceptance_json,
        "paper_strategy_replay_plan_acceptance_txt": acceptance_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_replay_plan_acceptance_report(
    *,
    replay_plan_path: Path,
    output_dir: Path,
    min_scenario_plans: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> tuple[ReplayPlanAcceptanceReport, dict[str, Path]]:
    report = build_replay_plan_acceptance_report(
        replay_plan_path=replay_plan_path,
        output_dir=output_dir,
        min_scenario_plans=min_scenario_plans,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )
    outputs = write_replay_plan_acceptance_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate a no-execution paper strategy replay plan."
    )
    parser.add_argument(
        "--replay-plan",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_replay_plan/"
            "paper_strategy_replay_plan.json"
        ),
        help="Path to paper strategy replay plan JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_replay_plan_acceptance"
        ),
        help="Directory where replay-plan acceptance reports are written.",
    )
    parser.add_argument(
        "--min-scenario-plans",
        type=int,
        default=1,
        help="Minimum scenario plans required for pass status.",
    )
    parser.add_argument(
        "--min-total-planned-bars",
        type=int,
        default=1,
        help="Minimum total planned bars required for pass status.",
    )
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="Allow warning status to be accepted.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_replay_plan_acceptance_report(
        replay_plan_path=Path(args.replay_plan),
        output_dir=Path(args.output_dir),
        min_scenario_plans=args.min_scenario_plans,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data paper strategy replay plan acceptance completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for future paper strategy replay: {report.accepted}")
    print(f"Scenario plans: {report.scenario_count}")
    print(f"Replay plan acceptance report: {outputs['paper_strategy_replay_plan_acceptance_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
