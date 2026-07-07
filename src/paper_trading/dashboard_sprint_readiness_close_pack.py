"""
Dashboard sprint readiness close pack.

Module CCCC closes the post-v1.0 Dashboard Sprint.

This module reads the dashboard dry run validation pack and creates a paper-only
Dashboard Sprint readiness close report.

It does not start a dashboard UI, does not import or require Streamlit at
runtime, does not run backtests, does not calculate profitability, does not
select a winning strategy, does not modify strategy logic, does not connect to
brokers, does not request live market data, does not place real orders, does
not use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_VALIDATION_ITEMS = {
    "plain_python_template_validation",
    "page_registry_validation",
    "component_registry_validation",
    "section_registry_validation",
    "smoke_step_validation",
    "safety_boundary_validation",
    "profitability_claim_guard_validation",
}

REQUIRED_SMOKE_STEPS = {
    "load_app_shell_template",
    "verify_overview_page",
    "verify_evidence_page",
    "verify_cost_review_page",
    "verify_safety_boundary",
    "verify_no_execution_hooks",
}

REQUIRED_PAGES = {"overview", "evidence", "cost_review"}
REQUIRED_COMPONENTS = {
    "overview_header",
    "progress_card_grid",
    "input_evidence_table",
    "mode_evidence_table",
    "cost_review_table",
    "safety_boundary_panel",
}
REQUIRED_SECTIONS = {"overview", "progress", "inputs", "mode_evidence", "cost_review", "safety"}

FORBIDDEN_KEYS = {
    "broker",
    "broker_order_id",
    "exchange_order_id",
    "live_order",
    "order",
    "order_id",
    "orders",
    "real_money",
}


@dataclass(frozen=True)
class DashboardSprintCloseChecklistItem:
    item_index: int
    item_name: str
    status: str
    evidence: str
    next_instruction: str


@dataclass(frozen=True)
class DashboardSprintCloseIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class DashboardSprintReadinessCloseReport:
    generated_at_utc: str
    dashboard_dry_run_validation_path: str
    output_directory: str
    status: str
    dashboard_sprint_closed: bool
    ready_for_recorded_backtest_review_workflow: bool
    selected_dataset_path: str
    safety_notice: str
    checklist_item_count: int
    validation_item_count: int
    smoke_step_count: int
    page_count: int
    component_count: int
    section_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_2_pending_before_module: int
    phase_2_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    recommended_next_phase: str
    issues: list[DashboardSprintCloseIssue]
    checklist: list[DashboardSprintCloseChecklistItem]
    validation_item_names: list[str]
    smoke_step_names: list[str]
    page_names: list[str]
    component_names: list[str]
    section_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation dashboard sprint readiness close pack only. This pack "
        "closes the Dashboard Sprint from paper-only dry-run validation "
        "evidence. It does not start a dashboard UI, does not import or require "
        "Streamlit at runtime, does not run backtests, does not calculate "
        "profitability, does not select a winning strategy, does not modify "
        "strategy logic, does not connect to brokers, does not request live "
        "market data, does not place real orders, does not use real money, or "
        "prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> DashboardSprintCloseIssue:
    return DashboardSprintCloseIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[DashboardSprintCloseIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _load_dry_run_validation(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[DashboardSprintCloseIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "dashboard_dry_run_validation_pack_missing",
                1,
                f"Dashboard dry run validation pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "dashboard_dry_run_validation_pack_invalid_json",
                1,
                f"Dashboard dry run validation pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "dashboard_dry_run_validation_pack_invalid_shape",
                1,
                "Dashboard dry run validation pack must be a JSON object.",
            )
        ]

    return payload, []


def _dry_run_validation_issues(
    validation: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[DashboardSprintCloseIssue]:
    if validation is None:
        return []

    issues: list[DashboardSprintCloseIssue] = []

    status = str(validation.get("status") or "unknown").lower()
    ready = bool(validation.get("ready_for_dashboard_sprint_close"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "dashboard_dry_run_validation_pack_warn",
                1,
                "Dashboard dry run validation pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "dashboard_dry_run_validation_pack_not_pass",
                1,
                f"Dashboard dry run validation pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "dashboard_dry_run_validation_pack_not_ready",
                1,
                "Dashboard dry run validation pack is not ready for dashboard sprint close.",
            )
        )

    forbidden = _forbidden(validation)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "dashboard_dry_run_validation_pack_forbidden_fields",
                len(forbidden),
                "Dashboard dry run validation pack contains forbidden broker/order/real-money fields.",
            )
        )

    validation_issues = validation.get("issues")
    if isinstance(validation_issues, list):
        fail_count = sum(
            1
            for item in validation_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "dashboard_dry_run_validation_pack_contains_fail_issues",
                    fail_count,
                    "Dashboard dry run validation pack contains fail issues.",
                )
            )

    return issues


def _validation_item_names(validation: Mapping[str, Any] | None) -> list[str]:
    if validation is None:
        return []

    raw_items = validation.get("validation_items")
    if not isinstance(raw_items, list):
        return []

    return sorted(
        {
            str(item.get("item_name") or "").strip().lower()
            for item in raw_items
            if isinstance(item, Mapping) and str(item.get("item_name") or "").strip()
        }
    )


def _list_field(validation: Mapping[str, Any] | None, field_name: str) -> list[str]:
    if validation is None:
        return []

    raw_names = validation.get(field_name)
    if not isinstance(raw_names, list):
        return []

    return sorted({str(name).strip().lower() for name in raw_names if str(name).strip()})


def _readiness_issues(
    *,
    validation_item_names: Sequence[str],
    smoke_step_names: Sequence[str],
    page_names: Sequence[str],
    component_names: Sequence[str],
    section_names: Sequence[str],
) -> list[DashboardSprintCloseIssue]:
    issues: list[DashboardSprintCloseIssue] = []

    missing_validation_items = REQUIRED_VALIDATION_ITEMS - set(validation_item_names)
    if missing_validation_items:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_close_validation_items_missing",
                len(missing_validation_items),
                "Required dashboard close validation items are missing.",
            )
        )

    missing_smoke_steps = REQUIRED_SMOKE_STEPS - set(smoke_step_names)
    if missing_smoke_steps:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_close_smoke_steps_missing",
                len(missing_smoke_steps),
                "Required dashboard close smoke steps are missing.",
            )
        )

    missing_pages = REQUIRED_PAGES - set(page_names)
    if missing_pages:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_close_pages_missing",
                len(missing_pages),
                "Required dashboard close pages are missing.",
            )
        )

    missing_components = REQUIRED_COMPONENTS - set(component_names)
    if missing_components:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_close_components_missing",
                len(missing_components),
                "Required dashboard close components are missing.",
            )
        )

    missing_sections = REQUIRED_SECTIONS - set(section_names)
    if missing_sections:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_close_sections_missing",
                len(missing_sections),
                "Required dashboard close sections are missing.",
            )
        )

    return issues


def _checklist(status: str) -> list[DashboardSprintCloseChecklistItem]:
    checklist_status = "closed" if status in {"pass", "warn"} else "blocked"

    raw_items = [
        (
            "dashboard_input_index",
            checklist_status,
            "Module VVV created dashboard input index foundation.",
            "Use indexed evidence paths for future recorded-data review.",
        ),
        (
            "dashboard_overview_snapshot",
            checklist_status,
            "Module WWW created static overview cards.",
            "Use cards for future operator summary layout.",
        ),
        (
            "dashboard_section_registry",
            checklist_status,
            "Module XXX created section registry and card routes.",
            "Use sections as future dashboard navigation boundaries.",
        ),
        (
            "dashboard_component_scaffold",
            checklist_status,
            "Module YYY created future component definitions.",
            "Use components as UI build blueprint only.",
        ),
        (
            "dashboard_app_shell",
            checklist_status,
            "Module ZZZ created future app shell template.",
            "Do not start Streamlit until operator explicitly chooses dry run.",
        ),
        (
            "dashboard_smoke_test_plan",
            checklist_status,
            "Module AAAA created future smoke-test steps.",
            "Use smoke plan before any dashboard runtime attempt.",
        ),
        (
            "dashboard_dry_run_validation",
            checklist_status,
            "Module BBBB created future dry-run validation items.",
            "Use validation pack before Dashboard Sprint close acceptance.",
        ),
        (
            "safety_boundary",
            checklist_status,
            "No broker orders, no live market data, no real money, no profitability claim.",
            "Next recorded-data backtest review must remain paper-only.",
        ),
    ]

    return [
        DashboardSprintCloseChecklistItem(
            item_index=index,
            item_name=item_name,
            status=item_status,
            evidence=evidence,
            next_instruction=next_instruction,
        )
        for index, (item_name, item_status, evidence, next_instruction) in enumerate(
            raw_items,
            start=1,
        )
    ]


def build_dashboard_sprint_readiness_close_report(
    *,
    dashboard_dry_run_validation_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> DashboardSprintReadinessCloseReport:
    validation, load_issues = _load_dry_run_validation(dashboard_dry_run_validation_path)

    issues: list[DashboardSprintCloseIssue] = []
    issues.extend(load_issues)
    issues.extend(_dry_run_validation_issues(validation, allow_warnings=allow_warnings))

    validation_item_names = _validation_item_names(validation)
    smoke_step_names = _list_field(validation, "smoke_step_names")
    page_names = _list_field(validation, "page_names")
    component_names = _list_field(validation, "component_names")
    section_names = _list_field(validation, "section_names")

    issues.extend(
        _readiness_issues(
            validation_item_names=validation_item_names,
            smoke_step_names=smoke_step_names,
            page_names=page_names,
            component_names=component_names,
            section_names=section_names,
        )
    )

    status = _status(issues)
    checklist = _checklist(status)

    return DashboardSprintReadinessCloseReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dashboard_dry_run_validation_path=str(dashboard_dry_run_validation_path),
        output_directory=str(output_dir),
        status=status,
        dashboard_sprint_closed=status in {"pass", "warn"},
        ready_for_recorded_backtest_review_workflow=status in {"pass", "warn"},
        selected_dataset_path=str((validation or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        checklist_item_count=len(checklist),
        validation_item_count=len(validation_item_names),
        smoke_step_count=len(smoke_step_names),
        page_count=len(page_names),
        component_count=len(component_names),
        section_count=len(section_names),
        completed_total_before_module=80,
        completed_total_after_module=81,
        phase_2_pending_before_module=1,
        phase_2_pending_after_module=0,
        full_hqe_product_estimate_after_module="73-78%",
        recommended_next_phase=(
            "Begin recorded-data paper backtest review workflow only after operator "
            "confirms dataset and remains inside paper-only safety boundary."
        ),
        issues=issues,
        checklist=checklist,
        validation_item_names=validation_item_names,
        smoke_step_names=smoke_step_names,
        page_names=page_names,
        component_names=component_names,
        section_names=section_names,
    )


def write_dashboard_sprint_readiness_close_report(
    report: DashboardSprintReadinessCloseReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    close_json = output_dir / "dashboard_sprint_readiness_close_pack.json"
    close_txt = output_dir / "dashboard_sprint_readiness_close_pack.txt"
    checklist_csv = output_dir / "dashboard_sprint_close_checklist.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["checklist"] = [asdict(item) for item in report.checklist]
    close_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with checklist_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "item_name",
                "status",
                "evidence",
                "next_instruction",
            ]
        )
        for item in report.checklist:
            writer.writerow(
                [
                    item.item_index,
                    item.item_name,
                    item.status,
                    item.evidence,
                    item.next_instruction,
                ]
            )

    lines = [
        "HQE Dashboard Sprint Readiness Close Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Dashboard Sprint closed: {report.dashboard_sprint_closed}",
        f"Ready for recorded-data backtest review workflow: {report.ready_for_recorded_backtest_review_workflow}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Checklist items: {report.checklist_item_count}",
        f"Validation items: {report.validation_item_count}",
        f"Smoke steps: {report.smoke_step_count}",
        f"Pages: {report.page_count}",
        f"Components: {report.component_count}",
        f"Sections: {report.section_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Post-v1.0 Phase 1: Real Backtest Usage Sprint complete.",
        f"- Completed total before Module CCCC: {report.completed_total_before_module} modules.",
        f"- Completed total after Module CCCC: {report.completed_total_after_module} modules.",
        f"- Phase 2 pending before Module CCCC: {report.phase_2_pending_before_module} module.",
        f"- Phase 2 pending after Module CCCC: {report.phase_2_pending_after_module} modules.",
        f"- Full HQE product estimate after Module CCCC: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Recommended next phase:",
        report.recommended_next_phase,
        "",
        "Close checklist:",
    ]

    for item in report.checklist:
        lines.append(
            (
                f"{item.item_index}. {item.item_name} [{item.status}] - "
                f"{item.evidence} Next={item.next_instruction}"
            )
        )

    lines.extend(["", "Validation items:"])
    for item_name in report.validation_item_names:
        lines.append(f"- {item_name}")

    lines.extend(["", "Smoke steps:"])
    for step_name in report.smoke_step_names:
        lines.append(f"- {step_name}")

    lines.extend(["", "Pages:"])
    for page_name in report.page_names:
        lines.append(f"- {page_name}")

    lines.extend(["", "Components:"])
    for component_name in report.component_names:
        lines.append(f"- {component_name}")

    lines.extend(["", "Sections:"])
    for section_name in report.section_names:
        lines.append(f"- {section_name}")

    lines.extend(
        [
            "",
            "Safety:",
            "- This pack does not start a dashboard UI.",
            "- This pack does not import or require Streamlit at runtime.",
            "- This pack does not run backtests.",
            "- This pack does not calculate profitability.",
            "- This pack does not select a winning strategy.",
            "- This report is not a profitability claim.",
            "- LONG = CE BUY paper plan only.",
            "- SHORT = PE BUY paper plan only.",
            "- NEUTRAL = no trade.",
            "- No option selling.",
            "- No broker orders.",
            "- No live market data.",
            "- No real money.",
            "",
            "Issues:",
        ]
    )

    if not report.issues:
        lines.append("- PASS: Dashboard Sprint is closed as a paper-only evidence workflow.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {close_json}",
            f"- {close_txt}",
            f"- {checklist_csv}",
            f"- {manifest_json}",
        ]
    )
    close_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "dashboard_sprint_readiness_close_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "dashboard_sprint_closed": report.dashboard_sprint_closed,
        "ready_for_recorded_backtest_review_workflow": report.ready_for_recorded_backtest_review_workflow,
        "selected_dataset_path": report.selected_dataset_path,
        "checklist_item_count": report.checklist_item_count,
        "validation_item_count": report.validation_item_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_2_pending_after_module": report.phase_2_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "recommended_next_phase": report.recommended_next_phase,
        "safety_notice": report.safety_notice,
        "outputs": {
            "dashboard_sprint_readiness_close_pack_json": str(close_json),
            "dashboard_sprint_readiness_close_pack_txt": str(close_txt),
            "dashboard_sprint_close_checklist_csv": str(checklist_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "dashboard_sprint_readiness_close_pack_json": close_json,
        "dashboard_sprint_readiness_close_pack_txt": close_txt,
        "dashboard_sprint_close_checklist_csv": checklist_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_dashboard_sprint_readiness_close_report(
    *,
    dashboard_dry_run_validation_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[DashboardSprintReadinessCloseReport, dict[str, Path]]:
    report = build_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=dashboard_dry_run_validation_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_dashboard_sprint_readiness_close_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dashboard sprint readiness close pack."
    )
    parser.add_argument(
        "--dashboard-dry-run-validation",
        default=(
            "reports/paper_trading/"
            "dashboard_dry_run_validation_pack/"
            "dashboard_dry_run_validation_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/dashboard_sprint_readiness_close_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=Path(args.dashboard_dry_run_validation),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE dashboard sprint readiness close pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Dashboard Sprint closed: {report.dashboard_sprint_closed}")
    print(f"Ready for recorded-data backtest review workflow: {report.ready_for_recorded_backtest_review_workflow}")
    print(f"Dashboard sprint close: {outputs['dashboard_sprint_readiness_close_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
