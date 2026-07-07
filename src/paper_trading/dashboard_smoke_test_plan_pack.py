"""
Dashboard smoke test plan pack.

Module AAAA in the post-v1.0 Dashboard Sprint.

This module reads the dashboard app shell pack and creates a paper-only future
dashboard smoke test plan.

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


REQUIRED_PAGES = {"overview", "evidence", "cost_review"}
REQUIRED_SECTIONS = {"overview", "progress", "inputs", "mode_evidence", "cost_review", "safety"}
REQUIRED_COMPONENTS = {
    "overview_header",
    "progress_card_grid",
    "input_evidence_table",
    "mode_evidence_table",
    "cost_review_table",
    "safety_boundary_panel",
}

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
class DashboardSmokeTestStep:
    step_index: int
    step_name: str
    page_name: str
    expected_result: str
    status: str
    safety_check: str


@dataclass(frozen=True)
class DashboardSmokeTestPlanIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class DashboardSmokeTestPlanReport:
    generated_at_utc: str
    dashboard_app_shell_path: str
    output_directory: str
    status: str
    ready_for_future_streamlit_dry_run: bool
    selected_dataset_path: str
    safety_notice: str
    smoke_step_count: int
    page_count: int
    component_count: int
    section_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_2_pending_before_module: int
    phase_2_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    issues: list[DashboardSmokeTestPlanIssue]
    smoke_steps: list[DashboardSmokeTestStep]
    page_names: list[str]
    component_names: list[str]
    section_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation dashboard smoke test plan pack only. This pack "
        "creates future dashboard smoke-test steps from paper-only app shell "
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
) -> DashboardSmokeTestPlanIssue:
    return DashboardSmokeTestPlanIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[DashboardSmokeTestPlanIssue]) -> str:
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


def _load_app_shell_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[DashboardSmokeTestPlanIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "dashboard_app_shell_pack_missing",
                1,
                f"Dashboard app shell pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "dashboard_app_shell_pack_invalid_json",
                1,
                f"Dashboard app shell pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "dashboard_app_shell_pack_invalid_shape",
                1,
                "Dashboard app shell pack must be a JSON object.",
            )
        ]

    return payload, []


def _app_shell_issues(
    shell: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[DashboardSmokeTestPlanIssue]:
    if shell is None:
        return []

    issues: list[DashboardSmokeTestPlanIssue] = []

    status = str(shell.get("status") or "unknown").lower()
    ready = bool(shell.get("ready_for_future_dashboard_smoke_test"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "dashboard_app_shell_pack_warn",
                1,
                "Dashboard app shell pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "dashboard_app_shell_pack_not_pass",
                1,
                f"Dashboard app shell pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "dashboard_app_shell_pack_not_ready",
                1,
                "Dashboard app shell pack is not ready for future dashboard smoke test.",
            )
        )

    forbidden = _forbidden(shell)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "dashboard_app_shell_pack_forbidden_fields",
                len(forbidden),
                "Dashboard app shell pack contains forbidden broker/order/real-money fields.",
            )
        )

    shell_issues = shell.get("issues")
    if isinstance(shell_issues, list):
        fail_count = sum(
            1
            for item in shell_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "dashboard_app_shell_pack_contains_fail_issues",
                    fail_count,
                    "Dashboard app shell pack contains fail issues.",
                )
            )

    return issues


def _page_names(shell: Mapping[str, Any] | None) -> list[str]:
    if shell is None:
        return []

    raw_pages = shell.get("pages")
    if not isinstance(raw_pages, list):
        return []

    return sorted(
        {
            str(page.get("page_name") or "").strip().lower()
            for page in raw_pages
            if isinstance(page, Mapping) and str(page.get("page_name") or "").strip()
        }
    )


def _component_names(shell: Mapping[str, Any] | None) -> list[str]:
    if shell is None:
        return []

    raw_names = shell.get("component_names")
    if not isinstance(raw_names, list):
        return []

    return sorted({str(name).strip().lower() for name in raw_names if str(name).strip()})


def _section_names(shell: Mapping[str, Any] | None) -> list[str]:
    if shell is None:
        return []

    raw_names = shell.get("section_names")
    if not isinstance(raw_names, list):
        return []

    return sorted({str(name).strip().lower() for name in raw_names if str(name).strip()})


def _readiness_issues(
    *,
    page_names: Sequence[str],
    component_names: Sequence[str],
    section_names: Sequence[str],
) -> list[DashboardSmokeTestPlanIssue]:
    issues: list[DashboardSmokeTestPlanIssue] = []

    missing_pages = REQUIRED_PAGES - set(page_names)
    if missing_pages:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_smoke_test_pages_missing",
                len(missing_pages),
                "Required dashboard smoke-test pages are missing.",
            )
        )

    missing_components = REQUIRED_COMPONENTS - set(component_names)
    if missing_components:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_smoke_test_components_missing",
                len(missing_components),
                "Required dashboard smoke-test components are missing.",
            )
        )

    missing_sections = REQUIRED_SECTIONS - set(section_names)
    if missing_sections:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_smoke_test_sections_missing",
                len(missing_sections),
                "Required dashboard smoke-test sections are missing.",
            )
        )

    return issues


def _smoke_steps() -> list[DashboardSmokeTestStep]:
    raw_steps = [
        (
            "load_app_shell_template",
            "overview",
            "Template file can be imported as a plain Python module in future dry run.",
            "planned",
            "No Streamlit runtime import is required by the generated template.",
        ),
        (
            "verify_overview_page",
            "overview",
            "Overview page registry includes overview, progress, and safety sections.",
            "planned",
            "No live market data or broker connection.",
        ),
        (
            "verify_evidence_page",
            "evidence",
            "Evidence page registry includes inputs and mode_evidence sections.",
            "planned",
            "Paper-only evidence paths only.",
        ),
        (
            "verify_cost_review_page",
            "cost_review",
            "Cost review page registry includes cost_review and safety sections.",
            "planned",
            "No profitability claim.",
        ),
        (
            "verify_safety_boundary",
            "overview",
            "Safety text displays no broker orders, no live market data, no real money.",
            "planned",
            "NIFTY option-buy paper plan only.",
        ),
        (
            "verify_no_execution_hooks",
            "overview",
            "No order placement, broker, live feed, or real-money execution hook exists.",
            "planned",
            "Live execution remains out of scope.",
        ),
    ]

    return [
        DashboardSmokeTestStep(
            step_index=index,
            step_name=step_name,
            page_name=page_name,
            expected_result=expected_result,
            status=status,
            safety_check=safety_check,
        )
        for index, (step_name, page_name, expected_result, status, safety_check) in enumerate(
            raw_steps,
            start=1,
        )
    ]


def build_dashboard_smoke_test_plan_report(
    *,
    dashboard_app_shell_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> DashboardSmokeTestPlanReport:
    shell, load_issues = _load_app_shell_pack(dashboard_app_shell_path)

    issues: list[DashboardSmokeTestPlanIssue] = []
    issues.extend(load_issues)
    issues.extend(_app_shell_issues(shell, allow_warnings=allow_warnings))

    page_names = _page_names(shell)
    component_names = _component_names(shell)
    section_names = _section_names(shell)

    issues.extend(
        _readiness_issues(
            page_names=page_names,
            component_names=component_names,
            section_names=section_names,
        )
    )

    smoke_steps = _smoke_steps()
    status = _status(issues)

    return DashboardSmokeTestPlanReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dashboard_app_shell_path=str(dashboard_app_shell_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_streamlit_dry_run=status in {"pass", "warn"},
        selected_dataset_path=str((shell or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        smoke_step_count=len(smoke_steps),
        page_count=len(page_names),
        component_count=len(component_names),
        section_count=len(section_names),
        completed_total_before_module=78,
        completed_total_after_module=79,
        phase_2_pending_before_module=3,
        phase_2_pending_after_module=2,
        full_hqe_product_estimate_after_module="71-76%",
        issues=issues,
        smoke_steps=smoke_steps,
        page_names=page_names,
        component_names=component_names,
        section_names=section_names,
    )


def write_dashboard_smoke_test_plan_report(
    report: DashboardSmokeTestPlanReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_json = output_dir / "dashboard_smoke_test_plan_pack.json"
    plan_txt = output_dir / "dashboard_smoke_test_plan_pack.txt"
    steps_csv = output_dir / "dashboard_smoke_test_steps.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["smoke_steps"] = [asdict(step) for step in report.smoke_steps]
    plan_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with steps_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "step_index",
                "step_name",
                "page_name",
                "expected_result",
                "status",
                "safety_check",
            ]
        )
        for step in report.smoke_steps:
            writer.writerow(
                [
                    step.step_index,
                    step.step_name,
                    step.page_name,
                    step.expected_result,
                    step.status,
                    step.safety_check,
                ]
            )

    lines = [
        "HQE Dashboard Smoke Test Plan Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future Streamlit dry run: {report.ready_for_future_streamlit_dry_run}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Smoke test steps: {report.smoke_step_count}",
        f"Pages: {report.page_count}",
        f"Components: {report.component_count}",
        f"Sections: {report.section_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Phase 1 pending after Module UUU: 0 modules.",
        f"- Completed total before Module AAAA: {report.completed_total_before_module} modules.",
        f"- Completed total after Module AAAA: {report.completed_total_after_module} modules.",
        f"- Phase 2 pending before Module AAAA: {report.phase_2_pending_before_module} modules.",
        f"- Phase 2 pending after Module AAAA: {report.phase_2_pending_after_module} modules.",
        f"- Full HQE product estimate after Module AAAA: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Smoke test steps:",
    ]

    for step in report.smoke_steps:
        lines.append(
            (
                f"{step.step_index}. {step.step_name} -> {step.page_name} "
                f"[{step.status}] expected={step.expected_result}"
            )
        )

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
        lines.append("- PASS: Dashboard smoke test plan is ready for future Streamlit dry run.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {plan_json}",
            f"- {plan_txt}",
            f"- {steps_csv}",
            f"- {manifest_json}",
        ]
    )
    plan_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "dashboard_smoke_test_plan_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_streamlit_dry_run": report.ready_for_future_streamlit_dry_run,
        "selected_dataset_path": report.selected_dataset_path,
        "smoke_step_count": report.smoke_step_count,
        "page_count": report.page_count,
        "component_count": report.component_count,
        "section_count": report.section_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_2_pending_after_module": report.phase_2_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "safety_notice": report.safety_notice,
        "outputs": {
            "dashboard_smoke_test_plan_pack_json": str(plan_json),
            "dashboard_smoke_test_plan_pack_txt": str(plan_txt),
            "dashboard_smoke_test_steps_csv": str(steps_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "dashboard_smoke_test_plan_pack_json": plan_json,
        "dashboard_smoke_test_plan_pack_txt": plan_txt,
        "dashboard_smoke_test_steps_csv": steps_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_dashboard_smoke_test_plan_report(
    *,
    dashboard_app_shell_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[DashboardSmokeTestPlanReport, dict[str, Path]]:
    report = build_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=dashboard_app_shell_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_dashboard_smoke_test_plan_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dashboard smoke test plan pack."
    )
    parser.add_argument(
        "--dashboard-app-shell",
        default=(
            "reports/paper_trading/"
            "dashboard_app_shell_pack/"
            "dashboard_app_shell_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/dashboard_smoke_test_plan_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=Path(args.dashboard_app_shell),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE dashboard smoke test plan pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future Streamlit dry run: {report.ready_for_future_streamlit_dry_run}")
    print(f"Smoke test steps: {report.smoke_step_count}")
    print(f"Dashboard smoke test plan: {outputs['dashboard_smoke_test_plan_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
