"""
Improved Recorded-Data Paper Rerun Preflight Pack

Module CCCCC - paper/offline preflight only.

This pack verifies the safe preflight conditions for a future improved recorded-data
paper rerun. It checks the rerun planning report, recorded dataset presence, and
paper-only safety gates before any actual improved paper rerun module exists.

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


DEFAULT_PLANNING_INPUT = Path(
    "reports/paper_trading/improved_recorded_data_paper_rerun_planning_pack/"
    "improved_recorded_data_paper_rerun_planning_pack.json"
)
DEFAULT_DATASET_PATH = Path("data/recorded/fyers_nifty_5min.csv")
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/improved_recorded_data_paper_rerun_preflight_pack"
)

REPORT_TYPE = "improved_recorded_data_paper_rerun_preflight_pack"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Improved recorded-data paper rerun preflight only. This pack does not run a "
    "backtest, connect to brokers, request live market data, place real orders, use "
    "real money, approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Dataset readiness, planning readiness, "
    "preflight checks, future rerun status, win rate, expectancy, equity, and "
    "simulated total references remain paper/simulation evidence only."
)


@dataclass(frozen=True)
class PreflightCheck:
    id: str
    title: str
    requirement: str
    observed_value: str
    passed: bool
    severity: str


@dataclass(frozen=True)
class RerunPreflightReport:
    report_type: str
    status: str
    generated_at_utc: str
    planning_input_path: str
    dataset_path: str
    output_directory: str
    planning_report_found: bool
    planning_report_status: str
    planning_accepts_future_execution: bool
    dataset_found: bool
    dataset_row_count_including_header: int
    dataset_record_count: int
    check_count: int
    passed_check_count: int
    failed_check_count: int
    accepted_for_future_improved_rerun_runner: bool
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
    checks: list[PreflightCheck]


def _load_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [
            {
                "code": "planning_input_missing",
                "severity": "warn",
                "message": f"Input report not found: {path}",
            }
        ]

    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": "planning_input_invalid_json",
                "severity": "fail",
                "message": str(exc),
            }
        ]


def _count_dataset_rows(path: Path) -> tuple[bool, int, int]:
    if not path.exists():
        return False, 0, 0

    row_count = 0
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as file:
        for _line in file:
            row_count += 1

    record_count = max(row_count - 1, 0)
    return True, row_count, record_count


def _planning_bool(payload: dict[str, Any] | None, key: str, default: bool = False) -> bool:
    if not payload:
        return default
    return bool(payload.get(key, default))


def _planning_status(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "missing"
    return str(payload.get("status") or "")


def build_rerun_preflight_report(
    *,
    planning_input_path: Path = DEFAULT_PLANNING_INPUT,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> RerunPreflightReport:
    planning_payload, issues = _load_json(planning_input_path)
    planning_found = planning_payload is not None
    planning_status = _planning_status(planning_payload)
    planning_accepts = _planning_bool(
        planning_payload,
        "accepted_for_future_improved_rerun_execution",
    )

    planning_unsafe = (
        _planning_bool(planning_payload, "ready_for_live_or_real_money")
        or _planning_bool(planning_payload, "profitability_claim_allowed")
        or _planning_bool(planning_payload, "strategy_logic_changed")
        or _planning_bool(planning_payload, "backtest_executed")
    )
    if planning_unsafe:
        issues.append(
            {
                "code": "unsafe_planning_boundary",
                "severity": "fail",
                "message": "Planning report allowed live/real money, profit claim, strategy change, or backtest execution.",
            }
        )

    dataset_found, row_count, record_count = _count_dataset_rows(dataset_path)

    checks = [
        PreflightCheck(
            "check-01",
            "Planning report exists",
            "Planning report from Module BBBBB must exist.",
            str(planning_found),
            planning_found,
            "fail",
        ),
        PreflightCheck(
            "check-02",
            "Planning report is pass",
            "Planning report status must be pass.",
            planning_status,
            planning_status == "pass",
            "fail",
        ),
        PreflightCheck(
            "check-03",
            "Planning accepts future improved rerun execution",
            "Module BBBBB must accept future paper-only rerun execution planning.",
            str(planning_accepts),
            planning_accepts,
            "fail",
        ),
        PreflightCheck(
            "check-04",
            "Recorded dataset exists",
            "Future rerun must use recorded local dataset only.",
            str(dataset_path),
            dataset_found,
            "fail",
        ),
        PreflightCheck(
            "check-05",
            "Recorded dataset has records",
            "Recorded dataset must have at least one data row after the header.",
            str(record_count),
            record_count > 0,
            "fail",
        ),
        PreflightCheck(
            "check-06",
            "Safety gates remain paper-only",
            "Planning report and this preflight must keep live/real-money/profit-claim gates disabled.",
            str(not planning_unsafe),
            not planning_unsafe,
            "fail",
        ),
    ]

    failed_checks = [check for check in checks if not check.passed]
    failed_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "pass" if not failed_checks and not failed_issues else "fail"

    accepted = status == "pass"

    return RerunPreflightReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        planning_input_path=str(planning_input_path),
        dataset_path=str(dataset_path),
        output_directory=str(output_dir),
        planning_report_found=planning_found,
        planning_report_status=planning_status,
        planning_accepts_future_execution=planning_accepts,
        dataset_found=dataset_found,
        dataset_row_count_including_header=row_count,
        dataset_record_count=record_count,
        check_count=len(checks),
        passed_check_count=sum(1 for check in checks if check.passed),
        failed_check_count=len(failed_checks),
        accepted_for_future_improved_rerun_runner=accepted,
        completed_total_after_module=107,
        phase_7_pending_after_module=2,
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
        checks=checks,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, checks: list[PreflightCheck]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "title",
                "requirement",
                "observed_value",
                "passed",
                "severity",
            ],
        )
        writer.writeheader()
        for check in checks:
            writer.writerow(asdict(check))


def _text_report(report: RerunPreflightReport) -> str:
    lines = [
        "HQE Improved Recorded-Data Paper Rerun Preflight Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Planning report found: {report.planning_report_found}",
        f"Planning report status: {report.planning_report_status}",
        f"Planning accepts future execution: {report.planning_accepts_future_execution}",
        f"Dataset found: {report.dataset_found}",
        f"Dataset rows including header: {report.dataset_row_count_including_header}",
        f"Dataset records: {report.dataset_record_count}",
        f"Checks: {report.passed_check_count}/{report.check_count} passed",
        (
            "Accepted for future improved rerun runner: "
            f"{report.accepted_for_future_improved_rerun_runner}"
        ),
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
        "Checks:",
    ]
    for check in report.checks:
        lines.extend(
            [
                "",
                f"- {check.id}: {check.title}",
                f"  Requirement: {check.requirement}",
                f"  Observed: {check.observed_value}",
                f"  Passed: {check.passed}",
                f"  Severity: {check.severity}",
            ]
        )
    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")
    return "\n".join(lines) + "\n"


def write_rerun_preflight_pack(
    report: RerunPreflightReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    checks_csv = output_dir / "improved_recorded_data_paper_rerun_preflight_checks.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_csv(checks_csv, report.checks)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "checks_csv": str(checks_csv),
        "manifest_json": str(manifest_json),
    }
    manifest_payload = {
        "report_type": REPORT_TYPE,
        "status": report.status,
        "generated_at_utc": report.generated_at_utc,
        "accepted_for_future_improved_rerun_runner": report.accepted_for_future_improved_rerun_runner,
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


def build_and_write_rerun_preflight_pack(
    *,
    planning_input_path: Path = DEFAULT_PLANNING_INPUT,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[RerunPreflightReport, dict[str, str]]:
    report = build_rerun_preflight_report(
        planning_input_path=planning_input_path,
        dataset_path=dataset_path,
        output_dir=output_dir,
    )
    outputs = write_rerun_preflight_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Improved recorded-data paper rerun preflight pack."
    )
    parser.add_argument("--planning-input", default=str(DEFAULT_PLANNING_INPUT))
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_rerun_preflight_pack(
        planning_input_path=Path(args.planning_input),
        dataset_path=Path(args.dataset),
        output_dir=Path(args.output_dir),
    )

    print("HQE improved recorded-data paper rerun preflight pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Planning report found: {report.planning_report_found}")
    print(f"Dataset found: {report.dataset_found}")
    print(f"Dataset records: {report.dataset_record_count}")
    print(f"Checks passed: {report.passed_check_count}/{report.check_count}")
    print(f"Accepted for future improved rerun runner: {report.accepted_for_future_improved_rerun_runner}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 7 pending after module: {report.phase_7_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
