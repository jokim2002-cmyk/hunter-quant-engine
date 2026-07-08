"""
Paper Improvement Execution Sprint Close Pack

Module AAAAA - paper/offline only.

This pack closes the paper-only improvement execution sprint by aggregating the
paper improvement evidence from Modules VVVV through ZZZZ.

It does NOT change strategy logic, run a backtest, optimize parameters, connect
to brokers, request live data, place orders, use real money, approve live
trading, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


DEFAULT_INPUTS = {
    "pricing_reality": Path(
        "reports/paper_trading/paper_option_reference_pricing_reality_check_pack/"
        "paper_option_reference_pricing_reality_check_pack.json"
    ),
    "slippage_cost": Path(
        "reports/paper_trading/paper_slippage_and_cost_sensitivity_pack/"
        "paper_slippage_and_cost_sensitivity_pack.json"
    ),
    "exit_rule": Path(
        "reports/paper_trading/paper_exit_rule_sensitivity_review_pack/"
        "paper_exit_rule_sensitivity_review_pack.json"
    ),
    "cooldown_duplicate": Path(
        "reports/paper_trading/paper_signal_cooldown_duplicate_filter_review_pack/"
        "paper_signal_cooldown_duplicate_filter_review_pack.json"
    ),
    "session_frequency": Path(
        "reports/paper_trading/paper_session_trade_frequency_filter_review_pack/"
        "paper_session_trade_frequency_filter_review_pack.json"
    ),
}
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/paper_improvement_execution_sprint_close_pack"
)

REPORT_TYPE = "paper_improvement_execution_sprint_close_pack"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "live_data_disabled"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Paper/simulation improvement execution sprint close only. This pack does not "
    "connect to brokers, request live market data, place real orders, use real money, "
    "approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Pricing reality, slippage/cost, exit-rule, "
    "cooldown/duplicate, session/frequency, win rate, expectancy, equity, and "
    "simulated total references remain paper/simulation evidence only."
)


@dataclass(frozen=True)
class CloseInputStatus:
    id: str
    title: str
    path: str
    found: bool
    status: str
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    backtest_executed: bool
    strategy_logic_changed: bool


@dataclass(frozen=True)
class ImprovementExecutionCloseReport:
    report_type: str
    status: str
    generated_at_utc: str
    output_directory: str
    input_count: int
    found_input_count: int
    pass_input_count: int
    missing_input_count: int
    accepted_for_improved_paper_rerun_planning: bool
    phase_6_complete: bool
    completed_total_after_module: int
    phase_6_pending_after_module: int
    backtest_executed: bool
    optimization_executed: bool
    strategy_logic_changed: bool
    broker_execution_mode: str
    live_data_mode: str
    real_order_mode: str
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    next_recommended_step: str
    safety_notice: str
    no_profitability_claim_notice: str
    issues: list[dict[str, Any]]
    inputs: list[CloseInputStatus]


INPUT_TITLES = {
    "pricing_reality": "Option reference pricing reality check",
    "slippage_cost": "Slippage and cost sensitivity",
    "exit_rule": "Exit rule sensitivity review",
    "cooldown_duplicate": "Signal cooldown and duplicate filter review",
    "session_frequency": "Session and trade-frequency filter review",
}


def _load_json(path: Path, *, input_id: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [
            {
                "code": f"{input_id}_missing",
                "severity": "warn",
                "message": f"Input report not found: {path}",
            }
        ]

    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": f"{input_id}_invalid_json",
                "severity": "fail",
                "message": str(exc),
            }
        ]


def _bool_value(payload: dict[str, Any] | None, key: str, default: bool = False) -> bool:
    if not payload:
        return default
    return bool(payload.get(key, default))


def _status_value(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "missing"
    return str(payload.get("status") or "")


def build_improvement_execution_close_report(
    *,
    input_paths: dict[str, Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ImprovementExecutionCloseReport:
    paths = input_paths or DEFAULT_INPUTS
    issues: list[dict[str, Any]] = []
    input_statuses: list[CloseInputStatus] = []

    for input_id, path in paths.items():
        payload, payload_issues = _load_json(path, input_id=input_id)
        issues.extend(payload_issues)
        found = payload is not None
        status = _status_value(payload)
        input_statuses.append(
            CloseInputStatus(
                id=input_id,
                title=INPUT_TITLES.get(input_id, input_id),
                path=str(path),
                found=found,
                status=status,
                ready_for_live_or_real_money=_bool_value(payload, "ready_for_live_or_real_money"),
                profitability_claim_allowed=_bool_value(payload, "profitability_claim_allowed"),
                backtest_executed=_bool_value(payload, "backtest_executed"),
                strategy_logic_changed=_bool_value(payload, "strategy_logic_changed"),
            )
        )

    found_count = sum(1 for item in input_statuses if item.found)
    pass_count = sum(1 for item in input_statuses if item.status == "pass")
    missing_count = sum(1 for item in input_statuses if not item.found)
    unsafe_inputs = [
        item
        for item in input_statuses
        if item.ready_for_live_or_real_money
        or item.profitability_claim_allowed
        or item.strategy_logic_changed
    ]
    failed_issues = [issue for issue in issues if issue.get("severity") == "fail"]

    accepted = (
        missing_count == 0
        and len(unsafe_inputs) == 0
        and len(failed_issues) == 0
        and pass_count == len(input_statuses)
    )

    if unsafe_inputs:
        issues.append(
            {
                "code": "unsafe_input_boundary",
                "severity": "fail",
                "message": "One or more input reports allowed live/real money, profit claim, or strategy logic change.",
            }
        )

    status = "pass" if not failed_issues and not unsafe_inputs else "fail"

    return ImprovementExecutionCloseReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        output_directory=str(output_dir),
        input_count=len(input_statuses),
        found_input_count=found_count,
        pass_input_count=pass_count,
        missing_input_count=missing_count,
        accepted_for_improved_paper_rerun_planning=accepted,
        phase_6_complete=accepted,
        completed_total_after_module=105,
        phase_6_pending_after_module=0 if accepted else 1,
        backtest_executed=False,
        optimization_executed=False,
        strategy_logic_changed=False,
        broker_execution_mode=SAFE_BROKER_MODE,
        live_data_mode=SAFE_DATA_MODE,
        real_order_mode=SAFE_ORDER_MODE,
        ready_for_live_or_real_money=False,
        profitability_claim_allowed=False,
        next_recommended_step=(
            "Prepare an improved recorded-data paper rerun plan that compares baseline, "
            "pricing reality, slippage/cost, exit-rule, cooldown/duplicate, and "
            "session/frequency assumptions without claiming profitability."
        ),
        safety_notice=SAFETY_NOTICE,
        no_profitability_claim_notice=NO_PROFIT_CLAIM,
        issues=issues,
        inputs=input_statuses,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, inputs: list[CloseInputStatus]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "title",
                "path",
                "found",
                "status",
                "ready_for_live_or_real_money",
                "profitability_claim_allowed",
                "backtest_executed",
                "strategy_logic_changed",
            ],
        )
        writer.writeheader()
        for item in inputs:
            writer.writerow(asdict(item))


def _text_report(report: ImprovementExecutionCloseReport) -> str:
    lines = [
        "HQE Paper Improvement Execution Sprint Close Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Input count: {report.input_count}",
        f"Found inputs: {report.found_input_count}",
        f"Pass inputs: {report.pass_input_count}",
        f"Missing inputs: {report.missing_input_count}",
        (
            "Accepted for improved paper rerun planning: "
            f"{report.accepted_for_improved_paper_rerun_planning}"
        ),
        f"Phase 6 complete: {report.phase_6_complete}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 6 pending after module: {report.phase_6_pending_after_module}",
        f"Backtest executed: {report.backtest_executed}",
        f"Optimization executed: {report.optimization_executed}",
        f"Strategy logic changed: {report.strategy_logic_changed}",
        f"Broker mode: {report.broker_execution_mode}",
        f"Live data mode: {report.live_data_mode}",
        f"Ready for live/real money: {report.ready_for_live_or_real_money}",
        f"Profitability claim allowed: {report.profitability_claim_allowed}",
        "",
        report.safety_notice,
        report.no_profitability_claim_notice,
        "",
        "Inputs:",
    ]
    for item in report.inputs:
        lines.extend(
            [
                "",
                f"- {item.id}: {item.title}",
                f"  Found: {item.found}",
                f"  Status: {item.status}",
                f"  Path: {item.path}",
                f"  Ready for live/real money: {item.ready_for_live_or_real_money}",
                f"  Profitability claim allowed: {item.profitability_claim_allowed}",
                f"  Backtest executed: {item.backtest_executed}",
                f"  Strategy logic changed: {item.strategy_logic_changed}",
            ]
        )
    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")
    lines.extend(["", "Next recommended step:", report.next_recommended_step])
    return "\n".join(lines) + "\n"


def write_improvement_execution_close_pack(
    report: ImprovementExecutionCloseReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    inputs_csv = output_dir / "paper_improvement_execution_sprint_close_inputs.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_csv(inputs_csv, report.inputs)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "inputs_csv": str(inputs_csv),
        "manifest_json": str(manifest_json),
    }
    manifest_payload = {
        "report_type": REPORT_TYPE,
        "status": report.status,
        "generated_at_utc": report.generated_at_utc,
        "accepted_for_improved_paper_rerun_planning": report.accepted_for_improved_paper_rerun_planning,
        "phase_6_complete": report.phase_6_complete,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_6_pending_after_module": report.phase_6_pending_after_module,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
        "outputs": outputs,
    }
    _write_json(manifest_json, manifest_payload)
    return outputs


def build_and_write_improvement_execution_close_pack(
    *,
    input_paths: dict[str, Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[ImprovementExecutionCloseReport, dict[str, str]]:
    report = build_improvement_execution_close_report(
        input_paths=input_paths,
        output_dir=output_dir,
    )
    outputs = write_improvement_execution_close_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paper improvement execution sprint close pack."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_improvement_execution_close_pack(
        output_dir=Path(args.output_dir),
    )

    print("HQE paper improvement execution sprint close pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for improved paper rerun planning: {report.accepted_for_improved_paper_rerun_planning}")
    print(f"Phase 6 complete: {report.phase_6_complete}")
    print(f"Inputs found/pass: {report.found_input_count}/{report.pass_input_count}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 6 pending after module: {report.phase_6_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
