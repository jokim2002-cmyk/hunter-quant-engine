"""
Dashboard app shell pack.

Module ZZZ in the post-v1.0 Dashboard Sprint.

This module reads the dashboard component scaffold pack and creates a paper-only
future Streamlit app shell template plus page registry.

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


REQUIRED_COMPONENTS = {
    "overview_header",
    "progress_card_grid",
    "input_evidence_table",
    "mode_evidence_table",
    "cost_review_table",
    "safety_boundary_panel",
}

REQUIRED_SECTIONS = {
    "overview",
    "progress",
    "inputs",
    "mode_evidence",
    "cost_review",
    "safety",
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
class DashboardAppPage:
    page_index: int
    page_name: str
    title: str
    sections: list[str]
    status: str
    purpose: str


@dataclass(frozen=True)
class DashboardAppShellIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class DashboardAppShellReport:
    generated_at_utc: str
    dashboard_component_scaffold_path: str
    output_directory: str
    status: str
    ready_for_future_dashboard_smoke_test: bool
    selected_dataset_path: str
    safety_notice: str
    page_count: int
    component_count: int
    section_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_2_pending_before_module: int
    phase_2_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    issues: list[DashboardAppShellIssue]
    pages: list[DashboardAppPage]
    component_names: list[str]
    section_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation dashboard app shell pack only. This pack creates a "
        "future Streamlit app shell template and page registry from paper-only "
        "component definitions. It does not start a dashboard UI, does not "
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
) -> DashboardAppShellIssue:
    return DashboardAppShellIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[DashboardAppShellIssue]) -> str:
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


def _load_component_scaffold(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[DashboardAppShellIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "dashboard_component_scaffold_pack_missing",
                1,
                f"Dashboard component scaffold pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "dashboard_component_scaffold_pack_invalid_json",
                1,
                f"Dashboard component scaffold pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "dashboard_component_scaffold_pack_invalid_shape",
                1,
                "Dashboard component scaffold pack must be a JSON object.",
            )
        ]

    return payload, []


def _component_scaffold_issues(
    scaffold: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[DashboardAppShellIssue]:
    if scaffold is None:
        return []

    issues: list[DashboardAppShellIssue] = []

    status = str(scaffold.get("status") or "unknown").lower()
    ready = bool(scaffold.get("ready_for_future_streamlit_app_shell"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "dashboard_component_scaffold_pack_warn",
                1,
                "Dashboard component scaffold pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "dashboard_component_scaffold_pack_not_pass",
                1,
                f"Dashboard component scaffold pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "dashboard_component_scaffold_pack_not_ready",
                1,
                "Dashboard component scaffold pack is not ready for future Streamlit app shell.",
            )
        )

    forbidden = _forbidden(scaffold)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "dashboard_component_scaffold_pack_forbidden_fields",
                len(forbidden),
                "Dashboard component scaffold pack contains forbidden broker/order/real-money fields.",
            )
        )

    scaffold_issues = scaffold.get("issues")
    if isinstance(scaffold_issues, list):
        fail_count = sum(
            1
            for item in scaffold_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "dashboard_component_scaffold_pack_contains_fail_issues",
                    fail_count,
                    "Dashboard component scaffold pack contains fail issues.",
                )
            )

    return issues


def _component_names(scaffold: Mapping[str, Any] | None) -> list[str]:
    if scaffold is None:
        return []

    raw_components = scaffold.get("components")
    if not isinstance(raw_components, list):
        return []

    return sorted(
        {
            str(component.get("component_name") or "").strip().lower()
            for component in raw_components
            if isinstance(component, Mapping)
            and str(component.get("component_name") or "").strip()
        }
    )


def _section_names(scaffold: Mapping[str, Any] | None) -> list[str]:
    if scaffold is None:
        return []

    raw_names = scaffold.get("section_names")
    if isinstance(raw_names, list):
        return sorted({str(name).strip().lower() for name in raw_names if str(name).strip()})

    raw_components = scaffold.get("components")
    if not isinstance(raw_components, list):
        return []

    return sorted(
        {
            str(component.get("section_name") or "").strip().lower()
            for component in raw_components
            if isinstance(component, Mapping)
            and str(component.get("section_name") or "").strip()
        }
    )


def _component_and_section_issues(
    *,
    component_names: Sequence[str],
    section_names: Sequence[str],
) -> list[DashboardAppShellIssue]:
    issues: list[DashboardAppShellIssue] = []

    missing_components = REQUIRED_COMPONENTS - set(component_names)
    if missing_components:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_app_shell_components_missing",
                len(missing_components),
                "Required dashboard app shell components are missing.",
            )
        )

    missing_sections = REQUIRED_SECTIONS - set(section_names)
    if missing_sections:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_app_shell_sections_missing",
                len(missing_sections),
                "Required dashboard app shell sections are missing.",
            )
        )

    return issues


def _pages() -> list[DashboardAppPage]:
    raw_pages = [
        (
            "overview",
            "Overview",
            ["overview", "progress", "safety"],
            "ready",
            "Future landing page with progress and safety cards.",
        ),
        (
            "evidence",
            "Evidence",
            ["inputs", "mode_evidence"],
            "planned",
            "Future evidence page with input and mode evidence tables.",
        ),
        (
            "cost_review",
            "Cost Review",
            ["cost_review", "safety"],
            "planned",
            "Future cost/slippage review page without profitability claims.",
        ),
    ]

    return [
        DashboardAppPage(
            page_index=index,
            page_name=page_name,
            title=title,
            sections=sections,
            status=status,
            purpose=purpose,
        )
        for index, (page_name, title, sections, status, purpose) in enumerate(
            raw_pages,
            start=1,
        )
    ]


def _shell_template(report: DashboardAppShellReport) -> str:
    lines = [
        '"""',
        "Future HQE Streamlit dashboard app shell template.",
        "",
        "Generated by Module ZZZ as a paper-only scaffold.",
        "This file is a template. Do not treat it as live trading software.",
        '"""',
        "",
        "# Safety boundary:",
        "# - Paper/simulation only.",
        "# - Does not place orders.",
        "# - Does not request live market data.",
        "# - Does not prove profitability.",
        "",
        "# Future usage idea:",
        "# streamlit run apps/hqe_dashboard_app.py",
        "# This generated template does not import Streamlit at runtime.",
        "",
        "APP_TITLE = 'Hunter Quant Engine Dashboard'",
        f"SELECTED_DATASET_PATH = {report.selected_dataset_path!r}",
        "",
        "PAGES = [",
    ]

    for page in report.pages:
        lines.append(
            "    {"
            f"'page_name': {page.page_name!r}, "
            f"'title': {page.title!r}, "
            f"'sections': {page.sections!r}, "
            f"'status': {page.status!r}"
            "},"
        )

    lines.extend(
        [
            "]",
            "",
            "",
            "def describe_app_shell():",
            "    return {",
            "        'app_title': APP_TITLE,",
            "        'selected_dataset_path': SELECTED_DATASET_PATH,",
            "        'pages': PAGES,",
            "        'safety': 'paper-only; no broker orders; no real money; no profitability claim',",
            "    }",
            "",
        ]
    )

    return "\n".join(lines)


