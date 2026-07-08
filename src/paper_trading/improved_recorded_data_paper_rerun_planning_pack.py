"""
Improved Recorded-Data Paper Rerun Planning Pack

Module BBBBB - paper/offline planning only.

This pack starts the next safe phase after the paper improvement execution sprint.
It creates a controlled plan for a future improved recorded-data paper rerun using
the evidence from Modules VVVV through AAAAA.

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


DEFAULT_CLOSE_INPUT = Path(
    "reports/paper_trading/paper_improvement_execution_sprint_close_pack/"
    "paper_improvement_execution_sprint_close_pack.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/improved_recorded_data_paper_rerun_planning_pack"
)

REPORT_TYPE = "improved_recorded_data_paper_rerun_planning_pack"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "live_data_disabled"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Improved recorded-data paper rerun planning only. This pack does not run a "
    "backtest, connect to brokers, request live market data, place real orders, use "
    "real money, approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. The future rerun plan, comparison matrix, "
    "pricing reality, slippage/cost, exit-rule, cooldown/duplicate, session/frequency, "
    "win rate, expectancy, equity, and simulated total references remain paper/simulation "
    "evidence only."
)


@dataclass(frozen=True)
class RerunPlanStep:
    id: str
    title: str
    purpose: str
    required_input: str
    output_evidence: str
    safety_boundary: str
    status: str


@dataclass(frozen=True)
class RerunPlanningReport:
    report_type: str
    status: str
    generated_at_utc: str
    close_input_path: str
    output_directory: str
    close_report_found: bool
    close_report_status: str
    phase_6_complete: bool
    accepted_for_improved_paper_rerun_planning: bool
    accepted_for_future_improved_rerun_execution: bool
    plan_step_count: int
    high_impact_step_count: int
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
    safety_notice: str
    no_profitability_claim_notice: str
    issues: list[dict[str, Any]]
    steps: list[RerunPlanStep]


def _load_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [
            {
                "code": "close_input_missing",
                "severity": "warn",
                "message": f"Input report not found: {path}",
            }
        ]

    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": "close_input_invalid_json",
                "severity": "fail",
                "message": str(exc),
            }
        ]


def _standard_steps() -> list[RerunPlanStep]:
    return [
        RerunPlanStep(
            "step-01",
            "Freeze baseline reference inputs",
            "Keep the current SMC parameter-aligned recorded-data baseline traceable before comparison.",
            "Existing one-month recorded NIFTY 5-minute data and current paper evidence reports.",
            "Baseline manifest with dataset path, row count, date span, and no-live-data wording.",
            "No new market data download and no live data dependency.",
            "planned",
        ),
        RerunPlanStep(
            "step-02",
            "Define comparison matrix",
            "Compare baseline, pricing reality, slippage/cost, exit-rule, cooldown/duplicate, and session/frequency assumptions.",
            "Phase 6 close pack and all VVVV-ZZZZ evidence reports.",
            "Comparison matrix showing each assumption layer, expected output, and skipped-reason fields.",
            "No optimization, no parameter hunt, and no winning-strategy selection.",
            "planned",
        ),
        RerunPlanStep(
            "step-03",
            "Lock rerun safety gates",
            "Prevent accidental live/broker/real-money interpretation before any future rerun command exists.",
            "Safety flags from close pack and project-level paper-only boundaries.",
            "Rerun guard checklist with broker disabled, live data disabled, real orders disabled.",
            "LONG remains CE BUY paper plan only; SHORT remains PE BUY paper plan only; NEUTRAL remains no trade.",
            "planned",
        ),
        RerunPlanStep(
            "step-04",
            "Define output evidence schema",
            "Make the future rerun auditable and comparable rather than result-only.",
            "Existing paper ledgers, review packs, and report manifests.",
            "Schema plan for raw plans, guarded plans, skipped reasons, costs, exits, daily/session concentration, and no-profit-claim summary.",
            "No profitability claim allowed even if paper reference totals are positive.",
            "planned",
        ),
        RerunPlanStep(
            "step-05",
            "Prepare rerun execution module boundary",
            "Separate planning from actual paper rerun execution so this module remains safe and reviewable.",
            "Approved planning report from this pack.",
            "Next-module readiness flag for a future paper-only improved rerun runner.",
            "This pack itself does not execute a backtest.",
            "blocked_until_next_module",
        ),
    ]


def build_rerun_planning_report(
    *,
    close_input_path: Path = DEFAULT_CLOSE_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> RerunPlanningReport:
    close_payload, issues = _load_json(close_input_path)

    close_found = close_payload is not None
    close_status = str((close_payload or {}).get("status") or "")
    phase_6_complete = bool((close_payload or {}).get("phase_6_complete", False))
    accepted_close = bool(
        (close_payload or {}).get("accepted_for_improved_paper_rerun_planning", False)
    )

    if close_found and not phase_6_complete:
        issues.append(
            {
                "code": "phase_6_not_complete",
                "severity": "warn",
                "message": "Close report exists, but phase_6_complete is not true.",
            }
        )

    if close_found and not accepted_close:
        issues.append(
            {
                "code": "close_not_accepted_for_rerun_planning",
                "severity": "warn",
                "message": "Close report is not accepted for improved paper rerun planning.",
            }
        )

    unsafe_close = bool((close_payload or {}).get("ready_for_live_or_real_money", False)) or bool(
        (close_payload or {}).get("profitability_claim_allowed", False)
    ) or bool((close_payload or {}).get("strategy_logic_changed", False))

    if unsafe_close:
        issues.append(
            {
                "code": "unsafe_close_boundary",
                "severity": "fail",
                "message": "Close report allowed live/real-money, profitability claim, or strategy logic change.",
            }
        )

    failure_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "pass" if not failure_issues else "fail"

    accepted_for_execution = (
        close_found
        and close_status == "pass"
        and phase_6_complete
        and accepted_close
        and not unsafe_close
        and not failure_issues
    )

    steps = _standard_steps()
    high_impact_count = sum(
        1 for step in steps if step.status in {"planned", "blocked_until_next_module"}
    )

    return RerunPlanningReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        close_input_path=str(close_input_path),
        output_directory=str(output_dir),
        close_report_found=close_found,
        close_report_status=close_status,
        phase_6_complete=phase_6_complete,
        accepted_for_improved_paper_rerun_planning=accepted_close,
        accepted_for_future_improved_rerun_execution=accepted_for_execution,
        plan_step_count=len(steps),
        high_impact_step_count=high_impact_count,
        completed_total_after_module=106,
        phase_7_pending_after_module=3,
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
        steps=steps,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, steps: list[RerunPlanStep]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "title",
                "purpose",
                "required_input",
                "output_evidence",
                "safety_boundary",
                "status",
            ],
        )
        writer.writeheader()
        for step in steps:
            writer.writerow(asdict(step))


def _text_report(report: RerunPlanningReport) -> str:
    lines = [
        "HQE Improved Recorded-Data Paper Rerun Planning Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Close report found: {report.close_report_found}",
        f"Close report status: {report.close_report_status}",
        f"Phase 6 complete: {report.phase_6_complete}",
        (
            "Accepted for improved paper rerun planning: "
            f"{report.accepted_for_improved_paper_rerun_planning}"
        ),
        (
            "Accepted for future improved rerun execution: "
            f"{report.accepted_for_future_improved_rerun_execution}"
        ),
        f"Plan steps: {report.plan_step_count}",
        f"High impact steps: {report.high_impact_step_count}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 7 pending after module: {report.phase_7_pending_after_module}",
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
        "Plan steps:",
    ]
    for step in report.steps:
        lines.extend(
            [
                "",
                f"- {step.id}: {step.title}",
                f"  Purpose: {step.purpose}",
                f"  Required input: {step.required_input}",
                f"  Output evidence: {step.output_evidence}",
                f"  Safety boundary: {step.safety_boundary}",
                f"  Status: {step.status}",
            ]
        )
    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")
    return "\n".join(lines) + "\n"


def write_rerun_planning_pack(
    report: RerunPlanningReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    steps_csv = output_dir / "improved_recorded_data_paper_rerun_plan_steps.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_csv(steps_csv, report.steps)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "steps_csv": str(steps_csv),
        "manifest_json": str(manifest_json),
    }
    manifest_payload = {
        "report_type": REPORT_TYPE,
        "status": report.status,
        "generated_at_utc": report.generated_at_utc,
        "accepted_for_future_improved_rerun_execution": report.accepted_for_future_improved_rerun_execution,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_7_pending_after_module": report.phase_7_pending_after_module,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
        "outputs": outputs,
    }
    _write_json(manifest_json, manifest_payload)
    return outputs


def build_and_write_rerun_planning_pack(
    *,
    close_input_path: Path = DEFAULT_CLOSE_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[RerunPlanningReport, dict[str, str]]:
    report = build_rerun_planning_report(
        close_input_path=close_input_path,
        output_dir=output_dir,
    )
    outputs = write_rerun_planning_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Improved recorded-data paper rerun planning pack."
    )
    parser.add_argument("--close-input", default=str(DEFAULT_CLOSE_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_rerun_planning_pack(
        close_input_path=Path(args.close_input),
        output_dir=Path(args.output_dir),
    )

    print("HQE improved recorded-data paper rerun planning pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Close report found: {report.close_report_found}")
    print(f"Phase 6 complete: {report.phase_6_complete}")
    print(
        "Accepted for future improved rerun execution: "
        f"{report.accepted_for_future_improved_rerun_execution}"
    )
    print(f"Plan steps: {report.plan_step_count}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 7 pending after module: {report.phase_7_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
