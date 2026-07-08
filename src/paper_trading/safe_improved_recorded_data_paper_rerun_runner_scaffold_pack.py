"""
Safe Improved Recorded-Data Paper Rerun Runner Scaffold Pack

Module FFFFF - paper/offline runner scaffold only.

This pack starts Phase 8 by building the safe runner scaffold for a future
improved recorded-data paper rerun. It verifies the Phase 7 close report and
writes the runner scaffold contract.

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


DEFAULT_PHASE7_CLOSE_INPUT = Path(
    "reports/paper_trading/improved_recorded_data_paper_rerun_sprint_close_pack/"
    "improved_recorded_data_paper_rerun_sprint_close_pack.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/safe_improved_recorded_data_paper_rerun_runner_scaffold_pack"
)

REPORT_TYPE = "safe_improved_recorded_data_paper_rerun_runner_scaffold_pack"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Safe improved recorded-data paper rerun runner scaffold only. This pack does "
    "not run a backtest, connect to brokers, request live market data, place real "
    "orders, use real money, approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Runner scaffold status, future paper rerun "
    "readiness, win rate, expectancy, equity, and simulated total references remain "
    "paper/simulation evidence only."
)


@dataclass(frozen=True)
class RunnerScaffoldComponent:
    id: str
    title: str
    component_type: str
    purpose: str
    locked_boundary: str
    status: str


@dataclass(frozen=True)
class RunnerScaffoldReport:
    report_type: str
    status: str
    generated_at_utc: str
    phase7_close_input_path: str
    output_directory: str
    phase7_close_report_found: bool
    phase7_close_status: str
    phase7_complete: bool
    phase7_accepts_runner_build: bool
    scaffold_component_count: int
    locked_component_count: int
    accepted_for_future_runner_dry_run_pack: bool
    completed_total_after_module: int
    phase_8_pending_after_module: int
    backtest_executed: bool
    optimization_executed: bool
    strategy_logic_changed: bool
    broker_execution_mode: str
    live_data_mode: str
    real_order_mode: str
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    runner_scaffold_built: bool
    runner_execution_enabled: bool
    safety_notice: str
    no_profitability_claim_notice: str
    issues: list[dict[str, Any]]
    components: list[RunnerScaffoldComponent]


def _load_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [
            {
                "code": "phase7_close_input_missing",
                "severity": "warn",
                "message": f"Input report not found: {path}",
            }
        ]

    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": "phase7_close_input_invalid_json",
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


def _standard_components() -> list[RunnerScaffoldComponent]:
    return [
        RunnerScaffoldComponent(
            "component-01",
            "Runner input loader contract",
            "input",
            "Future runner must load local recorded data and Phase 6/7 evidence inputs from disk only.",
            "local_files_only; recorded_data_only; no_live_data",
            "locked",
        ),
        RunnerScaffoldComponent(
            "component-02",
            "Paper trade mapping contract",
            "trade_mapping",
            "Future runner must map decisions into paper option-buy plans only.",
            "LONG=CE_BUY_PAPER; SHORT=PE_BUY_PAPER; NEUTRAL=NO_TRADE",
            "locked",
        ),
        RunnerScaffoldComponent(
            "component-03",
            "Improvement layer pipeline contract",
            "pipeline",
            "Future runner must preserve separate layers for baseline, pricing reality, slippage/cost, exit-rule, cooldown/duplicate, and session/frequency checks.",
            "layered_comparison_required",
            "locked",
        ),
        RunnerScaffoldComponent(
            "component-04",
            "Skip reason and reduction contract",
            "output_schema",
            "Future runner must emit skipped reasons and layer-level reduction counts.",
            "skipped_reasons_required; layer_counts_required",
            "locked",
        ),
        RunnerScaffoldComponent(
            "component-05",
            "No broker/live execution contract",
            "safety",
            "Future runner must keep broker, live-data, and real-order paths disabled.",
            "broker_disabled; live_data_disabled; real_orders_disabled",
            "locked",
        ),
        RunnerScaffoldComponent(
            "component-06",
            "No-profitability-claim contract",
            "reporting",
            "Future runner output must remain paper/simulation evidence only.",
            "profitability_claim_allowed=false; ready_for_live_or_real_money=false",
            "locked",
        ),
    ]


def build_runner_scaffold_report(
    *,
    phase7_close_input_path: Path = DEFAULT_PHASE7_CLOSE_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> RunnerScaffoldReport:
    phase7_payload, issues = _load_json(phase7_close_input_path)

    phase7_found = phase7_payload is not None
    phase7_status = _payload_status(phase7_payload)
    phase7_complete = _payload_bool(phase7_payload, "phase_7_complete")
    phase7_accepts = _payload_bool(
        phase7_payload,
        "accepted_for_future_safe_paper_rerun_runner_build",
    )

    unsafe_phase7 = (
        _payload_bool(phase7_payload, "ready_for_live_or_real_money")
        or _payload_bool(phase7_payload, "profitability_claim_allowed")
        or _payload_bool(phase7_payload, "strategy_logic_changed")
        or _payload_bool(phase7_payload, "backtest_executed")
    )
    if unsafe_phase7:
        issues.append(
            {
                "code": "unsafe_phase7_close_boundary",
                "severity": "fail",
                "message": "Phase 7 close report allowed live/real money, profit claim, strategy change, or backtest execution.",
            }
        )

    if phase7_found and phase7_status != "pass":
        issues.append(
            {
                "code": "phase7_close_not_pass",
                "severity": "warn",
                "message": f"Phase 7 close report status is {phase7_status}.",
            }
        )

    if phase7_found and not phase7_complete:
        issues.append(
            {
                "code": "phase7_not_complete",
                "severity": "warn",
                "message": "Phase 7 close report exists, but phase_7_complete is not true.",
            }
        )

    if phase7_found and not phase7_accepts:
        issues.append(
            {
                "code": "phase7_not_accepted_for_runner_build",
                "severity": "warn",
                "message": "Phase 7 close report does not accept future safe paper rerun runner build.",
            }
        )

    failure_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "pass" if not failure_issues else "fail"

    accepted = (
        phase7_found
        and phase7_status == "pass"
        and phase7_complete
        and phase7_accepts
        and not unsafe_phase7
        and not failure_issues
    )

    components = _standard_components()

    return RunnerScaffoldReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        phase7_close_input_path=str(phase7_close_input_path),
        output_directory=str(output_dir),
        phase7_close_report_found=phase7_found,
        phase7_close_status=phase7_status,
        phase7_complete=phase7_complete,
        phase7_accepts_runner_build=phase7_accepts,
        scaffold_component_count=len(components),
        locked_component_count=sum(1 for component in components if component.status == "locked"),
        accepted_for_future_runner_dry_run_pack=accepted,
        completed_total_after_module=110,
        phase_8_pending_after_module=2,
        backtest_executed=False,
        optimization_executed=False,
        strategy_logic_changed=False,
        broker_execution_mode=SAFE_BROKER_MODE,
        live_data_mode=SAFE_DATA_MODE,
        real_order_mode=SAFE_ORDER_MODE,
        ready_for_live_or_real_money=False,
        profitability_claim_allowed=False,
        runner_scaffold_built=True,
        runner_execution_enabled=False,
        safety_notice=SAFETY_NOTICE,
        no_profitability_claim_notice=NO_PROFIT_CLAIM,
        issues=issues,
        components=components,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, components: list[RunnerScaffoldComponent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "title",
                "component_type",
                "purpose",
                "locked_boundary",
                "status",
            ],
        )
        writer.writeheader()
        for component in components:
            writer.writerow(asdict(component))


def _text_report(report: RunnerScaffoldReport) -> str:
    lines = [
        "HQE Safe Improved Recorded-Data Paper Rerun Runner Scaffold Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Phase 7 close report found: {report.phase7_close_report_found}",
        f"Phase 7 close status: {report.phase7_close_status}",
        f"Phase 7 complete: {report.phase7_complete}",
        f"Phase 7 accepts runner build: {report.phase7_accepts_runner_build}",
        (
            "Accepted for future runner dry-run pack: "
            f"{report.accepted_for_future_runner_dry_run_pack}"
        ),
        f"Scaffold components locked: {report.locked_component_count}/{report.scaffold_component_count}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 8 pending after module: {report.phase_8_pending_after_module}",
        f"Runner scaffold built: {report.runner_scaffold_built}",
        f"Runner execution enabled: {report.runner_execution_enabled}",
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
        "Runner scaffold components:",
    ]
    for component in report.components:
        lines.extend(
            [
                "",
                f"- {component.id}: {component.title}",
                f"  Type: {component.component_type}",
                f"  Purpose: {component.purpose}",
                f"  Locked boundary: {component.locked_boundary}",
                f"  Status: {component.status}",
            ]
        )
    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")
    return "\n".join(lines) + "\n"


def write_runner_scaffold_pack(
    report: RunnerScaffoldReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    components_csv = output_dir / "safe_improved_recorded_data_paper_rerun_runner_scaffold_components.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_csv(components_csv, report.components)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "components_csv": str(components_csv),
        "manifest_json": str(manifest_json),
    }
    manifest_payload = {
        "report_type": REPORT_TYPE,
        "status": report.status,
        "generated_at_utc": report.generated_at_utc,
        "accepted_for_future_runner_dry_run_pack": report.accepted_for_future_runner_dry_run_pack,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_8_pending_after_module": report.phase_8_pending_after_module,
        "runner_scaffold_built": report.runner_scaffold_built,
        "runner_execution_enabled": report.runner_execution_enabled,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
        "outputs": outputs,
    }
    _write_json(manifest_json, manifest_payload)
    return outputs


def build_and_write_runner_scaffold_pack(
    *,
    phase7_close_input_path: Path = DEFAULT_PHASE7_CLOSE_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[RunnerScaffoldReport, dict[str, str]]:
    report = build_runner_scaffold_report(
        phase7_close_input_path=phase7_close_input_path,
        output_dir=output_dir,
    )
    outputs = write_runner_scaffold_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safe improved recorded-data paper rerun runner scaffold pack."
    )
    parser.add_argument("--phase7-close-input", default=str(DEFAULT_PHASE7_CLOSE_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_runner_scaffold_pack(
        phase7_close_input_path=Path(args.phase7_close_input),
        output_dir=Path(args.output_dir),
    )

    print("HQE safe improved recorded-data paper rerun runner scaffold pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Phase 7 close report found: {report.phase7_close_report_found}")
    print(f"Phase 7 complete: {report.phase7_complete}")
    print(f"Accepted for future runner dry-run pack: {report.accepted_for_future_runner_dry_run_pack}")
    print(f"Scaffold components locked: {report.locked_component_count}/{report.scaffold_component_count}")
    print(f"Runner execution enabled: {report.runner_execution_enabled}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 8 pending after module: {report.phase_8_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
