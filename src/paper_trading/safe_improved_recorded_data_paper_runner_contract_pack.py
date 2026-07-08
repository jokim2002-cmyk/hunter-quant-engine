"""
Safe Improved Recorded-Data Paper Runner Contract Pack

Module KKKKK continues Phase 9 by creating the guarded paper-runner contract
for the next execution module.

This pack does not execute a backtest, optimize parameters, change strategy
logic, connect to a broker, request live market data, place real orders, use
real money, approve live trading, or claim profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


REPORT_TYPE = "safe_improved_recorded_data_paper_runner_contract_pack"

DEFAULT_EXECUTION_PLAN_INPUTS = (
    Path(
        "reports/paper_trading/safe_improved_recorded_data_paper_runner_execution_plan_pack/"
        "safe_improved_recorded_data_paper_runner_execution_plan_pack.json"
    ),
    Path(
        "reports/paper_trading/safe_improved_recorded_data_paper_runner_execution_plan_pack/"
        "manifest.json"
    ),
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/safe_improved_recorded_data_paper_runner_contract_pack"
)

SAFE_RUNNER_MODE = "contract_only"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Safe improved recorded-data paper runner contract only. This pack does not "
    "run a backtest, connect to brokers, request live market data, place real "
    "orders, use real money, approve live trading, or prove profitability."
)
NO_PROFITABILITY_CLAIM_NOTICE = (
    "This is not a profitability claim. Future runner results must remain "
    "paper/simulation evidence only."
)


@dataclass(frozen=True)
class ContractRule:
    """A locked rule the future guarded runner must obey."""

    rule_id: str
    category: str
    name: str
    requirement: str
    allowed_value: str
    blocked_value: str
    evidence_field: str
    status: str


@dataclass(frozen=True)
class ContractReport:
    """Serializable paper-runner contract evidence report."""

    report_type: str
    status: str
    generated_at_utc: str
    execution_plan_input_path: str
    execution_plan_found: bool
    execution_plan_status: str
    execution_plan_accepted_runner_contract: bool
    output_directory: str
    contract_rule_count: int
    locked_contract_rule_count: int
    accepted_for_future_guarded_paper_runner_execution: bool
    completed_total_after_module: int
    phase_9_pending_after_module: int
    runner_mode: str
    runner_execution_enabled: bool
    backtest_executed: bool
    optimization_executed: bool
    strategy_logic_changed: bool
    broker_execution_mode: str
    live_data_mode: str
    real_order_mode: str
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    safety_notice: str
    no_profitability_claim_notice: str
    issues: list[dict[str, Any]]
    contract_rules: list[ContractRule]


def _first_existing(paths: Sequence[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _load_json(path: Path, *, missing_code: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [
            {
                "code": missing_code,
                "severity": "warn",
                "message": f"Input report not found: {path}",
            }
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": f"{missing_code}_invalid_json",
                "severity": "fail",
                "message": str(exc),
            }
        ]

    if not isinstance(payload, dict):
        return None, [
            {
                "code": f"{missing_code}_not_object",
                "severity": "fail",
                "message": f"Input report is not a JSON object: {path}",
            }
        ]

    return payload, []


def _status(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "missing"
    return str(payload.get("status") or payload.get("report_status") or "unknown")


def _bool(payload: dict[str, Any] | None, key: str, *, default: bool = False) -> bool:
    if not payload:
        return default
    return bool(payload.get(key, default))


def _plan_accepts_contract(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    accepted_keys = (
        "accepted_for_future_guarded_runner_module",
        "accepted_for_future_guarded_paper_runner_execution",
        "accepted_for_future_runner_contract",
    )
    return any(bool(payload.get(key)) for key in accepted_keys)


def _unsafe_payload(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    unsafe_keys = (
        "ready_for_live_or_real_money",
        "profitability_claim_allowed",
        "runner_execution_enabled",
        "backtest_executed",
        "optimization_executed",
        "strategy_logic_changed",
        "broker_execution_enabled",
        "live_data_enabled",
        "real_order_enabled",
    )
    return any(bool(payload.get(key)) for key in unsafe_keys)


def _contract_rules() -> list[ContractRule]:
    return [
        ContractRule(
            "contract-01",
            "input",
            "Recorded dataset lock",
            "Future runner must read only the recorded NIFTY 5-minute CSV dataset.",
            "data/recorded/fyers_nifty_5min.csv",
            "live_market_feed",
            "dataset_path",
            "locked",
        ),
        ContractRule(
            "contract-02",
            "execution_boundary",
            "Paper-only execution boundary",
            "Future runner may create paper trade rows only; it must not place orders.",
            "paper_trade_plan_rows",
            "broker_order_payload",
            "paper_execution_mode",
            "locked",
        ),
        ContractRule(
            "contract-03",
            "direction_mapping",
            "Option-buy mapping",
            "Future runner must map LONG to CE BUY paper plan, SHORT to PE BUY paper plan, and NEUTRAL to no trade.",
            "LONG=CE_BUY_PAPER; SHORT=PE_BUY_PAPER; NEUTRAL=NO_TRADE",
            "option_selling_or_futures_execution",
            "direction_to_option_intent",
            "locked",
        ),
        ContractRule(
            "contract-04",
            "risk_boundary",
            "No real-money boundary",
            "Future runner output must keep ready_for_live_or_real_money false.",
            "ready_for_live_or_real_money=false",
            "ready_for_live_or_real_money=true",
            "ready_for_live_or_real_money",
            "locked",
        ),
        ContractRule(
            "contract-05",
            "reporting",
            "No-profitability-claim boundary",
            "Future runner report must label all totals as paper/simulation evidence only.",
            "profitability_claim_allowed=false",
            "profitability_claim_allowed=true",
            "profitability_claim_allowed",
            "locked",
        ),
        ContractRule(
            "contract-06",
            "output_schema",
            "Layered evidence outputs",
            "Future runner must emit JSON, text, CSV, and manifest evidence outputs.",
            "json_txt_csv_manifest",
            "console_only_output",
            "outputs",
            "locked",
        ),
    ]


def build_contract_report(
    *,
    execution_plan_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ContractReport:
    """Build the guarded runner contract report without executing any runner."""

    input_path = execution_plan_input_path or _first_existing(DEFAULT_EXECUTION_PLAN_INPUTS)
    payload, issues = _load_json(input_path, missing_code="execution_plan_input_missing")

    input_found = payload is not None
    input_status = _status(payload)
    input_accepted = _plan_accepts_contract(payload)

    if _unsafe_payload(payload):
        issues.append(
            {
                "code": "unsafe_execution_plan_input_boundary",
                "severity": "fail",
                "message": "Execution plan input allowed live/real money, runner execution, strategy change, optimization, backtest, or profitability claims.",
            }
        )

    if input_found and input_status != "pass":
        issues.append(
            {
                "code": "execution_plan_input_not_pass",
                "severity": "warn",
                "message": "Execution plan input exists but is not marked pass.",
            }
        )

    if input_found and not input_accepted:
        issues.append(
            {
                "code": "execution_plan_input_not_accepted",
                "severity": "warn",
                "message": "Execution plan input exists but is not explicitly accepted for future guarded runner work.",
            }
        )

    failures = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "fail" if failures else "pass"
    rules = _contract_rules()

    accepted = (
        status == "pass"
        and input_found
        and input_status == "pass"
        and input_accepted
        and len(rules) == sum(1 for rule in rules if rule.status == "locked")
    )

    return ContractReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        execution_plan_input_path=str(input_path),
        execution_plan_found=input_found,
        execution_plan_status=input_status,
        execution_plan_accepted_runner_contract=input_accepted,
        output_directory=str(output_dir),
        contract_rule_count=len(rules),
        locked_contract_rule_count=sum(1 for rule in rules if rule.status == "locked"),
        accepted_for_future_guarded_paper_runner_execution=accepted,
        completed_total_after_module=115,
        phase_9_pending_after_module=1,
        runner_mode=SAFE_RUNNER_MODE,
        runner_execution_enabled=False,
        backtest_executed=False,
        optimization_executed=False,
        strategy_logic_changed=False,
        broker_execution_mode=SAFE_BROKER_MODE,
        live_data_mode=SAFE_DATA_MODE,
        real_order_mode=SAFE_ORDER_MODE,
        ready_for_live_or_real_money=False,
        profitability_claim_allowed=False,
        safety_notice=SAFETY_NOTICE,
        no_profitability_claim_notice=NO_PROFITABILITY_CLAIM_NOTICE,
        issues=issues,
        contract_rules=rules,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_rules_csv(path: Path, rules: list[ContractRule]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "rule_id",
                "category",
                "name",
                "requirement",
                "allowed_value",
                "blocked_value",
                "evidence_field",
                "status",
            ],
        )
        writer.writeheader()
        for rule in rules:
            writer.writerow(asdict(rule))


def _text_report(report: ContractReport) -> str:
    lines = [
        "HQE Safe Improved Recorded-Data Paper Runner Contract Pack",
        "=" * 74,
        f"Status: {report.status}",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Execution plan input path: {report.execution_plan_input_path}",
        f"Execution plan found: {report.execution_plan_found}",
        f"Execution plan status: {report.execution_plan_status}",
        f"Execution plan accepted runner contract: {report.execution_plan_accepted_runner_contract}",
        (
            "Accepted for future guarded paper runner execution: "
            f"{report.accepted_for_future_guarded_paper_runner_execution}"
        ),
        f"Contract rules locked: {report.locked_contract_rule_count}/{report.contract_rule_count}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 9 pending after module: {report.phase_9_pending_after_module}",
        f"Runner mode: {report.runner_mode}",
        f"Runner execution enabled: {report.runner_execution_enabled}",
        f"Backtest executed: {report.backtest_executed}",
        f"Optimization executed: {report.optimization_executed}",
        f"Strategy logic changed: {report.strategy_logic_changed}",
        f"Broker execution mode: {report.broker_execution_mode}",
        f"Live data mode: {report.live_data_mode}",
        f"Real order mode: {report.real_order_mode}",
        f"Ready for live or real money: {report.ready_for_live_or_real_money}",
        f"Profitability claim allowed: {report.profitability_claim_allowed}",
        "",
        report.safety_notice,
        report.no_profitability_claim_notice,
        "",
        "Locked contract rules:",
    ]

    for rule in report.contract_rules:
        lines.extend(
            [
                "",
                f"- {rule.rule_id}: {rule.name}",
                f"  Category: {rule.category}",
                f"  Requirement: {rule.requirement}",
                f"  Allowed: {rule.allowed_value}",
                f"  Blocked: {rule.blocked_value}",
                f"  Evidence field: {rule.evidence_field}",
                f"  Status: {rule.status}",
            ]
        )

    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(
                f"- {issue.get('severity', 'unknown').upper()} {issue.get('code')}: {issue.get('message')}"
            )

    return "\n".join(lines) + "\n"


def write_contract_pack(report: ContractReport, output_dir: Path) -> dict[str, str]:
    """Write JSON, text, CSV, and manifest evidence files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    rules_csv = output_dir / "safe_improved_recorded_data_paper_runner_contract_rules.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_rules_csv(rules_csv, report.contract_rules)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "rules_csv": str(rules_csv),
        "manifest_json": str(manifest_json),
    }

    _write_json(
        manifest_json,
        {
            "report_type": REPORT_TYPE,
            "status": report.status,
            "generated_at_utc": report.generated_at_utc,
            "accepted_for_future_guarded_paper_runner_execution": report.accepted_for_future_guarded_paper_runner_execution,
            "completed_total_after_module": report.completed_total_after_module,
            "phase_9_pending_after_module": report.phase_9_pending_after_module,
            "runner_mode": report.runner_mode,
            "runner_execution_enabled": report.runner_execution_enabled,
            "backtest_executed": report.backtest_executed,
            "optimization_executed": report.optimization_executed,
            "strategy_logic_changed": report.strategy_logic_changed,
            "broker_execution_mode": report.broker_execution_mode,
            "live_data_mode": report.live_data_mode,
            "real_order_mode": report.real_order_mode,
            "ready_for_live_or_real_money": report.ready_for_live_or_real_money,
            "profitability_claim_allowed": report.profitability_claim_allowed,
            "outputs": outputs,
        },
    )

    return outputs


