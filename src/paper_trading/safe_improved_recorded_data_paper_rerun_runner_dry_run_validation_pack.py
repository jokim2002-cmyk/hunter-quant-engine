"""
Safe Improved Recorded-Data Paper Rerun Runner Dry-Run Validation Pack

Module GGGGG - paper/offline dry-run validation only.

This pack validates the safe runner scaffold from Module FFFFF using a dry-run
evidence contract. It checks that runner execution remains disabled while the
future runner's input, layer, output, and safety boundaries are reviewable.

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


DEFAULT_SCAFFOLD_INPUT = Path(
    "reports/paper_trading/safe_improved_recorded_data_paper_rerun_runner_scaffold_pack/"
    "safe_improved_recorded_data_paper_rerun_runner_scaffold_pack.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/safe_improved_recorded_data_paper_rerun_runner_dry_run_validation_pack"
)

REPORT_TYPE = "safe_improved_recorded_data_paper_rerun_runner_dry_run_validation_pack"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Safe improved recorded-data paper rerun runner dry-run validation only. This "
    "pack does not run a backtest, connect to brokers, request live market data, "
    "place real orders, use real money, approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Dry-run validation status, future runner "
    "readiness, win rate, expectancy, equity, and simulated total references remain "
    "paper/simulation evidence only."
)


@dataclass(frozen=True)
class DryRunValidationItem:
    id: str
    title: str
    validation_type: str
    requirement: str
    expected_value: str
    observed_value: str
    passed: bool
    status: str


@dataclass(frozen=True)
class RunnerDryRunValidationReport:
    report_type: str
    status: str
    generated_at_utc: str
    scaffold_input_path: str
    output_directory: str
    scaffold_report_found: bool
    scaffold_report_status: str
    scaffold_accepts_dry_run_pack: bool
    scaffold_runner_execution_enabled: bool
    validation_count: int
    passed_validation_count: int
    failed_validation_count: int
    accepted_for_future_runner_close_pack: bool
    completed_total_after_module: int
    phase_8_pending_after_module: int
    dry_run_validation_executed: bool
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
    validations: list[DryRunValidationItem]


def _load_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [
            {
                "code": "scaffold_input_missing",
                "severity": "warn",
                "message": f"Input report not found: {path}",
            }
        ]

    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": "scaffold_input_invalid_json",
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


def _standard_validations(
    *,
    scaffold_found: bool,
    scaffold_status: str,
    scaffold_accepts: bool,
    scaffold_runner_execution_enabled: bool,
    unsafe_scaffold: bool,
) -> list[DryRunValidationItem]:
    return [
        DryRunValidationItem(
            "validation-01",
            "Scaffold report exists",
            "input",
            "Module FFFFF scaffold report must exist.",
            "true",
            str(scaffold_found).lower(),
            scaffold_found,
            "passed" if scaffold_found else "failed",
        ),
        DryRunValidationItem(
            "validation-02",
            "Scaffold report passed",
            "input",
            "Module FFFFF scaffold status must be pass.",
            "pass",
            scaffold_status,
            scaffold_status == "pass",
            "passed" if scaffold_status == "pass" else "failed",
        ),
        DryRunValidationItem(
            "validation-03",
            "Scaffold accepts dry-run validation",
            "gate",
            "Module FFFFF must accept a future runner dry-run pack.",
            "true",
            str(scaffold_accepts).lower(),
            scaffold_accepts,
            "passed" if scaffold_accepts else "failed",
        ),
        DryRunValidationItem(
            "validation-04",
            "Runner execution remains disabled",
            "safety",
            "Dry-run validation must not enable the runner.",
            "false",
            str(scaffold_runner_execution_enabled).lower(),
            not scaffold_runner_execution_enabled,
            "passed" if not scaffold_runner_execution_enabled else "failed",
        ),
        DryRunValidationItem(
            "validation-05",
            "Scaffold safety boundary remains locked",
            "safety",
            "Scaffold must not allow live/real money, profit claims, backtest execution, or strategy changes.",
            "safe",
            "unsafe" if unsafe_scaffold else "safe",
            not unsafe_scaffold,
            "passed" if not unsafe_scaffold else "failed",
        ),
        DryRunValidationItem(
            "validation-06",
            "Dry-run evidence boundary",
            "reporting",
            "This module validates contracts only and must not execute a backtest.",
            "backtest_executed=false",
            "backtest_executed=false",
            True,
            "passed",
        ),
    ]


def build_runner_dry_run_validation_report(
    *,
    scaffold_input_path: Path = DEFAULT_SCAFFOLD_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> RunnerDryRunValidationReport:
    scaffold_payload, issues = _load_json(scaffold_input_path)

    scaffold_found = scaffold_payload is not None
    scaffold_status = _payload_status(scaffold_payload)
    scaffold_accepts = _payload_bool(
        scaffold_payload,
        "accepted_for_future_runner_dry_run_pack",
    )
    scaffold_runner_execution_enabled = _payload_bool(
        scaffold_payload,
        "runner_execution_enabled",
    )

    unsafe_scaffold = (
        _payload_bool(scaffold_payload, "ready_for_live_or_real_money")
        or _payload_bool(scaffold_payload, "profitability_claim_allowed")
        or _payload_bool(scaffold_payload, "strategy_logic_changed")
        or _payload_bool(scaffold_payload, "backtest_executed")
    )
    if unsafe_scaffold:
        issues.append(
            {
                "code": "unsafe_scaffold_boundary",
                "severity": "fail",
                "message": "Scaffold report allowed live/real money, profit claim, strategy change, or backtest execution.",
            }
        )

    validations = _standard_validations(
        scaffold_found=scaffold_found,
        scaffold_status=scaffold_status,
        scaffold_accepts=scaffold_accepts,
        scaffold_runner_execution_enabled=scaffold_runner_execution_enabled,
        unsafe_scaffold=unsafe_scaffold,
    )

    failed_validations = [item for item in validations if not item.passed]
    failed_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "pass" if not failed_validations and not failed_issues else "fail"

    accepted = status == "pass"

    return RunnerDryRunValidationReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        scaffold_input_path=str(scaffold_input_path),
        output_directory=str(output_dir),
        scaffold_report_found=scaffold_found,
        scaffold_report_status=scaffold_status,
        scaffold_accepts_dry_run_pack=scaffold_accepts,
        scaffold_runner_execution_enabled=scaffold_runner_execution_enabled,
        validation_count=len(validations),
        passed_validation_count=sum(1 for item in validations if item.passed),
        failed_validation_count=len(failed_validations),
        accepted_for_future_runner_close_pack=accepted,
        completed_total_after_module=111,
        phase_8_pending_after_module=1,
        dry_run_validation_executed=True,
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
        no_profitability_claim_notice=NO_PROFIT_CLAIM,
        issues=issues,
        validations=validations,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, validations: list[DryRunValidationItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "title",
                "validation_type",
                "requirement",
                "expected_value",
                "observed_value",
                "passed",
                "status",
            ],
        )
        writer.writeheader()
        for validation in validations:
            writer.writerow(asdict(validation))


def _text_report(report: RunnerDryRunValidationReport) -> str:
    lines = [
        "HQE Safe Improved Recorded-Data Paper Rerun Runner Dry-Run Validation Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Scaffold report found: {report.scaffold_report_found}",
        f"Scaffold report status: {report.scaffold_report_status}",
        f"Scaffold accepts dry-run pack: {report.scaffold_accepts_dry_run_pack}",
        f"Scaffold runner execution enabled: {report.scaffold_runner_execution_enabled}",
        f"Validations passed: {report.passed_validation_count}/{report.validation_count}",
        (
            "Accepted for future runner close pack: "
            f"{report.accepted_for_future_runner_close_pack}"
        ),
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 8 pending after module: {report.phase_8_pending_after_module}",
        f"Dry-run validation executed: {report.dry_run_validation_executed}",
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
        "Validations:",
    ]
    for validation in report.validations:
        lines.extend(
            [
                "",
                f"- {validation.id}: {validation.title}",
                f"  Type: {validation.validation_type}",
                f"  Requirement: {validation.requirement}",
                f"  Expected: {validation.expected_value}",
                f"  Observed: {validation.observed_value}",
                f"  Passed: {validation.passed}",
                f"  Status: {validation.status}",
            ]
        )
    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")
    return "\n".join(lines) + "\n"


def write_runner_dry_run_validation_pack(
    report: RunnerDryRunValidationReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    validations_csv = output_dir / "safe_improved_recorded_data_paper_rerun_runner_dry_run_validations.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_csv(validations_csv, report.validations)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "validations_csv": str(validations_csv),
        "manifest_json": str(manifest_json),
    }
    manifest_payload = {
        "report_type": REPORT_TYPE,
        "status": report.status,
        "generated_at_utc": report.generated_at_utc,
        "accepted_for_future_runner_close_pack": report.accepted_for_future_runner_close_pack,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_8_pending_after_module": report.phase_8_pending_after_module,
        "dry_run_validation_executed": report.dry_run_validation_executed,
        "runner_execution_enabled": False,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
        "outputs": outputs,
    }
    _write_json(manifest_json, manifest_payload)
    return outputs


def build_and_write_runner_dry_run_validation_pack(
    *,
    scaffold_input_path: Path = DEFAULT_SCAFFOLD_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[RunnerDryRunValidationReport, dict[str, str]]:
    report = build_runner_dry_run_validation_report(
        scaffold_input_path=scaffold_input_path,
        output_dir=output_dir,
    )
    outputs = write_runner_dry_run_validation_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safe improved recorded-data paper rerun runner dry-run validation pack."
    )
    parser.add_argument("--scaffold-input", default=str(DEFAULT_SCAFFOLD_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_runner_dry_run_validation_pack(
        scaffold_input_path=Path(args.scaffold_input),
        output_dir=Path(args.output_dir),
    )

    print("HQE safe improved recorded-data paper rerun runner dry-run validation pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Scaffold report found: {report.scaffold_report_found}")
    print(f"Validations passed: {report.passed_validation_count}/{report.validation_count}")
    print(f"Accepted for future runner close pack: {report.accepted_for_future_runner_close_pack}")
    print(f"Runner execution enabled: {report.runner_execution_enabled}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 8 pending after module: {report.phase_8_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
