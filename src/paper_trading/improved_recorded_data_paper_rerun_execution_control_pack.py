"""
Improved Recorded-Data Paper Rerun Execution Control Pack

Module DDDDD - paper/offline execution-control only.

This pack locks the control contract for a future improved recorded-data paper
rerun runner. It verifies the CCCCC preflight report and writes the runner gates,
comparison layers, output contract, and no-profit-claim boundaries.

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


DEFAULT_PREFLIGHT_INPUT = Path(
    "reports/paper_trading/improved_recorded_data_paper_rerun_preflight_pack/"
    "improved_recorded_data_paper_rerun_preflight_pack.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/improved_recorded_data_paper_rerun_execution_control_pack"
)

REPORT_TYPE = "improved_recorded_data_paper_rerun_execution_control_pack"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Improved recorded-data paper rerun execution control only. This pack does not "
    "run a backtest, connect to brokers, request live market data, place real orders, "
    "use real money, approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Future runner controls, comparison layers, "
    "output contracts, win rate, expectancy, equity, and simulated total references "
    "remain paper/simulation evidence only."
)


@dataclass(frozen=True)
class ExecutionControl:
    id: str
    title: str
    control_type: str
    requirement: str
    locked_value: str
    status: str


@dataclass(frozen=True)
class ExecutionControlReport:
    report_type: str
    status: str
    generated_at_utc: str
    preflight_input_path: str
    output_directory: str
    preflight_report_found: bool
    preflight_report_status: str
    preflight_accepts_future_runner: bool
    accepted_for_future_improved_paper_rerun: bool
    control_count: int
    locked_control_count: int
    completed_total_after_module: int
    phase_7_pending_after_module: int
    backtest_executed: bool
    optimization_executed: bool
    strategy_logic_changed: bool
    broker_execution_mode: str
    live_data_mode: str
    real_order_mode: str
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    runner_dataset_mode: str
    runner_order_mode: str
    runner_output_contract_locked: bool
    safety_notice: str
    no_profitability_claim_notice: str
    issues: list[dict[str, Any]]
    controls: list[ExecutionControl]


def _load_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [
            {
                "code": "preflight_input_missing",
                "severity": "warn",
                "message": f"Input report not found: {path}",
            }
        ]

    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": "preflight_input_invalid_json",
                "severity": "fail",
                "message": str(exc),
            }
        ]


def _payload_bool(payload: dict[str, Any] | None, key: str, default: bool = False) -> bool:
    if not payload:
        return default
    return bool(payload.get(key, default))


def _payload_status(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "missing"
    return str(payload.get("status") or "")


def _standard_controls() -> list[ExecutionControl]:
    return [
        ExecutionControl(
            "control-01",
            "Recorded-data-only runner mode",
            "dataset",
            "Future rerun runner must use local recorded data only.",
            "recorded_data_only",
            "locked",
        ),
        ExecutionControl(
            "control-02",
            "Broker and live data disabled",
            "safety",
            "Future runner must not connect to brokers or request live market data.",
            "broker_disabled; live_data_disabled",
            "locked",
        ),
        ExecutionControl(
            "control-03",
            "Paper option-buy interpretation",
            "trade_mapping",
            "LONG must map to CE BUY paper plan; SHORT must map to PE BUY paper plan; NEUTRAL must map to no trade.",
            "LONG=CE_BUY_PAPER; SHORT=PE_BUY_PAPER; NEUTRAL=NO_TRADE",
            "locked",
        ),
        ExecutionControl(
            "control-04",
            "Comparison layer contract",
            "comparison",
            "Future runner must compare baseline, pricing reality, slippage/cost, exit-rule, cooldown/duplicate, and session/frequency layers.",
            "baseline|pricing_reality|slippage_cost|exit_rule|cooldown_duplicate|session_frequency",
            "locked",
        ),
        ExecutionControl(
            "control-05",
            "Skipped-reason output contract",
            "output_schema",
            "Future runner must report skipped trade reasons and layer-specific reductions.",
            "raw_plans; guarded_plans; cooldown_filtered; session_filtered; skipped_reasons",
            "locked",
        ),
        ExecutionControl(
            "control-06",
            "No-profitability-claim output contract",
            "reporting",
            "Future runner must keep all results labeled paper/simulation reference only.",
            "profitability_claim_allowed=false; ready_for_live_or_real_money=false",
            "locked",
        ),
    ]


def build_execution_control_report(
    *,
    preflight_input_path: Path = DEFAULT_PREFLIGHT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ExecutionControlReport:
    preflight_payload, issues = _load_json(preflight_input_path)

    preflight_found = preflight_payload is not None
    preflight_status = _payload_status(preflight_payload)
    preflight_accepts = _payload_bool(
        preflight_payload,
        "accepted_for_future_improved_rerun_runner",
    )

    unsafe_preflight = (
        _payload_bool(preflight_payload, "ready_for_live_or_real_money")
        or _payload_bool(preflight_payload, "profitability_claim_allowed")
        or _payload_bool(preflight_payload, "strategy_logic_changed")
        or _payload_bool(preflight_payload, "backtest_executed")
    )
    if unsafe_preflight:
        issues.append(
            {
                "code": "unsafe_preflight_boundary",
                "severity": "fail",
                "message": "Preflight report allowed live/real money, profit claim, strategy change, or backtest execution.",
            }
        )

    if preflight_found and preflight_status != "pass":
        issues.append(
            {
                "code": "preflight_not_pass",
                "severity": "warn",
                "message": f"Preflight report status is {preflight_status}.",
            }
        )

    if preflight_found and not preflight_accepts:
        issues.append(
            {
                "code": "preflight_not_accepted_for_runner",
                "severity": "warn",
                "message": "Preflight report does not accept a future improved rerun runner.",
            }
        )

    failure_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "pass" if not failure_issues else "fail"

    accepted = (
        preflight_found
        and preflight_status == "pass"
        and preflight_accepts
        and not unsafe_preflight
        and not failure_issues
    )

    controls = _standard_controls()

    return ExecutionControlReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        preflight_input_path=str(preflight_input_path),
        output_directory=str(output_dir),
        preflight_report_found=preflight_found,
        preflight_report_status=preflight_status,
        preflight_accepts_future_runner=preflight_accepts,
        accepted_for_future_improved_paper_rerun=accepted,
        control_count=len(controls),
        locked_control_count=sum(1 for control in controls if control.status == "locked"),
        completed_total_after_module=108,
        phase_7_pending_after_module=1,
        backtest_executed=False,
        optimization_executed=False,
        strategy_logic_changed=False,
        broker_execution_mode=SAFE_BROKER_MODE,
        live_data_mode=SAFE_DATA_MODE,
        real_order_mode=SAFE_ORDER_MODE,
        ready_for_live_or_real_money=False,
        profitability_claim_allowed=False,
        runner_dataset_mode=SAFE_DATA_MODE,
        runner_order_mode=SAFE_ORDER_MODE,
        runner_output_contract_locked=True,
        safety_notice=SAFETY_NOTICE,
        no_profitability_claim_notice=NO_PROFIT_CLAIM,
        issues=issues,
        controls=controls,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, controls: list[ExecutionControl]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "title",
                "control_type",
                "requirement",
                "locked_value",
                "status",
            ],
        )
        writer.writeheader()
        for control in controls:
            writer.writerow(asdict(control))


def _text_report(report: ExecutionControlReport) -> str:
    lines = [
        "HQE Improved Recorded-Data Paper Rerun Execution Control Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Preflight report found: {report.preflight_report_found}",
        f"Preflight report status: {report.preflight_report_status}",
        f"Preflight accepts future runner: {report.preflight_accepts_future_runner}",
        (
            "Accepted for future improved paper rerun: "
            f"{report.accepted_for_future_improved_paper_rerun}"
        ),
        f"Controls locked: {report.locked_control_count}/{report.control_count}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 7 pending after module: {report.phase_7_pending_after_module}",
        f"Backtest executed: {report.backtest_executed}",
        f"Optimization executed: {report.optimization_executed}",
        f"Strategy logic changed: {report.strategy_logic_changed}",
        f"Broker mode: {report.broker_execution_mode}",
        f"Live data mode: {report.live_data_mode}",
        f"Runner dataset mode: {report.runner_dataset_mode}",
        f"Runner order mode: {report.runner_order_mode}",
        f"Runner output contract locked: {report.runner_output_contract_locked}",
        f"Ready for live/real money: {report.ready_for_live_or_real_money}",
        f"Profitability claim allowed: {report.profitability_claim_allowed}",
        "",
        report.safety_notice,
        report.no_profitability_claim_notice,
        "",
        "Execution controls:",
    ]
    for control in report.controls:
        lines.extend(
            [
                "",
                f"- {control.id}: {control.title}",
                f"  Type: {control.control_type}",
                f"  Requirement: {control.requirement}",
                f"  Locked value: {control.locked_value}",
                f"  Status: {control.status}",
            ]
        )
    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")
    return "\n".join(lines) + "\n"


def write_execution_control_pack(
    report: ExecutionControlReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    controls_csv = output_dir / "improved_recorded_data_paper_rerun_execution_controls.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_csv(controls_csv, report.controls)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "controls_csv": str(controls_csv),
        "manifest_json": str(manifest_json),
    }
    manifest_payload = {
        "report_type": REPORT_TYPE,
        "status": report.status,
        "generated_at_utc": report.generated_at_utc,
        "accepted_for_future_improved_paper_rerun": report.accepted_for_future_improved_paper_rerun,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_7_pending_after_module": report.phase_7_pending_after_module,
        "runner_output_contract_locked": report.runner_output_contract_locked,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
        "outputs": outputs,
    }
    _write_json(manifest_json, manifest_payload)
    return outputs


def build_and_write_execution_control_pack(
    *,
    preflight_input_path: Path = DEFAULT_PREFLIGHT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[ExecutionControlReport, dict[str, str]]:
    report = build_execution_control_report(
        preflight_input_path=preflight_input_path,
        output_dir=output_dir,
    )
    outputs = write_execution_control_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Improved recorded-data paper rerun execution control pack."
    )
    parser.add_argument("--preflight-input", default=str(DEFAULT_PREFLIGHT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_execution_control_pack(
        preflight_input_path=Path(args.preflight_input),
        output_dir=Path(args.output_dir),
    )

    print("HQE improved recorded-data paper rerun execution control pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Preflight report found: {report.preflight_report_found}")
    print(f"Preflight accepts future runner: {report.preflight_accepts_future_runner}")
    print(f"Accepted for future improved paper rerun: {report.accepted_for_future_improved_paper_rerun}")
    print(f"Controls locked: {report.locked_control_count}/{report.control_count}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 7 pending after module: {report.phase_7_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