def build_and_write_contract_pack(
    *,
    execution_plan_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[ContractReport, dict[str, str]]:
    report = build_contract_report(
        execution_plan_input_path=execution_plan_input_path,
        output_dir=output_dir,
    )
    outputs = write_contract_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write the safe improved recorded-data paper runner contract pack."
    )
    parser.add_argument("--execution-plan-input", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_contract_pack(
        execution_plan_input_path=Path(args.execution_plan_input)
        if args.execution_plan_input
        else None,
        output_dir=Path(args.output_dir),
    )

    print("HQE safe improved recorded-data paper runner contract pack completed.")
    print(f"Status: {report.status}")
    print(f"Execution plan found: {report.execution_plan_found}")
    print(f"Execution plan accepted: {report.execution_plan_accepted_runner_contract}")
    print(
        "Accepted for future guarded paper runner execution: "
        f"{report.accepted_for_future_guarded_paper_runner_execution}"
    )
    print(f"Contract rules locked: {report.locked_contract_rule_count}/{report.contract_rule_count}")
    print(f"Runner execution enabled: {report.runner_execution_enabled}")
    print(f"Backtest executed: {report.backtest_executed}")
    print(f"Strategy logic changed: {report.strategy_logic_changed}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 9 pending after module: {report.phase_9_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print(SAFETY_NOTICE)
    print(NO_PROFITABILITY_CLAIM_NOTICE)

    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
