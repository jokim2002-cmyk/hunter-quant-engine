"""
Dashboard section registry pack.

Module XXX in the post-v1.0 Dashboard Sprint.

This module reads the dashboard overview snapshot pack and creates a paper-only
section registry plus card routes for future Streamlit layout work.

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


REQUIRED_OVERVIEW_CARDS = {
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
class DashboardSection:
    section_index: int
    section_name: str
    title: str
    status: str
    purpose: str


@dataclass(frozen=True)
class DashboardCardRoute:
    route_index: int
    section_name: str
    card_name: str
    label: str
    source_status: str
    route_status: str


@dataclass(frozen=True)
class DashboardSectionRegistryIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class DashboardSectionRegistryReport:
    generated_at_utc: str
    dashboard_overview_snapshot_path: str
    output_directory: str
    status: str
    ready_for_future_streamlit_component_scaffold: bool
    selected_dataset_path: str
    safety_notice: str
    section_count: int
    card_route_count: int
    overview_card_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_2_pending_before_module: int
    phase_2_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    issues: list[DashboardSectionRegistryIssue]
    sections: list[DashboardSection]
    card_routes: list[DashboardCardRoute]
    overview_card_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation dashboard section registry pack only. This pack "
        "creates dashboard sections and card routes from paper-only evidence. "
        "It does not start a dashboard UI, does not run backtests, does not "
        "calculate profitability, does not select a winning strategy, does not "
        "modify strategy logic, does not connect to brokers, does not request "
        "live market data, does not place real orders, does not use real money, "
        "or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> DashboardSectionRegistryIssue:
    return DashboardSectionRegistryIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[DashboardSectionRegistryIssue]) -> str:
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


def _load_overview_snapshot(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[DashboardSectionRegistryIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "dashboard_overview_snapshot_pack_missing",
                1,
                f"Dashboard overview snapshot pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "dashboard_overview_snapshot_pack_invalid_json",
                1,
                f"Dashboard overview snapshot pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "dashboard_overview_snapshot_pack_invalid_shape",
                1,
                "Dashboard overview snapshot pack must be a JSON object.",
            )
        ]

    return payload, []


def _overview_snapshot_issues(
    snapshot: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[DashboardSectionRegistryIssue]:
    if snapshot is None:
        return []

    issues: list[DashboardSectionRegistryIssue] = []

    status = str(snapshot.get("status") or "unknown").lower()
    ready = bool(snapshot.get("ready_for_future_streamlit_layout"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "dashboard_overview_snapshot_pack_warn",
                1,
                "Dashboard overview snapshot pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "dashboard_overview_snapshot_pack_not_pass",
                1,
                f"Dashboard overview snapshot pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "dashboard_overview_snapshot_pack_not_ready",
                1,
                "Dashboard overview snapshot pack is not ready for future Streamlit layout.",
            )
        )

    forbidden = _forbidden(snapshot)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "dashboard_overview_snapshot_pack_forbidden_fields",
                len(forbidden),
                "Dashboard overview snapshot pack contains forbidden broker/order/real-money fields.",
            )
        )

    snapshot_issues = snapshot.get("issues")
    if isinstance(snapshot_issues, list):
        fail_count = sum(
            1
            for item in snapshot_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "dashboard_overview_snapshot_pack_contains_fail_issues",
                    fail_count,
                    "Dashboard overview snapshot pack contains fail issues.",
                )
            )

    return issues


def _overview_cards(snapshot: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if snapshot is None:
        return []

    raw_cards = snapshot.get("overview_cards")
    if not isinstance(raw_cards, list):
        return []

    return [card for card in raw_cards if isinstance(card, Mapping)]


def _overview_card_names(cards: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted(
        {
            str(card.get("card_name") or "").strip().lower()
            for card in cards
            if str(card.get("card_name") or "").strip()
        }
    )


def _card_issues(card_names: Sequence[str]) -> list[DashboardSectionRegistryIssue]:
    missing = REQUIRED_OVERVIEW_CARDS - set(card_names)

    if missing:
        return [
            _issue(
                "fail",
                "required_dashboard_overview_cards_missing",
                len(missing),
                "Required dashboard overview cards are missing.",
            )
        ]

    return []


def _sections() -> list[DashboardSection]:
    raw_sections = [
        (
            "overview",
            "Overview",
            "ready",
            "Top-level paper-only project summary cards.",
        ),
        (
            "progress",
            "Progress",
            "ready",
            "v1.0, Phase 1, and Phase 2 progress status.",
        ),
        (
            "inputs",
            "Dashboard Inputs",
            "ready",
            "Input index and evidence availability cards.",
        ),
        (
            "mode_evidence",
            "Mode Evidence",
            "planned",
            "Strict, balanced, and relaxed mode evidence cards for future UI.",
        ),
        (
            "cost_review",
            "Cost Review",
            "planned",
            "Paper-only cost/slippage review cards for future UI.",
        ),
        (
            "safety",
            "Safety Boundary",
            "ready",
            "No live, broker, real-money, or profitability-claim boundary.",
        ),
    ]

    return [
        DashboardSection(
            section_index=index,
            section_name=section_name,
            title=title,
            status=status,
            purpose=purpose,
        )
        for index, (section_name, title, status, purpose) in enumerate(raw_sections, start=1)
    ]


def _card_routes(cards: Sequence[Mapping[str, Any]]) -> list[DashboardCardRoute]:
    section_by_card = {
        "project_progress": "progress",
        "v1_status": "progress",
        "phase_1_status": "progress",
        "phase_2_status": "progress",
        "dashboard_inputs": "inputs",
        "existing_dashboard_inputs": "inputs",
        "missing_dashboard_inputs": "inputs",
        "selected_dataset": "overview",
        "safety_boundary": "safety",
    }

    routes: list[DashboardCardRoute] = []
    for index, card in enumerate(cards, start=1):
        card_name = str(card.get("card_name") or "").strip().lower()
        label = str(card.get("label") or card_name).strip()
        source_status = str(card.get("status") or "unknown").strip().lower()
        section_name = section_by_card.get(card_name, "overview")
        route_status = "ready" if card_name in section_by_card else "review"

        routes.append(
            DashboardCardRoute(
                route_index=index,
                section_name=section_name,
                card_name=card_name,
                label=label,
                source_status=source_status,
                route_status=route_status,
            )
        )

    return routes


def _section_issues(sections: Sequence[DashboardSection]) -> list[DashboardSectionRegistryIssue]:
    names = {section.section_name for section in sections}
    missing = REQUIRED_SECTIONS - names

    if missing:
        return [
            _issue(
                "fail",
                "required_dashboard_sections_missing",
                len(missing),
                "Required dashboard sections are missing from the section registry.",
            )
        ]

    return []


def build_dashboard_section_registry_report(
    *,
    dashboard_overview_snapshot_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> DashboardSectionRegistryReport:
    snapshot, load_issues = _load_overview_snapshot(dashboard_overview_snapshot_path)

    issues: list[DashboardSectionRegistryIssue] = []
    issues.extend(load_issues)
    issues.extend(_overview_snapshot_issues(snapshot, allow_warnings=allow_warnings))

    cards = _overview_cards(snapshot)
    card_names = _overview_card_names(cards)
    issues.extend(_card_issues(card_names))

    sections = _sections()
    issues.extend(_section_issues(sections))

    routes = _card_routes(cards)
    status = _status(issues)

    return DashboardSectionRegistryReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dashboard_overview_snapshot_path=str(dashboard_overview_snapshot_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_streamlit_component_scaffold=status in {"pass", "warn"},
        selected_dataset_path=str((snapshot or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        section_count=len(sections),
        card_route_count=len(routes),
        overview_card_count=len(cards),
        completed_total_before_module=75,
        completed_total_after_module=76,
        phase_2_pending_before_module=6,
        phase_2_pending_after_module=5,
        full_hqe_product_estimate_after_module="68-73%",
        issues=issues,
        sections=sections,
        card_routes=routes,
        overview_card_names=card_names,
    )


def write_dashboard_section_registry_report(
    report: DashboardSectionRegistryReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    registry_json = output_dir / "dashboard_section_registry_pack.json"
    registry_txt = output_dir / "dashboard_section_registry_pack.txt"
    sections_csv = output_dir / "dashboard_sections.csv"
    routes_csv = output_dir / "dashboard_card_routes.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["sections"] = [asdict(section) for section in report.sections]
    data["card_routes"] = [asdict(route) for route in report.card_routes]
    registry_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with sections_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section_index", "section_name", "title", "status", "purpose"])
        for section in report.sections:
            writer.writerow(
                [
                    section.section_index,
                    section.section_name,
                    section.title,
                    section.status,
                    section.purpose,
                ]
            )

    with routes_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "route_index",
                "section_name",
                "card_name",
                "label",
                "source_status",
                "route_status",
            ]
        )
        for route in report.card_routes:
            writer.writerow(
                [
                    route.route_index,
                    route.section_name,
                    route.card_name,
                    route.label,
                    route.source_status,
                    route.route_status,
                ]
            )

    lines = [
        "HQE Dashboard Section Registry Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future Streamlit component scaffold: {report.ready_for_future_streamlit_component_scaffold}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Dashboard sections: {report.section_count}",
        f"Card routes: {report.card_route_count}",
        f"Overview cards: {report.overview_card_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Phase 1 pending after Module UUU: 0 modules.",
        f"- Completed total before Module XXX: {report.completed_total_before_module} modules.",
        f"- Completed total after Module XXX: {report.completed_total_after_module} modules.",
        f"- Phase 2 pending before Module XXX: {report.phase_2_pending_before_module} modules.",
        f"- Phase 2 pending after Module XXX: {report.phase_2_pending_after_module} modules.",
        f"- Full HQE product estimate after Module XXX: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Dashboard sections:",
    ]

    for section in report.sections:
        lines.append(
            f"{section.section_index}. {section.title} [{section.status}] - {section.purpose}"
        )

    lines.extend(["", "Card routes:"])
    for route in report.card_routes:
        lines.append(
            f"{route.route_index}. {route.card_name} -> {route.section_name} [{route.route_status}]"
        )

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
        lines.append("- PASS: Dashboard section registry is ready for future Streamlit component scaffold.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {registry_json}",
            f"- {registry_txt}",
            f"- {sections_csv}",
            f"- {routes_csv}",
            f"- {manifest_json}",
        ]
    )
    registry_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "dashboard_section_registry_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_streamlit_component_scaffold": report.ready_for_future_streamlit_component_scaffold,
        "selected_dataset_path": report.selected_dataset_path,
        "section_count": report.section_count,
        "card_route_count": report.card_route_count,
        "overview_card_count": report.overview_card_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_2_pending_after_module": report.phase_2_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "safety_notice": report.safety_notice,
        "outputs": {
            "dashboard_section_registry_pack_json": str(registry_json),
            "dashboard_section_registry_pack_txt": str(registry_txt),
            "dashboard_sections_csv": str(sections_csv),
            "dashboard_card_routes_csv": str(routes_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "dashboard_section_registry_pack_json": registry_json,
        "dashboard_section_registry_pack_txt": registry_txt,
        "dashboard_sections_csv": sections_csv,
        "dashboard_card_routes_csv": routes_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_dashboard_section_registry_report(
    *,
    dashboard_overview_snapshot_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[DashboardSectionRegistryReport, dict[str, Path]]:
    report = build_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=dashboard_overview_snapshot_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_dashboard_section_registry_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dashboard section registry pack."
    )
    parser.add_argument(
        "--dashboard-overview-snapshot",
        default=(
            "reports/paper_trading/"
            "dashboard_overview_snapshot_pack/"
            "dashboard_overview_snapshot_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/dashboard_section_registry_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=Path(args.dashboard_overview_snapshot),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE dashboard section registry pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future Streamlit component scaffold: {report.ready_for_future_streamlit_component_scaffold}")
    print(f"Sections: {report.section_count}")
    print(f"Dashboard section registry: {outputs['dashboard_section_registry_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
