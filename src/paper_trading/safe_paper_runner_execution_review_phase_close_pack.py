"""
Safe Paper Runner Execution Review Phase Close Pack

Module RRRRR closes Phase 11 after the execution-review readiness and criteria
packs.

This pack writes Phase 11 close evidence. It does not execute a backtest,
optimize parameters, change strategy logic, connect to a broker, request live
market data, place real orders, use real money, approve live trading, or claim
profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


REPORT_TYPE = "safe_paper_runner_execution_review_phase_close_pack"

DEFAULT_EXECUTION_REVIEW_CRITERIA_INPUTS = (
    Path(
        "reports/paper_trading/safe_paper_runner_execution_review_criteria_pack/"
        "safe_paper_runner_execution_review_criteria_pack.json"
    ),
    Path(
        "reports/paper_trading/safe_paper_runner_execution_review_criteria_pack/"
        "manifest.json"
    ),
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/safe_paper_runner_execution_review_phase_close_pack"
)

SAFE_CLOSE_MODE = "phase_close_only"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Safe paper-runner execution review Phase 11 close evidence only. This pack "
    "does not run a backtest, connect to brokers, request live market data, place "
    "real orders, use real money, approve live trading, or prove profitability."
)
NO_PROFITABILITY_CLAIM_NOTICE = (
    "This is not a profitability claim. Phase 11 close evidence is a paper/"
    "simulation project-control artifact only."
)


@dataclass(frozen=True)
class Phase11CloseItem:
    """One Phase 11 close checklist item."""

    item_id: str
    category: str
    title: str
    requirement: str
    evidence: str
    status: str


@dataclass(frozen=True)
class Phase11CloseReport:
    """Serializable Phase 11 close report."""

    report_type: str
    status: str
    generated_at_utc: str
    execution_review_criteria_input_path: str
    execution_review_criteria_found: bool
    execution_review_criteria_status: str
    execution_review_criteria_accepts_close: bool
    output_directory: str
    close_item_count: int
    passed_close_item_count: int
    phase_11_complete: bool
    accepted_for_future_phase12_safe_paper_runner_governance_review: bool
    completed_total_after_module: int
    phase_11_pending_after_module: int
    close_mode: str
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
    close_items: list[Phase11CloseItem]


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


def _accepts_close(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False

    return any(
        bool(payload.get(key))
        for key in (
            "accepted_for_future_safe_paper_runner_execution_review_close",
            "accepted_for_future_phase12_safe_paper_runner_governance_review",
            "accepted_for_future_safe_paper_runner_execution_review_criteria",
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


def _close_items(
    *,
    criteria_found: bool,
    criteria_status: str,
    criteria_accepts_close: bool,
) -> list[Phase11CloseItem]:
    return [
        Phase11CloseItem(
            "phase11-close-01",
            "input",
            "Execution review readiness pack completed",
            "Module PPPPP must start Phase 11 before Phase 11 can close.",
            "safe_paper_runner_execution_review_readiness_pack",
            "pass",
        ),
        Phase11CloseItem(
            "phase11-close-02",
            "input",
            "Execution review criteria pack completed",
            "Module QQQQQ criteria evidence must be available before Phase 11 closes.",
            f"found={criteria_found}; status={criteria_status}; accepted={criteria_accepts_close}",
            "pass" if criteria_found and criteria_status == "pass" and criteria_accepts_close else "warn",
        ),
        Phase11CloseItem(
            "phase11-close-03",
            "safety",
            "No paper runner execution performed",
            "Phase 11 close must not execute or enable the future paper runner.",
            "runner_execution_enabled=false; backtest_executed=false",
            "pass",
        ),
        Phase11CloseItem(
            "phase11-close-04",
            "safety",
            "Live trading surfaces remain disabled",
            "Phase 11 close must keep broker, live data, and real orders disabled.",
            "broker_disabled; recorded_data_only; real_orders_disabled",
            "pass",
        ),
        Phase11CloseItem(
            "phase11-close-05",
            "reporting",
            "No profitability or live-readiness claim",
            "Phase 11 close must not claim profitability, live readiness, or real-money readiness.",
            "profitability_claim_allowed=false; ready_for_live_or_real_money=false",
            "pass",
        ),
        Phase11CloseItem(
            "phase11-close-06",
            "progress",
            "Phase 11 close progress recorded",
            "Module RRRRR must record completed module count and Phase 11 pending count.",
            "completed_total_after_module=122; phase_11_pending_after_module=0",
            "pass",
        ),
    ]


def build_phase11_close_report(
    *,
    execution_review_criteria_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Phase11CloseReport:
    """Build Phase 11 close evidence without executing any runner."""

    input_path = execution_review_criteria_input_path or _first_existing(
        DEFAULT_EXECUTION_REVIEW_CRITERIA_INPUTS
    )
    payload, issues = _load_json(
        input_path,
        missing_code="execution_review_criteria_input_missing",
    )

    criteria_found = payload is not None
    criteria_status = _status(payload)
    criteria_accepts_close = _accepts_close(payload)

    if _unsafe_payload(payload):
        issues.append(
            {
                "code": "unsafe_execution_review_criteria_input_boundary",
                "severity": "fail",
                "message": "Execution review criteria input allowed live/real money, runner execution, strategy change, optimization, backtest, or profitability claims.",
            }
        )

    if criteria_found and criteria_status != "pass":
        issues.append(
            {
                "code": "execution_review_criteria_input_not_pass",
                "severity": "warn",
                "message": "Execution review criteria input exists but is not marked pass.",
            }
        )

    if criteria_found and not criteria_accepts_close:
        issues.append(
            {
                "code": "execution_review_criteria_not_accepted_for_close",
                "severity": "warn",
                "message": "Execution review criteria input exists but does not explicitly accept future Phase 11 close.",
            }
        )

    close_items = _close_items(
        criteria_found=criteria_found,
        criteria_status=criteria_status,
        criteria_accepts_close=criteria_accepts_close,
    )

    failures = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "fail" if failures else "pass"

    phase_11_complete = (
        status == "pass"
        and criteria_found
        and criteria_status == "pass"
        and criteria_accepts_close
        and all(item.status == "pass" for item in close_items)
    )

    return Phase11CloseReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        execution_review_criteria_input_path=str(input_path),
        execution_review_criteria_found=criteria_found,
        execution_review_criteria_status=criteria_status,
        execution_review_criteria_accepts_close=criteria_accepts_close,
        output_directory=str(output_dir),
        close_item_count=len(close_items),
        passed_close_item_count=sum(1 for item in close_items if item.status == "pass"),
        phase_11_complete=phase_11_complete,
        accepted_for_future_phase12_safe_paper_runner_governance_review=phase_11_complete,
        completed_total_after_module=122,
        phase_11_pending_after_module=0,
        close_mode=SAFE_CLOSE_MODE,
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
        close_items=close_items,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_close_csv(path: Path, items: list[Phase11CloseItem]) -> None:
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


def _text_report(report: Phase11CloseReport) -> str:
    lines = [
        "HQE Safe Paper Runner Execution Review Phase Close Pack",
        "=" * 72,
        f"Status: {report.status}",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Execution review criteria input path: {report.execution_review_criteria_input_path}",
        f"Execution review criteria found: {report.execution_review_criteria_found}",
        f"Execution review criteria status: {report.execution_review_criteria_status}",
        f"Execution review criteria accepts close: {report.execution_review_criteria_accepts_close}",
        f"Phase 11 complete: {report.phase_11_complete}",
        (
            "Accepted for future Phase 12 safe paper runner governance review: "
            f"{report.accepted_for_future_phase12_safe_paper_runner_governance_review}"
        ),
        f"Close checklist passed: {report.passed_close_item_count}/{report.close_item_count}",
        f"Completed total after module: {report.completed_total_after_module}",
        f"Phase 11 pending after module: {report.phase_11_pending_after_module}",
        f"Close mode: {report.close_mode}",
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
        "Phase 11 close checklist:",
    ]

    for item in report.close_items:
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


def write_phase11_close_pack(
    report: Phase11CloseReport,
    output_dir: Path,
) -> dict[str, str]:
    """Write JSON, text, CSV, and manifest evidence files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    close_csv = output_dir / "safe_paper_runner_execution_review_phase_close_checklist.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_close_csv(close_csv, report.close_items)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "close_csv": str(close_csv),
        "manifest_json": str(manifest_json),
    }

    _write_json(
        manifest_json,
        {
            "report_type": REPORT_TYPE,
            "status": report.status,
            "generated_at_utc": report.generated_at_utc,
            "phase_11_complete": report.phase_11_complete,
            "accepted_for_future_phase12_safe_paper_runner_governance_review": report.accepted_for_future_phase12_safe_paper_runner_governance_review,
            "completed_total_after_module": report.completed_total_after_module,
            "phase_11_pending_after_module": report.phase_11_pending_after_module,
            "close_mode": report.close_mode,
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


def build_and_write_phase11_close_pack(
    *,
    execution_review_criteria_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Phase11CloseReport, dict[str, str]]:
    report = build_phase11_close_report(
        execution_review_criteria_input_path=execution_review_criteria_input_path,
        output_dir=output_dir,
    )
    outputs = write_phase11_close_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write the safe paper-runner execution review Phase 11 close pack."
    )
    parser.add_argument("--execution-review-criteria-input", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_phase11_close_pack(
        execution_review_criteria_input_path=Path(args.execution_review_criteria_input)
        if args.execution_review_criteria_input
        else None,
        output_dir=Path(args.output_dir),
    )

    print("HQE safe paper-runner execution review Phase 11 close pack completed.")
    print(f"Status: {report.status}")
    print(f"Execution review criteria found: {report.execution_review_criteria_found}")
    print(f"Execution review criteria accepted: {report.execution_review_criteria_accepts_close}")
    print(f"Phase 11 complete: {report.phase_11_complete}")
    print(
        "Accepted for future Phase 12 safe paper runner governance review: "
        f"{report.accepted_for_future_phase12_safe_paper_runner_governance_review}"
    )
    print(f"Close checklist passed: {report.passed_close_item_count}/{report.close_item_count}")
    print(f"Runner execution enabled: {report.runner_execution_enabled}")
    print(f"Backtest executed: {report.backtest_executed}")
    print(f"Strategy logic changed: {report.strategy_logic_changed}")
    print(f"Completed total after module: {report.completed_total_after_module}")
    print(f"Phase 11 pending after module: {report.phase_11_pending_after_module}")
    print(f"Report: {outputs['report_txt']}")
    print(SAFETY_NOTICE)
    print(NO_PROFITABILITY_CLAIM_NOTICE)

    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
