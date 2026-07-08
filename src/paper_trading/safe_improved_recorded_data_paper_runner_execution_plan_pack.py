"""
Safe Improved Recorded-Data Paper Runner Execution Plan Pack

Module JJJJJ starts Phase 9 with a paper/offline execution-plan gate.

This pack reads earlier local evidence reports when available and writes a
future-runner execution plan. It does not execute a backtest, optimize
parameters, change strategy logic, connect to a broker, use live data, place
orders, approve live trading, use real money, or claim profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


REPORT_TYPE = "safe_improved_recorded_data_paper_runner_execution_plan_pack"

DEFAULT_PHASE8_CLOSE_INPUTS = (
    Path(
        "reports/paper_trading/safe_improved_recorded_data_paper_rerun_runner_build_sprint_close_pack/"
        "safe_improved_recorded_data_paper_rerun_runner_build_sprint_close_pack.json"
    ),
    Path(
        "reports/paper_trading/safe_improved_recorded_data_paper_rerun_runner_build_sprint_close_pack/"
        "manifest.json"
    ),
)
DEFAULT_ORGANIZATION_INPUTS = (
    Path(
        "reports/project_hygiene/hqe_project_artifact_organization_pack/"
        "hqe_project_artifact_organization_pack.json"
    ),
    Path("reports/project_hygiene/hqe_project_artifact_organization_pack/manifest.json"),
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/safe_improved_recorded_data_paper_runner_execution_plan_pack"
)

SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "recorded_data_only"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Safe improved recorded-data paper runner execution planning only. This pack "
    "does not run a backtest, connect to brokers, request live market data, place "
    "real orders, use real money, approve live trading, or prove profitability."
)
NO_PROFITABILITY_CLAIM_NOTICE = (
    "This is not a profitability claim. Any future runner totals, win rate, "
    "expectancy, equity, or simulated PnL references must remain paper/simulation "
    "evidence only."
)


@dataclass(frozen=True)
class ExecutionPlanItem:
    """One locked planning requirement for a future guarded runner module."""

    item_id: str
    title: str
    category: str
    requirement: str
    locked_value: str
    expected_evidence: str
    status: str


@dataclass(frozen=True)
class ExecutionPlanReport:
    """Serializable execution-plan evidence report."""

    report_type: str
    status: str
    generated_at_utc: str
    phase8_input_path: str
    phase8_report_found: bool
    phase8_report_status: str
    phase8_complete: bool
    phase8_accepts_execution_phase: bool
    organization_input_path: str
    organization_report_found: bool
    organization_report_status: str
    organization_accepts_phase9: bool
    output_directory: str
    plan_item_count: int
    locked_plan_item_count: int
    accepted_for_future_guarded_runner_module: bool
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
    plan_items: list[ExecutionPlanItem]


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


def _bool(payload: dict[str, Any] | None, key: str, *, default: bool = False) -> bool:
    if not payload:
        return default
    return bool(payload.get(key, default))


def _status(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "missing"
    return str(payload.get("status") or payload.get("report_status") or "unknown")


def _accepts_phase8_execution(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    return any(
        bool(payload.get(key))
        for key in (
            "accepted_for_future_improved_paper_runner_execution_phase",
            "accepted_for_future_guarded_runner_module",
            "accepted_for_phase9_continuation",
        )
    )


def _is_phase8_complete(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    return any(
        bool(payload.get(key))
        for key in (
            "phase_8_complete",
            "safe_improved_recorded_data_paper_rerun_runner_build_sprint_complete",
            "phase_complete",
        )
    )


def _accepts_organization(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    return any(
        bool(payload.get(key))
        for key in (
            "accepted_for_phase9_continuation",
            "root_runner_clutter_cleared",
            "accepted_for_future_guarded_runner_module",
        )
    )


def _has_unsafe_boundary(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    return any(
        bool(payload.get(key))
        for key in (
            "ready_for_live_or_real_money",
            "profitability_claim_allowed",
            "backtest_executed",
            "optimization_executed",
            "strategy_logic_changed",
            "broker_execution_enabled",
            "live_data_enabled",
            "real_order_enabled",
        )
    )


def _plan_items() -> list[ExecutionPlanItem]:
    return [
        ExecutionPlanItem(
            "plan-01",
            "Recorded-data-only input gate",
            "input",
            "Future guarded runner must use the local recorded NIFTY dataset only.",
            "data/recorded/fyers_nifty_5min.csv",
            "Dataset path, row count, record count, and recorded-data-only manifest fields.",
            "locked",
        ),
        ExecutionPlanItem(
            "plan-02",
            "Prior evidence input manifest gate",
            "input",
            "Future guarded runner must list all local evidence inputs used for the comparison.",
            "local_reports_required",
            "Found/missing/accepted manifest for pricing, slippage/cost, exit, cooldown, session, preflight, and control evidence.",
            "locked",
        ),
        ExecutionPlanItem(
            "plan-03",
            "Paper option-buy mapping gate",
            "trade_mapping",
            "Future guarded runner must map LONG to CE BUY paper plan, SHORT to PE BUY paper plan, and NEUTRAL to no trade.",
            "LONG=CE_BUY_PAPER; SHORT=PE_BUY_PAPER; NEUTRAL=NO_TRADE",
            "Paper ledger fields for direction, option intent, and skipped reason.",
            "locked",
        ),
        ExecutionPlanItem(
            "plan-04",
            "Layered comparison output gate",
            "output_schema",
            "Future guarded runner must compare baseline, pricing reality, slippage/cost, exit-rule, cooldown/duplicate, and session/frequency layers.",
            "layered_comparison_required",
            "JSON, text, CSV, and manifest outputs with layer-level differences.",
            "locked",
        ),
        ExecutionPlanItem(
            "plan-05",
            "No live/broker/real-order gate",
            "safety",
            "Future guarded runner must not connect to brokers, request live data, place orders, or use real money.",
            "broker_disabled; live_data_disabled; real_orders_disabled",
            "Manifest safety flags remain disabled.",
            "locked",
        ),
        ExecutionPlanItem(
            "plan-06",
            "No-profitability-claim reporting gate",
            "reporting",
            "Future guarded runner must say that all results are paper/simulation references only.",
            "profitability_claim_allowed=false; ready_for_live_or_real_money=false",
            "Report text and manifest include no-profitability-claim notice.",
            "locked",
        ),
    ]


def build_execution_plan_report(
    *,
    phase8_input_path: Path | None = None,
    organization_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ExecutionPlanReport:
    """Build a safe execution-plan report without executing any runner."""

    phase8_path = phase8_input_path or _first_existing(DEFAULT_PHASE8_CLOSE_INPUTS)
    organization_path = organization_input_path or _first_existing(DEFAULT_ORGANIZATION_INPUTS)

    phase8_payload, issues = _load_json(phase8_path, missing_code="phase8_input_missing")
    organization_payload, organization_issues = _load_json(
        organization_path,
        missing_code="organization_input_missing",
    )
    issues.extend(organization_issues)

    phase8_found = phase8_payload is not None
    organization_found = organization_payload is not None
    phase8_status = _status(phase8_payload)
    organization_status = _status(organization_payload)
    phase8_complete = _is_phase8_complete(phase8_payload)
    phase8_accepts = _accepts_phase8_execution(phase8_payload)
    organization_accepts = _accepts_organization(organization_payload)

    if _has_unsafe_boundary(phase8_payload):
        issues.append(
            {
                "code": "unsafe_phase8_input_boundary",
                "severity": "fail",
                "message": "Phase 8 input permits a live, real-order, optimization, strategy-change, backtest, or profitability boundary.",
            }
        )

    if _has_unsafe_boundary(organization_payload):
        issues.append(
            {
                "code": "unsafe_organization_input_boundary",
                "severity": "fail",
                "message": "Organization input permits a live, real-order, optimization, strategy-change, backtest, or profitability boundary.",
            }
        )

    if phase8_found and not phase8_complete:
        issues.append(
            {
                "code": "phase8_not_marked_complete",
                "severity": "warn",
                "message": "Phase 8 input was found, but it does not explicitly mark Phase 8 complete.",
            }
        )

    if organization_found and not organization_accepts:
        issues.append(
            {
                "code": "organization_not_marked_for_phase9",
                "severity": "warn",
                "message": "Organization input was found, but it does not explicitly accept Phase 9 continuation.",
            }
        )

    failures = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "fail" if failures else "pass"

    accepted = (
        status == "pass"
        and phase8_found
        and organization_found
        and phase8_status == "pass"
        and organization_status == "pass"
        and phase8_complete
        and phase8_accepts
        and organization_accepts
    )

    items = _plan_items()

    return ExecutionPlanReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        phase8_input_path=str(phase8_path),
        phase8_report_found=phase8_found,
        phase8_report_status=phase8_status,
        phase8_complete=phase8_complete,
        phase8_accepts_execution_phase=phase8_accepts,
        organization_input_path=str(organization_path),
        organization_report_found=organization_found,
        organization_report_status=organization_status,
        organization_accepts_phase9=organization_accepts,
        output_directory=str(output_dir),
        plan_item_count=len(items),
        locked_plan_item_count=sum(1 for item in items if item.status == "locked"),
        accepted_for_future_guarded_runner_module=accepted,
        completed_total_after_module=114,
        phase_9_pending_after_module=2,
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
        plan_items=items,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_plan_csv(path: Path, items: list[ExecutionPlanItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "item_id",
                "title",
                "category",
                "requirement",
                "locked_value",
                "expected_evidence",
                "status",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def _text_report(report: ExecutionPlanReport) -> str:
    lines = [
        "HQE Safe Improved Recorded-Data Paper Runner Execution Plan Pack",
        "=" * 78,
        f"Status: {report.status}",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Phase 8 input path: {report.phase8_input_path}",
        f"Phase 8 report found: {report.phase8_report_found}",
        f"Phase 8 report status: {report.phase8_report_status}",
        f"Phase 8 complete: {report.phase8_complete}",
        f"Phase 8 accepts execution phase: {report.phase8_accepts_execution_phase}",
        f"Organization input path: {report.organization_input_path}",
        f"Organization report found: {report.organization_report_found}",
        f"Organization report status: {report.organization_report_status}",
        f"Organization accepts Phase 9: {report.organization_accepts_phase9}",
        f"Accepted for future guarded runner module: {report.accepted_for_future_guarded_runner_module}",
        f"Plan items locked: {report.locked_plan_item_count}/{report.plan_item_count}",
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
        "Locked plan items:",
    ]

    for item in report.plan_items:
        lines.extend(
            [
                "",
                f"- {item.item_id}: {item.title}",
                f"  Category: {item.category}",
                f"  Requirement: {item.requirement}",
                f"  Locked value: {item.locked_value}",
                f"  Expected evidence: {item.expected_evidence}",
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


def write_execution_plan_pack(report: ExecutionPlanReport, output_dir: Path) -> dict[str, str]:
    """Write report JSON, text, CSV, and manifest outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    plan_csv = output_dir / "safe_improved_recorded_data_paper_runner_execution_plan_items.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_plan_csv(plan_csv, report.plan_items)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "plan_csv": str(plan_csv),
        "manifest_json": str(manifest_json),
    }

    _write_json(
        manifest_json,
        {
            "report_type": REPORT_TYPE,
            "status": report.status,
            "generated_at_utc": report.generated_at_utc,
            "accepted_for_future_guarded_runner_module": report.accepted_for_future_guarded_runner_module,
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


def build_and_write_execution_plan_pack(
    *,
    phase8_input_path: Path | None = None,
    organization_input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[ExecutionPlanReport, dict[str, str]]:
    report = build_execution_plan_report(
        phase8_input_path=phase8_input_path,
        organization_input_path=organization_input_path,
        output_dir=output_dir,
    )
    outputs = write_execution_plan_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write the safe improved recorded-data paper runner execution plan pack."
    )
    parser.add_argument("--phase8-input", default=None)
    parser.add_argument("--organization-input", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_execution_plan_pack(
        phase8_input_path=Path(args.phase8_input) if args.phase8_input else None,
        organization_input_path=Path(args.organization_input) if args.organization_input else None,
        output_dir=Path(args.output_dir),
    )

    print("HQE safe improved recorded-data paper runner execution plan pack completed.")
    print(f"Status: {report.status}")
    print(f"Phase 8 report found: {report.phase8_report_found}")
    print(f"Organization report found: {report.organization_report_found}")
    print(f"Accepted for future guarded runner module: {report.accepted_for_future_guarded_runner_module}")
    print(f"Plan items locked: {report.locked_plan_item_count}/{report.plan_item_count}")
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
