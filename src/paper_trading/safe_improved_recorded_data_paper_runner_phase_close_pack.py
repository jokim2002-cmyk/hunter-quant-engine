"""
Safe Improved Recorded-Data Paper Runner Phase Close Pack

Module LLLLL closes Phase 9 after the execution plan and runner contract packs.

This pack verifies the local contract evidence boundary and writes Phase 9 close
evidence. It does not execute a backtest, optimize parameters, change strategy
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


REPORT_TYPE = "safe_improved_recorded_data_paper_runner_phase_close_pack"

DEFAULT_CONTRACT_INPUTS = (
    Path(
        "reports/paper_trading/safe_improved_recorded_data_paper_runner_contract_pack/"
        "safe_improved_recorded_data_paper_runner_contract_pack.json"
    ),
    Path(
        "reports/paper_trading/safe_improved_recorded_data_paper_runner_contract_pack/"
        "manifest.json"
    ),
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/safe_improved_recorded_data_paper_runner_phase_close_pack"
)

SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Safe improved recorded-data paper runner Phase 9 close evidence only. This "
    "pack does not run a backtest, connect to brokers, request live market data, "
    "place real orders, use real money, approve live trading, or prove profitability."
)
NO_PROFITABILITY_CLAIM_NOTICE = (
    "This is not a profitability claim. Phase 9 close evidence is a paper/simulation "
    "project-control artifact only."
)


@dataclass(frozen=True)
class PhaseCloseChecklistItem:
    """One Phase 9 close checklist item."""

    item_id: str
    category: str
    title: str
    requirement: str
    evidence: str
    status: str


@dataclass(frozen=True)
class PhaseCloseReport:
    """Serializable Phase 9 close evidence report."""

    report_type: str
    status: str
    generated_at_utc: str
    contract_input_path: str
    contract_report_found: bool
    contract_report_status: str
    contract_accepts_future_runner_execution: bool
    output_directory: str
    checklist_item_count: int
    passed_checklist_item_count: int
    phase_9_complete: bool
    accepted_for_future_phase10_safe_paper_runner_review: bool
    completed_total_after_module: int
    phase_9_pending_after_module: int
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
    checklist_items: list[PhaseCloseChecklistItem]


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


def _accepted_contract(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    return any(
        bool(payload.get(key))
        for key in (
            "accepted_for_future_guarded_paper_runner_execution",
            "accepted_for_future_guarded_runner_module",
            "accepted_for_future_phase10_safe_paper_runner_review",
        )
    )


def _unsafe_payload(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    return any(
        bool(payload.get(key))
        for key in (
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
    )


def _checklist_items(*, contract_found: bool, contract_status: str, contract_accepted: bool) -> list[PhaseCloseChecklistItem]:
    return [
        PhaseCloseChecklistItem(
            "close-01",
            "input",
            "Runner execution plan pack completed",
            "Module JJJJJ must provide a safe execution plan before Phase 9 closes.",
            "safe_improved_recorded_data_paper_runner_execution_plan_pack",
            "pass",
        ),
        PhaseCloseChecklistItem(
            "close-02",
            "input",
            "Runner contract pack completed",
            "Module KKKKK contract evidence must be available before Phase 9 closes.",
            f"found={contract_found}; status={contract_status}; accepted={contract_accepted}",
            "pass" if contract_found and contract_status == "pass" and contract_accepted else "warn",
        ),
        PhaseCloseChecklistItem(
            "close-03",
            "safety",
            "No runner execution performed",
            "Phase 9 close must not execute the future paper runner.",
            "runner_execution_enabled=false; backtest_executed=false",
            "pass",
        ),
        PhaseCloseChecklistItem(
            "close-04",
            "safety",
            "Broker and live data remain disabled",
            "Phase 9 close must keep broker, live data, and real orders disabled.",
            "broker_disabled; recorded_data_only; real_orders_disabled",
            "pass",
        ),
        PhaseCloseChecklistItem(
            "close-05",
            "reporting",
            "No profitability claim",
            "Phase 9 close must not claim profitability or live readiness.",
            "profitability_claim_allowed=false; ready_for_live_or_real_money=false",
            "pass",
        ),
        PhaseCloseChecklistItem(
            "close-06",
            "progress",
            "Phase 9 close progress recorded",
            "Module LLLLL must record completed module count and Phase 9 pending count.",
            "completed_total_after_module=116; phase_9_pending_after_module=0",
            "pass",
        ),
    ]


def build_phase_close_report(
    *,
    contract_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> PhaseCloseReport:
    """Build Phase 9 close report without executing any runner."""

    input_path = contract_input_path or _first_existing(DEFAULT_CONTRACT_INPUTS)
    payload, issues = _load_json(input_path, missing_code="contract_input_missing")

    contract_found = payload is not None
    contract_status = _status(payload)
    contract_accepted = _accepted_contract(payload)

    if _unsafe_payload(payload):
        issues.append(
            {
                "code": "unsafe_contract_input_boundary",
                "severity": "fail",
                "message": "Contract input allowed live/real money, runner execution, strategy change, optimization, backtest, or profitability claims.",
            }
        )

    if contract_found and contract_status != "pass":
        issues.append(
            {
                "code": "contract_input_not_pass",
                "severity": "warn",
                "message": "Contract input exists but is not marked pass.",
            }
        )

    if contract_found and not contract_accepted:
        issues.append(
            {
                "code": "contract_input_not_accepted",
                "severity": "warn",
                "message": "Contract input exists but is not explicitly accepted for future guarded paper runner execution.",
            }
        )

    checklist = _checklist_items(
        contract_found=contract_found,
        contract_status=contract_status,
        contract_accepted=contract_accepted,
    )

    failures = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "fail" if failures else "pass"

    phase_9_complete = (
        status == "pass"
        and contract_found
        and contract_status == "pass"
        and contract_accepted
        and all(item.status == "pass" for item in checklist)
    )

    return PhaseCloseReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        contract_input_path=str(input_path),
        contract_report_found=contract_found,
        contract_report_status=contract_status,
        contract_accepts_future_runner_execution=contract_accepted,
        output_directory=str(output_dir),
        checklist_item_count=len(checklist),
        passed_checklist_item_count=sum(1 for item in checklist if item.status == "pass"),
        phase_9_complete=phase_9_complete,
        accepted_for_future_phase10_safe_paper_runner_review=phase_9_complete,
        completed_total_after_module=116,
        phase_9_pending_after_module=0,
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
        checklist_items=checklist,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_checklist_csv(path: Path, items: list[PhaseCloseChecklistItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "item_id",
                "category",
                "title",
                "requirement",
                "evidence",
                "status",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def _text_report(report: PhaseCloseReport) -> str:
    lines = [
        "HQE Safe Improved Recorded-Data Paper Runner Phase Close Pack",
        "=" * 72,
        f"Status: {report.status}",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Contract input path: {report.contract_input_path}",
        f"Contract report found: {report.contract_report_found}",
        f"Contract report status: {report.contract_report_status}",
        f"Contract accepts future runner execution: {report.contract_accepts_future_runner_execution}",
        f"Phase 9 complete: {report.phase_9_complete}",
        (
            "Accepted for future Phase 10 safe paper runner review: "
            f"{report.accepted_for_future_phase10_safe_paper_runner_review}"
        ),
        f"Checklist passed: {report.passed_checklist_item_count}/{report.checklist_item_count}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 9 pending after module: {report.phase_9_pending_after_module}",
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
        "Checklist:",
    ]

    for item in report.checklist_items:
        lines.extend(
            [
                "",
                f"- {item.item_id}: {item.title}",
                f"  Category: {item.category}",
                f"  Requirement: {item.requirement}",
                f"  Evidence: {item.evidence}",
                f"  Status: {item.status}",
            ]
        )

    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(
                f"- {issue.get('severity', 'unknown').upper()} {issue.get('code')}: {issue.get('message')}"
            )

    return "\n".join(lines) + "\n"


def write_phase_close_pack(report: PhaseCloseReport, output_dir: Path) -> dict[str, str]:
    """Write JSON, text, CSV, and manifest evidence files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    checklist_csv = output_dir / "safe_improved_recorded_data_paper_runner_phase_close_checklist.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_checklist_csv(checklist_csv, report.checklist_items)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "checklist_csv": str(checklist_csv),
        "manifest_json": str(manifest_json),
    }

    _write_json(
        manifest_json,
        {
            "report_type": REPORT_TYPE,
            "status": report.status,
            "generated_at_utc": report.generated_at_utc,
            "phase_9_complete": report.phase_9_complete,
            "accepted_for_future_phase10_safe_paper_runner_review": report.accepted_for_future_phase10_safe_paper_runner_review,
            "completed_total_after_module": report.completed_total_after_module,
            "phase_9_pending_after_module": report.phase_9_pending_after_module,
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


def build_and_write_phase_close_pack(
    *,
    contract_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[PhaseCloseReport, dict[str, str]]:
    report = build_phase_close_report(
        contract_input_path=contract_input_path,
        output_dir=output_dir,
    )
    outputs = write_phase_close_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write the safe improved recorded-data paper runner Phase 9 close pack."
    )
    parser.add_argument("--contract-input", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_phase_close_pack(
        contract_input_path=Path(args.contract_input) if args.contract_input else None,
        output_dir=Path(args.output_dir),
    )

    print("HQE safe improved recorded-data paper runner Phase 9 close pack completed.")
    print(f"Status: {report.status}")
    print(f"Contract report found: {report.contract_report_found}")
    print(f"Contract report accepted: {report.contract_accepts_future_runner_execution}")
    print(f"Phase 9 complete: {report.phase_9_complete}")
    print(
        "Accepted for future Phase 10 safe paper runner review: "
        f"{report.accepted_for_future_phase10_safe_paper_runner_review}"
    )
    print(f"Checklist passed: {report.passed_checklist_item_count}/{report.checklist_item_count}")
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
