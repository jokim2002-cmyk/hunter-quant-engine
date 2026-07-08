"""
Safe Improved Recorded-Data Paper Rerun Runner Build Sprint Close Pack

Module HHHHH - paper/offline close only.

This pack closes Phase 8 by aggregating the safe runner scaffold and dry-run
validation evidence.

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
    "scaffold": Path(
        "reports/paper_trading/safe_improved_recorded_data_paper_rerun_runner_scaffold_pack/"
        "safe_improved_recorded_data_paper_rerun_runner_scaffold_pack.json"
    ),
    "dry_run_validation": Path(
        "reports/paper_trading/safe_improved_recorded_data_paper_rerun_runner_dry_run_validation_pack/"
        "safe_improved_recorded_data_paper_rerun_runner_dry_run_validation_pack.json"
    ),
}
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/safe_improved_recorded_data_paper_rerun_runner_build_sprint_close_pack"
)

REPORT_TYPE = "safe_improved_recorded_data_paper_rerun_runner_build_sprint_close_pack"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Safe improved recorded-data paper rerun runner build sprint close only. This "
    "pack does not run a backtest, connect to brokers, request live market data, "
    "place real orders, use real money, approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Phase close status, future runner readiness, "
    "win rate, expectancy, equity, and simulated total references remain paper/simulation "
    "evidence only."
)


@dataclass(frozen=True)
class Phase8InputStatus:
    id: str
    title: str
    path: str
    found: bool
    status: str
    accepted_flag_name: str
    accepted_flag_value: bool
    runner_execution_enabled: bool
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    backtest_executed: bool
    strategy_logic_changed: bool


@dataclass(frozen=True)
class Phase8CloseReport:
    report_type: str
    status: str
    generated_at_utc: str
    output_directory: str
    input_count: int
    found_input_count: int
    pass_input_count: int
    accepted_input_count: int
    missing_input_count: int
    runner_execution_enabled_input_count: int
    phase_8_complete: bool
    accepted_for_future_improved_paper_runner_execution_phase: bool
    completed_total_after_module: int
    phase_8_pending_after_module: int
    next_recommended_phase: str
    next_recommended_step: str
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
    inputs: list[Phase8InputStatus]


INPUT_TITLES = {
    "scaffold": "Safe improved recorded-data paper rerun runner scaffold",
    "dry_run_validation": "Safe improved recorded-data paper rerun runner dry-run validation",
}

ACCEPTED_FLAGS = {
    "scaffold": "accepted_for_future_runner_dry_run_pack",
    "dry_run_validation": "accepted_for_future_runner_close_pack",
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


def build_phase8_close_report(
    *,
    input_paths: dict[str, Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Phase8CloseReport:
    paths = input_paths or DEFAULT_INPUTS
    issues: list[dict[str, Any]] = []
    input_statuses: list[Phase8InputStatus] = []

    for input_id, path in paths.items():
        payload, payload_issues = _load_json(path, input_id=input_id)
        issues.extend(payload_issues)
        found = payload is not None
        accepted_flag = ACCEPTED_FLAGS.get(input_id, "accepted")
        input_statuses.append(
            Phase8InputStatus(
                id=input_id,
                title=INPUT_TITLES.get(input_id, input_id),
                path=str(path),
                found=found,
                status=_status_value(payload),
                accepted_flag_name=accepted_flag,
                accepted_flag_value=_bool_value(payload, accepted_flag),
                runner_execution_enabled=_bool_value(payload, "runner_execution_enabled"),
                ready_for_live_or_real_money=_bool_value(payload, "ready_for_live_or_real_money"),
                profitability_claim_allowed=_bool_value(payload, "profitability_claim_allowed"),
                backtest_executed=_bool_value(payload, "backtest_executed"),
                strategy_logic_changed=_bool_value(payload, "strategy_logic_changed"),
            )
        )

    found_count = sum(1 for item in input_statuses if item.found)
    pass_count = sum(1 for item in input_statuses if item.status == "pass")
    accepted_count = sum(1 for item in input_statuses if item.accepted_flag_value)
    missing_count = sum(1 for item in input_statuses if not item.found)
    runner_enabled_count = sum(1 for item in input_statuses if item.runner_execution_enabled)

    unsafe_inputs = [
        item
        for item in input_statuses
        if item.ready_for_live_or_real_money
        or item.profitability_claim_allowed
        or item.backtest_executed
        or item.strategy_logic_changed
        or item.runner_execution_enabled
    ]
    if unsafe_inputs:
        issues.append(
            {
                "code": "unsafe_input_boundary",
                "severity": "fail",
                "message": "One or more Phase 8 inputs allowed runner execution, live/real money, profit claim, backtest execution, or strategy logic change.",
            }
        )

    failed_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "pass" if not failed_issues else "fail"

    phase_complete = (
        status == "pass"
        and found_count == len(input_statuses)
        and pass_count == len(input_statuses)
        and accepted_count == len(input_statuses)
        and missing_count == 0
        and runner_enabled_count == 0
        and not unsafe_inputs
    )

    return Phase8CloseReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        output_directory=str(output_dir),
        input_count=len(input_statuses),
        found_input_count=found_count,
        pass_input_count=pass_count,
        accepted_input_count=accepted_count,
        missing_input_count=missing_count,
        runner_execution_enabled_input_count=runner_enabled_count,
        phase_8_complete=phase_complete,
        accepted_for_future_improved_paper_runner_execution_phase=phase_complete,
        completed_total_after_module=112,
        phase_8_pending_after_module=0 if phase_complete else 1,
        next_recommended_phase="Phase 9 - Safe improved recorded-data paper runner execution",
        next_recommended_step=(
            "Build a guarded paper-only runner execution module that uses recorded data only, "
            "keeps broker/live/real-order gates disabled, preserves layered comparison outputs, "
            "and labels all outputs as non-profitability paper evidence."
        ),
        backtest_executed=False,
        optimization_executed=False,
        strategy_logic_changed=False,
        broker_execution_mode=SAFE_BROKER_MODE,
        live_data_mode=SAFE_DATA_MODE,
        real_order_mode=SAFE_ORDER_MODE,
        ready_for_live_or_real_money=False,
        profitability_claim_allowed=False,
        safety_notice=SAFETY_NOTICE,
        no_profitability_claim_notice=NO_PROFIT_CLAIM,
        issues=issues,
        inputs=input_statuses,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, inputs: list[Phase8InputStatus]) -> None:
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
                "accepted_flag_name",
                "accepted_flag_value",
                "runner_execution_enabled",
                "ready_for_live_or_real_money",
                "profitability_claim_allowed",
                "backtest_executed",
                "strategy_logic_changed",
            ],
        )
        writer.writeheader()
        for item in inputs:
            writer.writerow(asdict(item))


def _text_report(report: Phase8CloseReport) -> str:
    lines = [
        "HQE Safe Improved Recorded-Data Paper Rerun Runner Build Sprint Close Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Input count: {report.input_count}",
        f"Found inputs: {report.found_input_count}",
        f"Pass inputs: {report.pass_input_count}",
        f"Accepted inputs: {report.accepted_input_count}",
        f"Missing inputs: {report.missing_input_count}",
        f"Runner execution enabled inputs: {report.runner_execution_enabled_input_count}",
        f"Phase 8 complete: {report.phase_8_complete}",
        (
            "Accepted for future improved paper runner execution phase: "
            f"{report.accepted_for_future_improved_paper_runner_execution_phase}"
        ),
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 8 pending after module: {report.phase_8_pending_after_module}",
        f"Next recommended phase: {report.next_recommended_phase}",
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
                f"  Accepted flag: {item.accepted_flag_name}={item.accepted_flag_value}",
                f"  Runner execution enabled: {item.runner_execution_enabled}",
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


def write_phase8_close_pack(
    report: Phase8CloseReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    inputs_csv = output_dir / "safe_improved_recorded_data_paper_rerun_runner_build_sprint_close_inputs.csv"
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
        "phase_8_complete": report.phase_8_complete,
        "accepted_for_future_improved_paper_runner_execution_phase": report.accepted_for_future_improved_paper_runner_execution_phase,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_8_pending_after_module": report.phase_8_pending_after_module,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
        "outputs": outputs,
    }
    _write_json(manifest_json, manifest_payload)
    return outputs


def build_and_write_phase8_close_pack(
    *,
    input_paths: dict[str, Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Phase8CloseReport, dict[str, str]]:
    report = build_phase8_close_report(
        input_paths=input_paths,
        output_dir=output_dir,
    )
    outputs = write_phase8_close_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safe improved recorded-data paper rerun runner build sprint close pack."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_phase8_close_pack(
        output_dir=Path(args.output_dir),
    )

    print("HQE safe improved recorded-data paper rerun runner build sprint close pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Phase 8 complete: {report.phase_8_complete}")
    print(f"Accepted for future improved paper runner execution phase: {report.accepted_for_future_improved_paper_runner_execution_phase}")
    print(f"Inputs found/pass/accepted: {report.found_input_count}/{report.pass_input_count}/{report.accepted_input_count}")
    print(f"Runner execution enabled inputs: {report.runner_execution_enabled_input_count}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 8 pending after module: {report.phase_8_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
