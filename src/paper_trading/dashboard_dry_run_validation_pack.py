"""
Dashboard dry run validation pack.

Module BBBB in the post-v1.0 Dashboard Sprint.

This module reads the dashboard smoke test plan pack and creates paper-only
future dashboard dry-run validation items.

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
class DashboardDryRunValidationItem:
    item_index: int
    item_name: str
    validation_area: str
    expected_result: str
    status: str
    safety_boundary: str


@dataclass(frozen=True)
class DashboardDryRunValidationIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class DashboardDryRunValidationReport:
    generated_at_utc: str
    dashboard_smoke_test_plan_path: str
    output_directory: str
    status: str
    ready_for_dashboard_sprint_close: bool
    selected_dataset_path: str
    safety_notice: str
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
    issues: list[DashboardDryRunValidationIssue]
    validation_items: list[DashboardDryRunValidationItem]
    smoke_step_names: list[str]
    page_names: list[str]
    component_names: list[str]
    section_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation dashboard dry run validation pack only. This pack "
        "creates future dashboard dry-run validation items from paper-only "
        "smoke-test plan evidence. It does not start a dashboard UI, does not "
        "import or require Streamlit at runtime, does not run backtests, does "
        "not calculate profitability, does not select a winning strategy, does "
        "not modify strategy logic, does not connect to brokers, does not "
        "request live market data, does not place real orders, does not use "
        "real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> DashboardDryRunValidationIssue:
    return DashboardDryRunValidationIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[DashboardDryRunValidationIssue]) -> str:
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


def _load_smoke_test_plan(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[DashboardDryRunValidationIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "dashboard_smoke_test_plan_pack_missing",
                1,
                f"Dashboard smoke test plan pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "dashboard_smoke_test_plan_pack_invalid_json",
                1,
                f"Dashboard smoke test plan pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "dashboard_smoke_test_plan_pack_invalid_shape",
                1,
                "Dashboard smoke test plan pack must be a JSON object.",
            )
        ]

    return payload, []


def _smoke_plan_issues(
    plan: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[DashboardDryRunValidationIssue]:
    if plan is None:
        return []

    issues: list[DashboardDryRunValidationIssue] = []

    status = str(plan.get("status") or "unknown").lower()
    ready = bool(plan.get("ready_for_future_streamlit_dry_run"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "dashboard_smoke_test_plan_pack_warn",
                1,
                "Dashboard smoke test plan pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "dashboard_smoke_test_plan_pack_not_pass",
                1,
                f"Dashboard smoke test plan pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "dashboard_smoke_test_plan_pack_not_ready",
                1,
                "Dashboard smoke test plan pack is not ready for future Streamlit dry run.",
            )
        )

    forbidden = _forbidden(plan)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "dashboard_smoke_test_plan_pack_forbidden_fields",
                len(forbidden),
                "Dashboard smoke test plan pack contains forbidden broker/order/real-money fields.",
            )
        )

    plan_issues = plan.get("issues")
    if isinstance(plan_issues, list):
        fail_count = sum(
            1
            for item in plan_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "dashboard_smoke_test_plan_pack_contains_fail_issues",
                    fail_count,
                    "Dashboard smoke test plan pack contains fail issues.",
                )
            )

    return issues


def _smoke_step_names(plan: Mapping[str, Any] | None) -> list[str]:
    if plan is None:
        return []

    raw_steps = plan.get("smoke_steps")
    if not isinstance(raw_steps, list):
        return []

    return sorted(
        {
            str(step.get("step_name") or "").strip().lower()
            for step in raw_steps
            if isinstance(step, Mapping) and str(step.get("step_name") or "").strip()
        }
    )


def _list_field(plan: Mapping[str, Any] | None, field_name: str) -> list[str]:
    if plan is None:
        return []

    raw_names = plan.get(field_name)
    if not isinstance(raw_names, list):
        return []

    return sorted({str(name).strip().lower() for name in raw_names if str(name).strip()})


def _readiness_issues(
    *,
    smoke_step_names: Sequence[str],
    page_names: Sequence[str],
    component_names: Sequence[str],
    section_names: Sequence[str],
) -> list[DashboardDryRunValidationIssue]:
    issues: list[DashboardDryRunValidationIssue] = []

    missing_steps = REQUIRED_SMOKE_STEPS - set(smoke_step_names)
    if missing_steps:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_dry_run_smoke_steps_missing",
                len(missing_steps),
                "Required dashboard dry-run smoke steps are missing.",
            )
        )

    missing_pages = REQUIRED_PAGES - set(page_names)
    if missing_pages:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_dry_run_pages_missing",
                len(missing_pages),
                "Required dashboard dry-run pages are missing.",
            )
        )

    missing_components = REQUIRED_COMPONENTS - set(component_names)
    if missing_components:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_dry_run_components_missing",
                len(missing_components),
                "Required dashboard dry-run components are missing.",
            )
        )

    missing_sections = REQUIRED_SECTIONS - set(section_names)
    if missing_sections:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_dry_run_sections_missing",
                len(missing_sections),
                "Required dashboard dry-run sections are missing.",
            )
        )

    return issues


def _validation_items() -> list[DashboardDryRunValidationItem]:
    raw_items = [
        (
            "plain_python_template_validation",
            "template",
            "Future app shell template can be checked without importing Streamlit.",
            "planned",
            "No Streamlit runtime dependency is required in this validation pack.",
        ),
        (
            "page_registry_validation",
            "pages",
            "Overview, evidence, and cost_review pages are present.",
            "planned",
            "No dashboard UI is started.",
        ),
        (
            "component_registry_validation",
            "components",
            "Required future dashboard components are present.",
            "planned",
            "No backtest execution is triggered.",
        ),
        (
            "section_registry_validation",
            "sections",
            "Required dashboard sections are present.",
            "planned",
            "No live market data is requested.",
        ),
        (
            "smoke_step_validation",
            "smoke_steps",
            "Required smoke-test steps are present.",
            "planned",
            "No broker order path is used.",
        ),
        (
            "safety_boundary_validation",
            "safety",
            "Safety panel confirms no broker orders, no live data, no real money.",
            "planned",
            "NIFTY option-buy paper plan only.",
        ),
        (
            "profitability_claim_guard_validation",
            "safety",
            "Dashboard dry-run wording remains not a profitability claim.",
            "planned",
            "No strategy winner or profit claim is produced.",
        ),
    ]

    return [
        DashboardDryRunValidationItem(
            item_index=index,
            item_name=item_name,
            validation_area=validation_area,
            expected_result=expected_result,
            status=status,
            safety_boundary=safety_boundary,
        )
        for index, (
            item_name,
            validation_area,
            expected_result,
            status,
            safety_boundary,
        ) in enumerate(raw_items, start=1)
    ]


def build_dashboard_dry_run_validation_report(
    *,
    dashboard_smoke_test_plan_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> DashboardDryRunValidationReport:
    plan, load_issues = _load_smoke_test_plan(dashboard_smoke_test_plan_path)

    issues: list[DashboardDryRunValidationIssue] = []
    issues.extend(load_issues)
    issues.extend(_smoke_plan_issues(plan, allow_warnings=allow_warnings))

    smoke_step_names = _smoke_step_names(plan)
    page_names = _list_field(plan, "page_names")
    component_names = _list_field(plan, "component_names")
    section_names = _list_field(plan, "section_names")

    issues.extend(
        _readiness_issues(
            smoke_step_names=smoke_step_names,
            page_names=page_names,
            component_names=component_names,
            section_names=section_names,
        )
    )

    validation_items = _validation_items()
    status = _status(issues)

    return DashboardDryRunValidationReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dashboard_smoke_test_plan_path=str(dashboard_smoke_test_plan_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_dashboard_sprint_close=status in {"pass", "warn"},
        selected_dataset_path=str((plan or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        validation_item_count=len(validation_items),
        smoke_step_count=len(smoke_step_names),
        page_count=len(page_names),
        component_count=len(component_names),
        section_count=len(section_names),
        completed_total_before_module=79,
        completed_total_after_module=80,
        phase_2_pending_before_module=2,
        phase_2_pending_after_module=1,
        full_hqe_product_estimate_after_module="72-77%",
        issues=issues,
        validation_items=validation_items,
        smoke_step_names=smoke_step_names,
        page_names=page_names,
        component_names=component_names,
        section_names=section_names,
    )


def write_dashboard_dry_run_validation_report(
    report: DashboardDryRunValidationReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    validation_json = output_dir / "dashboard_dry_run_validation_pack.json"
    validation_txt = output_dir / "dashboard_dry_run_validation_pack.txt"
    validation_csv = output_dir / "dashboard_dry_run_validation_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["validation_items"] = [asdict(item) for item in report.validation_items]
    validation_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with validation_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_index",
                "item_name",
                "validation_area",
                "expected_result",
                "status",
                "safety_boundary",
            ]
        )
        for item in report.validation_items:
            writer.writerow(
                [
                    item.item_index,
                    item.item_name,
                    item.validation_area,
                    item.expected_result,
                    item.status,
                    item.safety_boundary,
                ]
            )

    lines = [
        "HQE Dashboard Dry Run Validation Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for dashboard sprint close: {report.ready_for_dashboard_sprint_close}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Validation items: {report.validation_item_count}",
        f"Smoke steps: {report.smoke_step_count}",
        f"Pages: {report.page_count}",
        f"Components: {report.component_count}",
        f"Sections: {report.section_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Phase 1 pending after Module UUU: 0 modules.",
        f"- Completed total before Module BBBB: {report.completed_total_before_module} modules.",
        f"- Completed total after Module BBBB: {report.completed_total_after_module} modules.",
        f"- Phase 2 pending before Module BBBB: {report.phase_2_pending_before_module} modules.",
        f"- Phase 2 pending after Module BBBB: {report.phase_2_pending_after_module} module.",
        f"- Full HQE product estimate after Module BBBB: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Dry-run validation items:",
    ]

    for item in report.validation_items:
        lines.append(
            (
                f"{item.item_index}. {item.item_name} [{item.validation_area}] "
                f"expected={item.expected_result}"
            )
        )

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
        lines.append("- PASS: Dashboard dry-run validation is ready for dashboard sprint close.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {validation_json}",
            f"- {validation_txt}",
            f"- {validation_csv}",
            f"- {manifest_json}",
        ]
    )
    validation_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "dashboard_dry_run_validation_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_dashboard_sprint_close": report.ready_for_dashboard_sprint_close,
        "selected_dataset_path": report.selected_dataset_path,
        "validation_item_count": report.validation_item_count,
        "smoke_step_count": report.smoke_step_count,
        "page_count": report.page_count,
        "component_count": report.component_count,
        "section_count": report.section_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_2_pending_after_module": report.phase_2_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "safety_notice": report.safety_notice,
        "outputs": {
            "dashboard_dry_run_validation_pack_json": str(validation_json),
            "dashboard_dry_run_validation_pack_txt": str(validation_txt),
            "dashboard_dry_run_validation_items_csv": str(validation_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "dashboard_dry_run_validation_pack_json": validation_json,
        "dashboard_dry_run_validation_pack_txt": validation_txt,
        "dashboard_dry_run_validation_items_csv": validation_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_dashboard_dry_run_validation_report(
    *,
    dashboard_smoke_test_plan_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[DashboardDryRunValidationReport, dict[str, Path]]:
    report = build_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=dashboard_smoke_test_plan_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_dashboard_dry_run_validation_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dashboard dry run validation pack."
    )
    parser.add_argument(
        "--dashboard-smoke-test-plan",
        default=(
            "reports/paper_trading/"
            "dashboard_smoke_test_plan_pack/"
            "dashboard_smoke_test_plan_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/dashboard_dry_run_validation_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=Path(args.dashboard_smoke_test_plan),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE dashboard dry run validation pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for dashboard sprint close: {report.ready_for_dashboard_sprint_close}")
    print(f"Validation items: {report.validation_item_count}")
    print(f"Dashboard dry run validation: {outputs['dashboard_dry_run_validation_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
