"""
Recorded data paper strategy replay adapter contract.

This module converts an accepted no-execution paper strategy replay plan into
deterministic adapter requests for a future paper/simulation strategy adapter.

It never executes strategy logic, creates signals, creates trade plans, connects
to brokers, requests live market data, places orders, uses real money,
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
class AdapterContractIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class AdapterRequest:
    request_id: str
    scenario_id: str
    source_path: str
    source_type: str
    planned_bar_count: int
    first_timestamp: str | None
    last_timestamp: str | None
    adapter_mode: str
    strategy_execution_mode: str
    broker_execution_mode: str
    output_mode: str


@dataclass(frozen=True)
class AdapterContractReport:
    generated_at_utc: str
    plan_readiness_path: str
    replay_plan_path: str
    output_directory: str
    status: str
    ready_for_future_adapter: bool
    min_requests_required: int
    min_total_planned_bars_required: int
    request_count: int
    total_planned_bars: int
    safety_notice: str
    issues: list[AdapterContractIssue]
    adapter_requests: list[AdapterRequest]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter contract does not execute "
        "strategy logic, create signals, create trade plans, connect to brokers, "
        "request live market data, place real orders, use real money, calculate "
        "PnL, or prove profitability."
    )


def _issue(severity: str, code: str, count: int, message: str) -> AdapterContractIssue:
    return AdapterContractIssue(severity=severity, code=code, count=count, message=message)


def _status(issues: Sequence[AdapterContractIssue]) -> str:
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


def _load_json(path: Path, missing_code: str, invalid_code: str) -> tuple[Mapping[str, Any] | None, list[AdapterContractIssue]]:
    if not path.exists():
        return None, [_issue("fail", missing_code, 1, f"Required JSON file missing: {path}")]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [_issue("fail", invalid_code, 1, f"JSON parse failed: {exc}")]

    if not isinstance(payload, Mapping):
        return None, [_issue("fail", invalid_code, 1, "JSON payload must be an object.")]

    return payload, []


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _safe_plans(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    plans = payload.get("scenario_plans", [])
    if not isinstance(plans, list):
        return []
    return [plan for plan in plans if isinstance(plan, Mapping)]


def _readiness_issues(payload: Mapping[str, Any] | None, allow_warnings: bool) -> list[AdapterContractIssue]:
    if payload is None:
        return []

    issues: list[AdapterContractIssue] = []
    status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_paper_strategy_replay_plan"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "plan_readiness_warn",
                1,
                "Plan readiness status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "plan_readiness_not_pass",
                1,
                f"Plan readiness status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "plan_readiness_not_ready",
                1,
                "Plan readiness is not marked ready for future paper strategy replay plan.",
            )
        )

    return issues


def _plan_issues(payload: Mapping[str, Any] | None, allow_warnings: bool) -> list[AdapterContractIssue]:
    if payload is None:
        return []

    issues: list[AdapterContractIssue] = []
    status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_to_plan"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "replay_plan_warn",
                1,
                "Replay plan status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue("fail", "replay_plan_not_pass", 1, f"Replay plan status is not pass: {status}.")
        )

    if not ready:
        issues.append(_issue("fail", "replay_plan_not_ready", 1, "Replay plan is not ready_to_plan."))

    return issues


def _request_from_plan(index: int, plan: Mapping[str, Any]) -> AdapterRequest:
    return AdapterRequest(
        request_id=f"paper_strategy_adapter_request_{index:03d}",
        scenario_id=str(plan.get("scenario_id") or ""),
        source_path=str(plan.get("source_path") or ""),
        source_type=str(plan.get("source_type") or ""),
        planned_bar_count=_as_int(plan.get("planned_bar_count")) or 0,
        first_timestamp=plan.get("first_timestamp"),
        last_timestamp=plan.get("last_timestamp"),
        adapter_mode="contract_only_no_strategy_execution",
        strategy_execution_mode="not_executed_contract_only",
        broker_execution_mode="broker_disabled",
        output_mode="adapter_request_manifest_only",
    )


def build_adapter_contract_report(
    *,
    plan_readiness_path: Path,
    replay_plan_path: Path,
    output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> AdapterContractReport:
    issues: list[AdapterContractIssue] = []
    min_requests = max(min_requests, 0)
    min_total_planned_bars = max(min_total_planned_bars, 0)

    readiness, readiness_load_issues = _load_json(
        plan_readiness_path,
        "plan_readiness_missing",
        "plan_readiness_invalid_json",
    )
    plan, plan_load_issues = _load_json(
        replay_plan_path,
        "replay_plan_missing",
        "replay_plan_invalid_json",
    )
    issues.extend(readiness_load_issues)
    issues.extend(plan_load_issues)

    issues.extend(_readiness_issues(readiness, allow_warnings))
    issues.extend(_plan_issues(plan, allow_warnings))

    for payload, code in [(readiness, "forbidden_readiness_fields"), (plan, "forbidden_replay_plan_fields")]:
        if payload is None:
            continue
        bad = _forbidden(payload)
        if bad:
            issues.append(_issue("fail", code, len(bad), "Payload contains forbidden execution/trading/profit fields."))

    adapter_requests: list[AdapterRequest] = []
    plans = _safe_plans(plan) if plan is not None else []
    missing_fields = 0
    wrong_modes = 0
    forbidden_plan_fields = 0

    for index, scenario_plan in enumerate(plans, start=1):
        required = [
            scenario_plan.get("scenario_id"),
            scenario_plan.get("source_path"),
            scenario_plan.get("first_timestamp"),
            scenario_plan.get("last_timestamp"),
        ]
        if any(value in (None, "") for value in required):
            missing_fields += 1
            continue

        if (_as_int(scenario_plan.get("planned_bar_count")) or 0) <= 0:
            missing_fields += 1
            continue

        if (
            scenario_plan.get("strategy_execution_mode") != "not_executed_planning_only"
            or scenario_plan.get("broker_execution_mode") != "broker_disabled"
            or scenario_plan.get("output_mode") != "plan_manifest_only"
        ):
            wrong_modes += 1
            continue

        forbidden_plan_fields += len(_forbidden(scenario_plan))
        adapter_requests.append(_request_from_plan(index, scenario_plan))

    if missing_fields:
        issues.append(_issue("fail", "scenario_plan_missing_required_fields", missing_fields, "Scenario plans missing required adapter-contract fields."))

    if wrong_modes:
        issues.append(_issue("fail", "scenario_plan_wrong_modes", wrong_modes, "Scenario plans are not no-execution/broker-disabled/manifest-only."))

    if forbidden_plan_fields:
        issues.append(_issue("fail", "scenario_plan_forbidden_fields", forbidden_plan_fields, "Scenario plans contain forbidden execution/trading/profit fields."))

    total_planned_bars = sum(request.planned_bar_count for request in adapter_requests)

    if len(adapter_requests) < min_requests:
        issues.append(
            _issue(
                "fail",
                "insufficient_adapter_requests",
                min_requests - len(adapter_requests),
                f"Adapter request count below minimum. Required={min_requests}, actual={len(adapter_requests)}.",
            )
        )

    if total_planned_bars < min_total_planned_bars:
        issues.append(
            _issue(
                "fail",
                "insufficient_total_planned_bars",
                min_total_planned_bars - total_planned_bars,
                f"Total planned bars below minimum. Required={min_total_planned_bars}, actual={total_planned_bars}.",
            )
        )

    status = _status(issues)

    return AdapterContractReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        plan_readiness_path=str(plan_readiness_path),
        replay_plan_path=str(replay_plan_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_adapter=status in {"pass", "warn"},
        min_requests_required=min_requests,
        min_total_planned_bars_required=min_total_planned_bars,
        request_count=len(adapter_requests),
        total_planned_bars=total_planned_bars,
        safety_notice=safety_notice(),
        issues=issues,
        adapter_requests=adapter_requests,
    )


def write_adapter_contract_report(report: AdapterContractReport, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    contract_json = output_dir / "paper_strategy_adapter_contract.json"
    requests_jsonl = output_dir / "paper_strategy_adapter_requests.jsonl"
    contract_txt = output_dir / "paper_strategy_adapter_contract.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["adapter_requests"] = [asdict(request) for request in report.adapter_requests]

    contract_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with requests_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for request in report.adapter_requests:
            handle.write(json.dumps(asdict(request), sort_keys=True))
            handle.write("\n")

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Contract",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future adapter: {report.ready_for_future_adapter}",
        f"Adapter requests: {report.request_count}",
        f"Total planned bars: {report.total_planned_bars}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Adapter contract is structurally ready.")
    else:
        for issue in report.issues:
            lines.append(f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}")

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {contract_json}",
            f"- {requests_jsonl}",
            f"- {contract_txt}",
            f"- {manifest_json}",
            "",
            "This contract does not execute strategy logic, create signals, calculate PnL, or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    contract_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_adapter_contract",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_adapter": report.ready_for_future_adapter,
        "request_count": report.request_count,
        "total_planned_bars": report.total_planned_bars,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_contract_json": str(contract_json),
            "paper_strategy_adapter_requests_jsonl": str(requests_jsonl),
            "paper_strategy_adapter_contract_txt": str(contract_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "paper_strategy_adapter_contract_json": contract_json,
        "paper_strategy_adapter_requests_jsonl": requests_jsonl,
        "paper_strategy_adapter_contract_txt": contract_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_contract_report(
    *,
    plan_readiness_path: Path,
    replay_plan_path: Path,
    output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> tuple[AdapterContractReport, dict[str, Path]]:
    report = build_adapter_contract_report(
        plan_readiness_path=plan_readiness_path,
        replay_plan_path=replay_plan_path,
        output_dir=output_dir,
        min_requests=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )
    return report, write_adapter_contract_report(report, output_dir)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a no-execution paper strategy adapter contract.")
    parser.add_argument(
        "--plan-readiness",
        default="reports/paper_trading/recorded_data_paper_strategy_replay_plan_readiness/paper_strategy_replay_plan_readiness.json",
    )
    parser.add_argument(
        "--replay-plan",
        default="reports/paper_trading/recorded_data_paper_strategy_replay_plan/paper_strategy_replay_plan.json",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_paper_strategy_adapter_contract",
    )
    parser.add_argument("--min-requests", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_contract_report(
        plan_readiness_path=Path(args.plan_readiness),
        replay_plan_path=Path(args.replay_plan),
        output_dir=Path(args.output_dir),
        min_requests=args.min_requests,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data paper strategy adapter contract completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future adapter: {report.ready_for_future_adapter}")
    print(f"Adapter requests: {report.request_count}")
    print(f"Adapter contract report: {outputs['paper_strategy_adapter_contract_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
