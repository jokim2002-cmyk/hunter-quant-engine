"""
Recorded data paper strategy replay plan scaffold.

Evidence-only planning scaffold for a future paper/simulation strategy replay.
It reads scenario readiness output, scenario manifest output, and strategy input
bars, then builds deterministic replay plans.

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
class PaperStrategyReplayPlanIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class PaperStrategyReplayScenarioPlan:
    scenario_id: str
    source_path: str
    source_type: str
    planned_bar_count: int
    first_timestamp: str | None
    last_timestamp: str | None
    strategy_execution_mode: str
    broker_execution_mode: str
    output_mode: str


@dataclass(frozen=True)
class PaperStrategyReplayPlanReport:
    generated_at_utc: str
    scenario_readiness_path: str
    scenario_manifest_path: str
    strategy_input_bars_path: str
    output_directory: str
    status: str
    ready_to_plan: bool
    min_scenarios_required: int
    min_bars_required: int
    scenario_count: int
    total_planned_bars: int
    safety_notice: str
    issues: list[PaperStrategyReplayPlanIssue]
    scenario_plans: list[PaperStrategyReplayScenarioPlan]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data paper strategy replay "
        "plan scaffold does not run strategies, create signals, create trade "
        "plans, connect to brokers, request live market data, place real orders, "
        "use real money, calculate PnL, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> PaperStrategyReplayPlanIssue:
    return PaperStrategyReplayPlanIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status_from_issues(issues: Sequence[PaperStrategyReplayPlanIssue]) -> str:
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


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _load_json_object(
    path: Path,
    *,
    missing_code: str,
    invalid_json_code: str,
    invalid_shape_code: str,
    missing_message: str,
) -> tuple[Mapping[str, Any] | None, list[PaperStrategyReplayPlanIssue]]:
    if not path.exists():
        return None, [_issue("fail", missing_code, 1, missing_message)]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                invalid_json_code,
                1,
                f"JSON file could not be parsed safely: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                invalid_shape_code,
                1,
                "JSON file must be an object.",
            )
        ]

    return payload, []


def _load_jsonl_objects(
    path: Path,
) -> tuple[list[Mapping[str, Any]], list[PaperStrategyReplayPlanIssue]]:
    if not path.exists():
        return [], [
            _issue(
                "fail",
                "strategy_input_bars_missing",
                1,
                "Strategy input bars JSONL does not exist.",
            )
        ]

    rows: list[Mapping[str, Any]] = []
    issues: list[PaperStrategyReplayPlanIssue] = []
    invalid_json_lines = 0
    invalid_shape_lines = 0

    with path.open("r", encoding="utf-8") as file_handle:
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

            rows.append(payload)

    if invalid_json_lines:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bars_invalid_jsonl",
                invalid_json_lines,
                f"{invalid_json_lines} strategy input bar lines are invalid JSON.",
            )
        )

    if invalid_shape_lines:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bars_invalid_shape",
                invalid_shape_lines,
                f"{invalid_shape_lines} strategy input bar lines are not JSON objects.",
            )
        )

    return rows, issues


def _safe_scenarios(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    scenarios = payload.get("scenarios", [])
    if not isinstance(scenarios, list):
        return []
    return [scenario for scenario in scenarios if isinstance(scenario, Mapping)]


def _forbidden_keys(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_PLAN_KEYS
    }


def _validate_readiness(
    readiness_payload: Mapping[str, Any] | None,
) -> tuple[bool, list[PaperStrategyReplayPlanIssue]]:
    if readiness_payload is None:
        return False, []

    status = str(readiness_payload.get("status") or "unknown").lower()
    ready = bool(readiness_payload.get("ready_for_future_paper_strategy_replay"))

    if status == "fail" or not ready:
        return False, [
            _issue(
                "fail",
                "scenario_readiness_not_ready",
                1,
                "Scenario readiness gate is not ready for future paper strategy replay.",
            )
        ]

    if status == "warn":
        return True, [
            _issue(
                "warn",
                "scenario_readiness_warn",
                1,
                "Scenario readiness gate has warning status.",
            )
        ]

    if status == "pass":
        return True, []

    return False, [
        _issue(
            "fail",
            "scenario_readiness_unknown_status",
            1,
            f"Scenario readiness gate status is unknown: {status}.",
        )
    ]


def _manifest_status_issues(
    manifest_payload: Mapping[str, Any] | None,
) -> list[PaperStrategyReplayPlanIssue]:
    if manifest_payload is None:
        return []

    status = str(manifest_payload.get("status") or "unknown").lower()
    if status == "pass":
        return []
    if status == "warn":
        return [
            _issue(
                "warn",
                "scenario_manifest_warn",
                1,
                "Scenario manifest has warning status.",
            )
        ]
    if status == "fail":
        return [
            _issue(
                "fail",
                "scenario_manifest_failed",
                1,
                "Scenario manifest status is fail.",
            )
        ]
    return [
        _issue(
            "fail",
            "scenario_manifest_unknown_status",
            1,
            f"Scenario manifest status is unknown: {status}.",
        )
    ]


def _bars_by_source(
    bars: Sequence[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for bar in bars:
        source_path = str(bar.get("source_path") or "unknown_source")
        grouped.setdefault(source_path, []).append(bar)
    return grouped


def _scenario_plan_from_manifest(
    scenario: Mapping[str, Any],
    bars_for_source: Sequence[Mapping[str, Any]],
) -> PaperStrategyReplayScenarioPlan:
    bar_count = _as_int(scenario.get("bar_count")) or len(bars_for_source)

    return PaperStrategyReplayScenarioPlan(
        scenario_id=str(scenario.get("scenario_id") or ""),
        source_path=str(scenario.get("source_path") or ""),
        source_type=str(scenario.get("source_type") or ""),
        planned_bar_count=bar_count,
        first_timestamp=_as_text(scenario.get("first_timestamp")),
        last_timestamp=_as_text(scenario.get("last_timestamp")),
        strategy_execution_mode="not_executed_planning_only",
        broker_execution_mode="broker_disabled",
        output_mode="plan_manifest_only",
    )


def build_paper_strategy_replay_plan_report(
    *,
    scenario_readiness_path: Path,
    scenario_manifest_path: Path,
    strategy_input_bars_path: Path,
    output_dir: Path,
    min_scenarios: int = 1,
    min_bars: int = 1,
    allow_warnings: bool = False,
) -> PaperStrategyReplayPlanReport:
    normalized_min_scenarios = max(min_scenarios, 0)
    normalized_min_bars = max(min_bars, 0)
    issues: list[PaperStrategyReplayPlanIssue] = []

    readiness_payload, readiness_issues = _load_json_object(
        scenario_readiness_path,
        missing_code="scenario_readiness_missing",
        invalid_json_code="scenario_readiness_invalid_json",
        invalid_shape_code="scenario_readiness_invalid_shape",
        missing_message="Scenario readiness report does not exist.",
    )
    issues.extend(readiness_issues)

    manifest_payload, manifest_issues = _load_json_object(
        scenario_manifest_path,
        missing_code="scenario_manifest_missing",
        invalid_json_code="scenario_manifest_invalid_json",
        invalid_shape_code="scenario_manifest_invalid_shape",
        missing_message="Scenario manifest JSON does not exist.",
    )
    issues.extend(manifest_issues)

    bars, bar_issues = _load_jsonl_objects(strategy_input_bars_path)
    issues.extend(bar_issues)

    ready_to_plan, readiness_plan_issues = _validate_readiness(readiness_payload)
    issues.extend(readiness_plan_issues)
    issues.extend(_manifest_status_issues(manifest_payload))

    for payload, code in [
        (readiness_payload, "forbidden_readiness_fields"),
        (manifest_payload, "forbidden_manifest_fields"),
    ]:
        if payload is None:
            continue
        forbidden = _forbidden_keys(payload)
        if forbidden:
            issues.append(
                _issue(
                    "fail",
                    code,
                    len(forbidden),
                    "Payload contains forbidden execution/trading/profit fields.",
                )
            )

    scenarios = _safe_scenarios(manifest_payload) if manifest_payload is not None else []
    grouped_bars = _bars_by_source(bars)
    scenario_plans: list[PaperStrategyReplayScenarioPlan] = []

    if len(scenarios) < normalized_min_scenarios:
        issues.append(
            _issue(
                "fail",
                "insufficient_scenarios",
                normalized_min_scenarios - len(scenarios),
                (
                    "Scenario count is below the configured replay-plan minimum. "
                    f"Required={normalized_min_scenarios}, actual={len(scenarios)}."
                ),
            )
        )

    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id") or "unknown_scenario")
        source_path = str(scenario.get("source_path") or "")
        source_bars = grouped_bars.get(source_path, [])
        bar_count = _as_int(scenario.get("bar_count")) or 0

        if bar_count < normalized_min_bars:
            issues.append(
                _issue(
                    "fail",
                    "scenario_below_min_bars",
                    1,
                    (
                        "Scenario has fewer bars than required by replay-plan rules. "
                        f"Scenario={scenario_id}, bars={bar_count}, "
                        f"required={normalized_min_bars}."
                    ),
                )
            )
            continue

        if not source_bars:
            issues.append(
                _issue(
                    "fail",
                    "scenario_missing_source_bars",
                    1,
                    f"No strategy input bars found for scenario source: {source_path}.",
                )
            )
            continue

        scenario_plans.append(_scenario_plan_from_manifest(scenario, source_bars))

    if ready_to_plan and scenarios and not scenario_plans:
        issues.append(
            _issue(
                "fail",
                "no_replay_plans_created",
                1,
                "Scenario inputs existed, but no replay plans could be created.",
            )
        )

    if not allow_warnings and any(issue.severity == "warn" for issue in issues):
        issues.append(
            _issue(
                "fail",
                "warnings_not_allowed",
                1,
                "Replay-plan warnings are not allowed by default.",
            )
        )

    total_planned_bars = sum(plan.planned_bar_count for plan in scenario_plans)
    status = _status_from_issues(issues)

    return PaperStrategyReplayPlanReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        scenario_readiness_path=str(scenario_readiness_path),
        scenario_manifest_path=str(scenario_manifest_path),
        strategy_input_bars_path=str(strategy_input_bars_path),
        output_directory=str(output_dir),
        status=status,
        ready_to_plan=status in {"pass", "warn"},
        min_scenarios_required=normalized_min_scenarios,
        min_bars_required=normalized_min_bars,
        scenario_count=len(scenario_plans),
        total_planned_bars=total_planned_bars,
        safety_notice=safety_notice(),
        issues=issues,
        scenario_plans=scenario_plans,
    )


def write_paper_strategy_replay_plan_report(
    report: PaperStrategyReplayPlanReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_json = output_dir / "paper_strategy_replay_plan.json"
    plans_jsonl = output_dir / "paper_strategy_replay_plans.jsonl"
    plan_txt = output_dir / "paper_strategy_replay_plan.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["issues"] = [asdict(issue) for issue in report.issues]
    report_data["scenario_plans"] = [asdict(plan) for plan in report.scenario_plans]

    plan_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with plans_jsonl.open("w", encoding="utf-8", newline="\n") as file_handle:
        for plan in report.scenario_plans:
            file_handle.write(json.dumps(asdict(plan), sort_keys=True))
            file_handle.write("\n")

    lines = [
        "HQE Recorded Data Paper Strategy Replay Plan",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Scenario readiness path: {report.scenario_readiness_path}",
        f"Scenario manifest path: {report.scenario_manifest_path}",
        f"Strategy input bars path: {report.strategy_input_bars_path}",
        f"Status: {report.status}",
        f"Ready to plan future paper strategy replay: {report.ready_to_plan}",
        f"Minimum scenarios required: {report.min_scenarios_required}",
        f"Minimum bars required: {report.min_bars_required}",
        f"Scenario plans: {report.scenario_count}",
        f"Total planned bars: {report.total_planned_bars}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Scenario readiness and input bars satisfy this no-execution plan scaffold.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: "
                f"{issue.message} Count={issue.count}"
            )

    lines.append("")
    lines.append("Scenario Plans:")
    if not report.scenario_plans:
        lines.append("- No accepted replay plans.")
    else:
        for plan in report.scenario_plans:
            lines.append(
                f"- {plan.scenario_id}: bars={plan.planned_bar_count}, "
                f"source={plan.source_path}, mode={plan.strategy_execution_mode}"
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
            "This plan does not run strategy logic, create signals, calculate PnL, or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    plan_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_replay_plan",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_to_plan": report.ready_to_plan,
        "min_scenarios_required": report.min_scenarios_required,
        "min_bars_required": report.min_bars_required,
        "scenario_count": report.scenario_count,
        "total_planned_bars": report.total_planned_bars,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_replay_plan_json": str(plan_json),
            "paper_strategy_replay_plans_jsonl": str(plans_jsonl),
            "paper_strategy_replay_plan_txt": str(plan_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_replay_plan_json": plan_json,
        "paper_strategy_replay_plans_jsonl": plans_jsonl,
        "paper_strategy_replay_plan_txt": plan_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_paper_strategy_replay_plan_report(
    *,
    scenario_readiness_path: Path,
    scenario_manifest_path: Path,
    strategy_input_bars_path: Path,
    output_dir: Path,
    min_scenarios: int = 1,
    min_bars: int = 1,
    allow_warnings: bool = False,
) -> tuple[PaperStrategyReplayPlanReport, dict[str, Path]]:
    report = build_paper_strategy_replay_plan_report(
        scenario_readiness_path=scenario_readiness_path,
        scenario_manifest_path=scenario_manifest_path,
        strategy_input_bars_path=strategy_input_bars_path,
        output_dir=output_dir,
        min_scenarios=min_scenarios,
        min_bars=min_bars,
        allow_warnings=allow_warnings,
    )
    outputs = write_paper_strategy_replay_plan_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a no-execution paper strategy replay plan from recorded-data scenarios."
    )
    parser.add_argument(
        "--scenario-readiness",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_replay_scenario_readiness/"
            "scenario_readiness_report.json"
        ),
        help="Path to scenario readiness report JSON.",
    )
    parser.add_argument(
        "--scenario-manifest",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_replay_scenario/"
            "scenario_manifest.json"
        ),
        help="Path to scenario manifest JSON.",
    )
    parser.add_argument(
        "--strategy-input-bars",
        default=(
            "reports/paper_trading/"
            "recorded_data_strategy_input_contract/"
            "strategy_input_bars.jsonl"
        ),
        help="Path to strategy input bars JSONL.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_replay_plan",
        help="Directory where replay plan reports are written.",
    )
    parser.add_argument(
        "--min-scenarios",
        type=int,
        default=1,
        help="Minimum scenario plans required for pass status.",
    )
    parser.add_argument(
        "--min-bars",
        type=int,
        default=1,
        help="Minimum bars required per planned scenario.",
    )
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="Allow warning status to remain warning instead of failing the plan.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_paper_strategy_replay_plan_report(
        scenario_readiness_path=Path(args.scenario_readiness),
        scenario_manifest_path=Path(args.scenario_manifest),
        strategy_input_bars_path=Path(args.strategy_input_bars),
        output_dir=Path(args.output_dir),
        min_scenarios=args.min_scenarios,
        min_bars=args.min_bars,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data paper strategy replay plan completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready to plan future paper strategy replay: {report.ready_to_plan}")
    print(f"Scenario plans: {report.scenario_count}")
    print(f"Replay plan report: {outputs['paper_strategy_replay_plan_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
