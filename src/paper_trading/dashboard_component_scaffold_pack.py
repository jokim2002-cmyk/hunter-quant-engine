"""
Dashboard component scaffold pack.

Module YYY in the post-v1.0 Dashboard Sprint.

This module reads the dashboard section registry pack and creates paper-only
component scaffold definitions for future Streamlit UI work.

It does not start a dashboard UI, does not run backtests, does not calculate
profitability, does not select a winning strategy, does not modify strategy
logic, does not connect to brokers, does not request live market data, does not
place real orders, does not use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_SECTIONS = {
    "overview",
    "progress",
    "inputs",
    "mode_evidence",
    "cost_review",
    "safety",
}

REQUIRED_ROUTE_CARDS = {
    "project_progress",
    "v1_status",
    "phase_1_status",
    "phase_2_status",
    "dashboard_inputs",
    "existing_dashboard_inputs",
    "missing_dashboard_inputs",
    "selected_dataset",
    "safety_boundary",
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
class DashboardComponentScaffold:
    component_index: int
    component_name: str
    section_name: str
    component_type: str
    source_reference: str
    status: str
    implementation_note: str


@dataclass(frozen=True)
class DashboardComponentScaffoldIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class DashboardComponentScaffoldReport:
    generated_at_utc: str
    dashboard_section_registry_path: str
    output_directory: str
    status: str
    ready_for_future_streamlit_app_shell: bool
    selected_dataset_path: str
    safety_notice: str
    component_count: int
    section_count: int
    card_route_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_2_pending_before_module: int
    phase_2_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    issues: list[DashboardComponentScaffoldIssue]
    components: list[DashboardComponentScaffold]
    section_names: list[str]
    route_card_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation dashboard component scaffold pack only. This pack "
        "creates future Streamlit component definitions from paper-only "
        "dashboard sections and card routes. It does not start a dashboard UI, "
        "does not run backtests, does not calculate profitability, does not "
        "select a winning strategy, does not modify strategy logic, does not "
        "connect to brokers, does not request live market data, does not place "
        "real orders, does not use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> DashboardComponentScaffoldIssue:
    return DashboardComponentScaffoldIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[DashboardComponentScaffoldIssue]) -> str:
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


def _load_section_registry(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[DashboardComponentScaffoldIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "dashboard_section_registry_pack_missing",
                1,
                f"Dashboard section registry pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "dashboard_section_registry_pack_invalid_json",
                1,
                f"Dashboard section registry pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "dashboard_section_registry_pack_invalid_shape",
                1,
                "Dashboard section registry pack must be a JSON object.",
            )
        ]

    return payload, []


def _registry_issues(
    registry: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[DashboardComponentScaffoldIssue]:
    if registry is None:
        return []

    issues: list[DashboardComponentScaffoldIssue] = []

    status = str(registry.get("status") or "unknown").lower()
    ready = bool(registry.get("ready_for_future_streamlit_component_scaffold"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "dashboard_section_registry_pack_warn",
                1,
                "Dashboard section registry pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "dashboard_section_registry_pack_not_pass",
                1,
                f"Dashboard section registry pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "dashboard_section_registry_pack_not_ready",
                1,
                "Dashboard section registry pack is not ready for future Streamlit component scaffold.",
            )
        )

    forbidden = _forbidden(registry)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "dashboard_section_registry_pack_forbidden_fields",
                len(forbidden),
                "Dashboard section registry pack contains forbidden broker/order/real-money fields.",
            )
        )

    registry_issues = registry.get("issues")
    if isinstance(registry_issues, list):
        fail_count = sum(
            1
            for item in registry_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "dashboard_section_registry_pack_contains_fail_issues",
                    fail_count,
                    "Dashboard section registry pack contains fail issues.",
                )
            )

    return issues


def _section_names(registry: Mapping[str, Any] | None) -> list[str]:
    if registry is None:
        return []

    raw_sections = registry.get("sections")
    if not isinstance(raw_sections, list):
        return []

    return sorted(
        {
            str(section.get("section_name") or "").strip().lower()
            for section in raw_sections
            if isinstance(section, Mapping)
            and str(section.get("section_name") or "").strip()
        }
    )


def _route_card_names(registry: Mapping[str, Any] | None) -> list[str]:
    if registry is None:
        return []

    raw_routes = registry.get("card_routes")
    if not isinstance(raw_routes, list):
        return []

    return sorted(
        {
            str(route.get("card_name") or "").strip().lower()
            for route in raw_routes
            if isinstance(route, Mapping)
            and str(route.get("card_name") or "").strip()
        }
    )


def _section_and_route_issues(
    *,
    section_names: Sequence[str],
    route_card_names: Sequence[str],
) -> list[DashboardComponentScaffoldIssue]:
    issues: list[DashboardComponentScaffoldIssue] = []

    missing_sections = REQUIRED_SECTIONS - set(section_names)
    if missing_sections:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_component_sections_missing",
                len(missing_sections),
                "Required dashboard sections are missing for component scaffold.",
            )
        )

    missing_routes = REQUIRED_ROUTE_CARDS - set(route_card_names)
    if missing_routes:
        issues.append(
            _issue(
                "fail",
                "required_dashboard_component_card_routes_missing",
                len(missing_routes),
                "Required dashboard card routes are missing for component scaffold.",
            )
        )

    return issues


def _component(
    index: int,
    name: str,
    section: str,
    component_type: str,
    source_reference: str,
    status: str,
    note: str,
) -> DashboardComponentScaffold:
    return DashboardComponentScaffold(
        component_index=index,
        component_name=name,
        section_name=section,
        component_type=component_type,
        source_reference=source_reference,
        status=status,
        implementation_note=note,
    )


def _components() -> list[DashboardComponentScaffold]:
    raw_components = [
        (
            "overview_header",
            "overview",
            "header",
            "dashboard_overview_snapshot_pack.json",
            "ready",
            "Future Streamlit header for selected dataset and paper-only status.",
        ),
        (
            "progress_card_grid",
            "progress",
            "card_grid",
            "dashboard_card_routes.csv::progress",
            "ready",
            "Future card grid for project, v1.0, Phase 1, and Phase 2 progress.",
        ),
        (
            "input_evidence_table",
            "inputs",
            "table",
            "dashboard_input_entries.csv",
            "planned",
            "Future table for dashboard input evidence paths and existence flags.",
        ),
        (
            "mode_evidence_table",
            "mode_evidence",
            "table",
            "strategy_mode_backtest_result_comparison_pack.json",
            "planned",
            "Future table for strict, balanced, and relaxed paper-only mode evidence.",
        ),
        (
            "cost_review_table",
            "cost_review",
            "table",
            "strategy_mode_cost_adjusted_comparison_pack.json",
            "planned",
            "Future table for cost/slippage review assumptions without profit claims.",
        ),
        (
            "safety_boundary_panel",
            "safety",
            "panel",
            "dashboard_card_routes.csv::safety_boundary",
            "ready",
            "Future safety panel: no broker orders, no live data, no real money.",
        ),
    ]

    return [
        _component(index, name, section, component_type, source_reference, status, note)
        for index, (name, section, component_type, source_reference, status, note) in enumerate(
            raw_components,
            start=1,
        )
    ]


def build_dashboard_component_scaffold_report(
    *,
    dashboard_section_registry_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> DashboardComponentScaffoldReport:
    registry, load_issues = _load_section_registry(dashboard_section_registry_path)

    issues: list[DashboardComponentScaffoldIssue] = []
    issues.extend(load_issues)
    issues.extend(_registry_issues(registry, allow_warnings=allow_warnings))

    section_names = _section_names(registry)
    route_card_names = _route_card_names(registry)
    issues.extend(
        _section_and_route_issues(
            section_names=section_names,
            route_card_names=route_card_names,
        )
    )

    components = _components()
    status = _status(issues)

    return DashboardComponentScaffoldReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dashboard_section_registry_path=str(dashboard_section_registry_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_streamlit_app_shell=status in {"pass", "warn"},
        selected_dataset_path=str((registry or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        component_count=len(components),
        section_count=len(section_names),
        card_route_count=len(route_card_names),
        completed_total_before_module=76,
        completed_total_after_module=77,
        phase_2_pending_before_module=5,
        phase_2_pending_after_module=4,
        full_hqe_product_estimate_after_module="69-74%",
        issues=issues,
        components=components,
        section_names=section_names,
        route_card_names=route_card_names,
    )


def write_dashboard_component_scaffold_report(
    report: DashboardComponentScaffoldReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    scaffold_json = output_dir / "dashboard_component_scaffold_pack.json"
    scaffold_txt = output_dir / "dashboard_component_scaffold_pack.txt"
    components_csv = output_dir / "dashboard_components.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["components"] = [asdict(component) for component in report.components]
    scaffold_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with components_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "component_index",
                "component_name",
                "section_name",
                "component_type",
                "source_reference",
                "status",
                "implementation_note",
            ]
        )
        for component in report.components:
            writer.writerow(
                [
                    component.component_index,
                    component.component_name,
                    component.section_name,
                    component.component_type,
                    component.source_reference,
                    component.status,
                    component.implementation_note,
                ]
            )

    lines = [
        "HQE Dashboard Component Scaffold Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future Streamlit app shell: {report.ready_for_future_streamlit_app_shell}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Components: {report.component_count}",
        f"Sections: {report.section_count}",
        f"Card routes: {report.card_route_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Phase 1 pending after Module UUU: 0 modules.",
        f"- Completed total before Module YYY: {report.completed_total_before_module} modules.",
        f"- Completed total after Module YYY: {report.completed_total_after_module} modules.",
        f"- Phase 2 pending before Module YYY: {report.phase_2_pending_before_module} modules.",
        f"- Phase 2 pending after Module YYY: {report.phase_2_pending_after_module} modules.",
        f"- Full HQE product estimate after Module YYY: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Component scaffold:",
    ]

    for component in report.components:
        lines.append(
            (
                f"{component.component_index}. {component.component_name} "
                f"({component.component_type}) -> {component.section_name} "
                f"[{component.status}]"
            )
        )

    lines.extend(["", "Sections:"])
    for section_name in report.section_names:
        lines.append(f"- {section_name}")

    lines.extend(["", "Route cards:"])
    for card_name in report.route_card_names:
        lines.append(f"- {card_name}")

    lines.extend(
        [
            "",
            "Safety:",
            "- This pack does not start a dashboard UI.",
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
        lines.append("- PASS: Dashboard component scaffold is ready for future Streamlit app shell.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {scaffold_json}",
            f"- {scaffold_txt}",
            f"- {components_csv}",
            f"- {manifest_json}",
        ]
    )
    scaffold_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "dashboard_component_scaffold_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_streamlit_app_shell": report.ready_for_future_streamlit_app_shell,
        "selected_dataset_path": report.selected_dataset_path,
        "component_count": report.component_count,
        "section_count": report.section_count,
        "card_route_count": report.card_route_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_2_pending_after_module": report.phase_2_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "safety_notice": report.safety_notice,
        "outputs": {
            "dashboard_component_scaffold_pack_json": str(scaffold_json),
            "dashboard_component_scaffold_pack_txt": str(scaffold_txt),
            "dashboard_components_csv": str(components_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "dashboard_component_scaffold_pack_json": scaffold_json,
        "dashboard_component_scaffold_pack_txt": scaffold_txt,
        "dashboard_components_csv": components_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_dashboard_component_scaffold_report(
    *,
    dashboard_section_registry_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[DashboardComponentScaffoldReport, dict[str, Path]]:
    report = build_dashboard_component_scaffold_report(
        dashboard_section_registry_path=dashboard_section_registry_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_dashboard_component_scaffold_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dashboard component scaffold pack."
    )
    parser.add_argument(
        "--dashboard-section-registry",
        default=(
            "reports/paper_trading/"
            "dashboard_section_registry_pack/"
            "dashboard_section_registry_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/dashboard_component_scaffold_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_dashboard_component_scaffold_report(
        dashboard_section_registry_path=Path(args.dashboard_section_registry),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE dashboard component scaffold pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future Streamlit app shell: {report.ready_for_future_streamlit_app_shell}")
    print(f"Components: {report.component_count}")
    print(f"Dashboard component scaffold: {outputs['dashboard_component_scaffold_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