def build_dashboard_app_shell_report(
    *,
    dashboard_component_scaffold_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> DashboardAppShellReport:
    scaffold, load_issues = _load_component_scaffold(dashboard_component_scaffold_path)

    issues: list[DashboardAppShellIssue] = []
    issues.extend(load_issues)
    issues.extend(_component_scaffold_issues(scaffold, allow_warnings=allow_warnings))

    component_names = _component_names(scaffold)
    section_names = _section_names(scaffold)
    issues.extend(
        _component_and_section_issues(
            component_names=component_names,
            section_names=section_names,
        )
    )

    pages = _pages()
    status = _status(issues)

    return DashboardAppShellReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dashboard_component_scaffold_path=str(dashboard_component_scaffold_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_dashboard_smoke_test=status in {"pass", "warn"},
        selected_dataset_path=str((scaffold or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        page_count=len(pages),
        component_count=len(component_names),
        section_count=len(section_names),
        completed_total_before_module=77,
        completed_total_after_module=78,
        phase_2_pending_before_module=4,
        phase_2_pending_after_module=3,
        full_hqe_product_estimate_after_module="70-75%",
        issues=issues,
        pages=pages,
        component_names=component_names,
        section_names=section_names,
    )


def write_dashboard_app_shell_report(
    report: DashboardAppShellReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    shell_json = output_dir / "dashboard_app_shell_pack.json"
    shell_txt = output_dir / "dashboard_app_shell_pack.txt"
    pages_csv = output_dir / "dashboard_app_pages.csv"
    template_py = output_dir / "dashboard_app_shell_template.py"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["pages"] = [asdict(page) for page in report.pages]
    shell_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with pages_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["page_index", "page_name", "title", "sections", "status", "purpose"])
        for page in report.pages:
            writer.writerow(
                [
                    page.page_index,
                    page.page_name,
                    page.title,
                    "|".join(page.sections),
                    page.status,
                    page.purpose,
                ]
            )

    template_py.write_text(_shell_template(report), encoding="utf-8")

    lines = [
        "HQE Dashboard App Shell Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future dashboard smoke test: {report.ready_for_future_dashboard_smoke_test}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Pages: {report.page_count}",
        f"Components: {report.component_count}",
        f"Sections: {report.section_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Phase 1 pending after Module UUU: 0 modules.",
        f"- Completed total before Module ZZZ: {report.completed_total_before_module} modules.",
        f"- Completed total after Module ZZZ: {report.completed_total_after_module} modules.",
        f"- Phase 2 pending before Module ZZZ: {report.phase_2_pending_before_module} modules.",
        f"- Phase 2 pending after Module ZZZ: {report.phase_2_pending_after_module} modules.",
        f"- Full HQE product estimate after Module ZZZ: {report.full_hqe_product_estimate_after_module}.",
        "",
        "App pages:",
    ]

    for page in report.pages:
        lines.append(
            f"{page.page_index}. {page.title} [{page.status}] sections={', '.join(page.sections)}"
        )

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
        lines.append("- PASS: Dashboard app shell is ready for future dashboard smoke test.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {shell_json}",
            f"- {shell_txt}",
            f"- {pages_csv}",
            f"- {template_py}",
            f"- {manifest_json}",
        ]
    )
    shell_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "dashboard_app_shell_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_dashboard_smoke_test": report.ready_for_future_dashboard_smoke_test,
        "selected_dataset_path": report.selected_dataset_path,
        "page_count": report.page_count,
        "component_count": report.component_count,
        "section_count": report.section_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_2_pending_after_module": report.phase_2_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "safety_notice": report.safety_notice,
        "outputs": {
            "dashboard_app_shell_pack_json": str(shell_json),
            "dashboard_app_shell_pack_txt": str(shell_txt),
            "dashboard_app_pages_csv": str(pages_csv),
            "dashboard_app_shell_template_py": str(template_py),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "dashboard_app_shell_pack_json": shell_json,
        "dashboard_app_shell_pack_txt": shell_txt,
        "dashboard_app_pages_csv": pages_csv,
        "dashboard_app_shell_template_py": template_py,
        "manifest_json": manifest_json,
    }


def build_and_write_dashboard_app_shell_report(
    *,
    dashboard_component_scaffold_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[DashboardAppShellReport, dict[str, Path]]:
    report = build_dashboard_app_shell_report(
        dashboard_component_scaffold_path=dashboard_component_scaffold_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_dashboard_app_shell_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dashboard app shell pack."
    )
    parser.add_argument(
        "--dashboard-component-scaffold",
        default=(
            "reports/paper_trading/"
            "dashboard_component_scaffold_pack/"
            "dashboard_component_scaffold_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/dashboard_app_shell_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_dashboard_app_shell_report(
        dashboard_component_scaffold_path=Path(args.dashboard_component_scaffold),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE dashboard app shell pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future dashboard smoke test: {report.ready_for_future_dashboard_smoke_test}")
    print(f"Pages: {report.page_count}")
    print(f"Dashboard app shell: {outputs['dashboard_app_shell_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
