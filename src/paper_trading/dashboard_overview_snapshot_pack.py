"""
Dashboard overview snapshot pack.

Module WWW in the post-v1.0 Dashboard Sprint.

This module reads the dashboard input index pack and creates paper-only static
dashboard overview cards for future Streamlit UI work.

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


REQUIRED_DASHBOARD_CATEGORIES = {
    "readiness",
    "mode_config",
    "mode_run_matrix",
    "mode_results",
    "cost_review",
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
class DashboardOverviewCard:
    card_index: int
    card_name: str
    label: str
    value: str
    status: str
    description: str


@dataclass(frozen=True)
class DashboardOverviewSnapshotIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class DashboardOverviewSnapshotReport:
    generated_at_utc: str
    dashboard_input_index_path: str
    output_directory: str
    status: str
    ready_for_future_streamlit_layout: bool
    selected_dataset_path: str
    safety_notice: str
    card_count: int
    dashboard_entry_count: int
    dashboard_existing_entry_count: int
    dashboard_missing_entry_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_2_pending_before_module: int
    phase_2_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    issues: list[DashboardOverviewSnapshotIssue]
    overview_cards: list[DashboardOverviewCard]
    dashboard_categories: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation dashboard overview snapshot pack only. This pack "
        "creates static dashboard overview cards from paper-only evidence. It "
        "does not start a dashboard UI, does not run backtests, does not "
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
) -> DashboardOverviewSnapshotIssue:
    return DashboardOverviewSnapshotIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[DashboardOverviewSnapshotIssue]) -> str:
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


def _load_dashboard_input_index(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[DashboardOverviewSnapshotIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "dashboard_input_index_pack_missing",
                1,
                f"Dashboard input index pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "dashboard_input_index_pack_invalid_json",
                1,
                f"Dashboard input index pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "dashboard_input_index_pack_invalid_shape",
                1,
                "Dashboard input index pack must be a JSON object.",
            )
        ]

    return payload, []


def _index_pack_issues(
    index_pack: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[DashboardOverviewSnapshotIssue]:
    if index_pack is None:
        return []

    issues: list[DashboardOverviewSnapshotIssue] = []

    status = str(index_pack.get("status") or "unknown").lower()
    ready = bool(index_pack.get("ready_for_future_streamlit_dashboard"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "dashboard_input_index_pack_warn",
                1,
                "Dashboard input index pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "dashboard_input_index_pack_not_pass",
                1,
                f"Dashboard input index pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "dashboard_input_index_pack_not_ready",
                1,
                "Dashboard input index pack is not ready for future Streamlit dashboard.",
            )
        )

    forbidden = _forbidden(index_pack)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "dashboard_input_index_pack_forbidden_fields",
                len(forbidden),
                "Dashboard input index pack contains forbidden broker/order/real-money fields.",
            )
        )

    index_issues = index_pack.get("issues")
    if isinstance(index_issues, list):
        fail_count = sum(
            1
            for item in index_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "dashboard_input_index_pack_contains_fail_issues",
                    fail_count,
                    "Dashboard input index pack contains fail issues.",
                )
            )

    return issues


def _dashboard_categories(index_pack: Mapping[str, Any] | None) -> list[str]:
    if index_pack is None:
        return []

    raw_entries = index_pack.get("entries")
    if not isinstance(raw_entries, list):
        return []

    return sorted(
        {
            str(entry.get("category") or "").strip().lower()
            for entry in raw_entries
            if isinstance(entry, Mapping) and str(entry.get("category") or "").strip()
        }
    )


def _category_issues(categories: Sequence[str]) -> list[DashboardOverviewSnapshotIssue]:
    missing = REQUIRED_DASHBOARD_CATEGORIES - set(categories)

    if missing:
        return [
            _issue(
                "fail",
                "required_dashboard_overview_categories_missing",
                len(missing),
                "Required dashboard overview categories are missing from the input index.",
            )
        ]

    return []


def _card(
    index: int,
    name: str,
    label: str,
    value: str,
    status: str,
    description: str,
) -> DashboardOverviewCard:
    return DashboardOverviewCard(
        card_index=index,
        card_name=name,
        label=label,
        value=value,
        status=status,
        description=description,
    )


def _overview_cards(
    *,
    index_pack: Mapping[str, Any] | None,
    report_status: str,
) -> list[DashboardOverviewCard]:
    entry_count = int((index_pack or {}).get("entry_count") or 0)
    existing_entry_count = int((index_pack or {}).get("existing_entry_count") or 0)
    missing_entry_count = int((index_pack or {}).get("missing_entry_count") or 0)
    selected_dataset_path = str((index_pack or {}).get("selected_dataset_path") or "")

    card_status = "ready" if report_status in {"pass", "warn"} else "blocked"

    raw_cards = [
        (
            "project_progress",
            "Project progress",
            "75 modules complete",
            card_status,
            "HQE progress after Module WWW in the Dashboard Sprint.",
        ),
        (
            "v1_status",
            "v1.0 status",
            "63/63 modules complete",
            "ready",
            "v1.0 Testing Edition remains complete.",
        ),
        (
            "phase_1_status",
            "Phase 1 status",
            "Real Backtest Usage Sprint complete",
            "ready",
            "Phase 1 was closed in Module UUU as paper-only evidence.",
        ),
        (
            "phase_2_status",
            "Phase 2 status",
            "Dashboard Sprint in progress",
            card_status,
            "Phase 2 now has dashboard input index and overview snapshot foundation.",
        ),
        (
            "dashboard_inputs",
            "Dashboard inputs",
            str(entry_count),
            card_status,
            "Total dashboard input entries from Module VVV.",
        ),
        (
            "existing_dashboard_inputs",
            "Existing inputs",
            str(existing_entry_count),
            card_status,
            "Dashboard input entries currently found on disk.",
        ),
        (
            "missing_dashboard_inputs",
            "Missing optional inputs",
            str(missing_entry_count),
            "review",
            "Missing optional evidence files can be generated later by running paper-only packs.",
        ),
        (
            "selected_dataset",
            "Selected dataset",
            selected_dataset_path or "not provided",
            card_status,
            "Dataset path carried forward from paper-only readiness evidence.",
        ),
        (
            "safety_boundary",
            "Safety boundary",
            "paper-only",
            "ready",
            "No broker orders, no live market data, no real money, no option selling.",
        ),
    ]

    return [
        _card(index, name, label, value, status, description)
        for index, (name, label, value, status, description) in enumerate(raw_cards, start=1)
    ]


def build_dashboard_overview_snapshot_report(
    *,
    dashboard_input_index_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> DashboardOverviewSnapshotReport:
    index_pack, load_issues = _load_dashboard_input_index(dashboard_input_index_path)

    issues: list[DashboardOverviewSnapshotIssue] = []
    issues.extend(load_issues)
    issues.extend(_index_pack_issues(index_pack, allow_warnings=allow_warnings))

    categories = _dashboard_categories(index_pack)
    issues.extend(_category_issues(categories))

    status = _status(issues)
    cards = _overview_cards(index_pack=index_pack, report_status=status)

    return DashboardOverviewSnapshotReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dashboard_input_index_path=str(dashboard_input_index_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_streamlit_layout=status in {"pass", "warn"},
        selected_dataset_path=str((index_pack or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        card_count=len(cards),
        dashboard_entry_count=int((index_pack or {}).get("entry_count") or 0),
        dashboard_existing_entry_count=int((index_pack or {}).get("existing_entry_count") or 0),
        dashboard_missing_entry_count=int((index_pack or {}).get("missing_entry_count") or 0),
        completed_total_before_module=74,
        completed_total_after_module=75,
        phase_2_pending_before_module=7,
        phase_2_pending_after_module=6,
        full_hqe_product_estimate_after_module="67-72%",
        issues=issues,
        overview_cards=cards,
        dashboard_categories=categories,
    )


def write_dashboard_overview_snapshot_report(
    report: DashboardOverviewSnapshotReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_json = output_dir / "dashboard_overview_snapshot_pack.json"
    snapshot_txt = output_dir / "dashboard_overview_snapshot_pack.txt"
    cards_csv = output_dir / "dashboard_overview_cards.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["overview_cards"] = [asdict(card) for card in report.overview_cards]
    snapshot_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with cards_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["card_index", "card_name", "label", "value", "status", "description"])
        for card in report.overview_cards:
            writer.writerow(
                [
                    card.card_index,
                    card.card_name,
                    card.label,
                    card.value,
                    card.status,
                    card.description,
                ]
            )

    lines = [
        "HQE Dashboard Overview Snapshot Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future Streamlit layout: {report.ready_for_future_streamlit_layout}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Overview cards: {report.card_count}",
        f"Dashboard input entries: {report.dashboard_entry_count}",
        f"Existing dashboard inputs: {report.dashboard_existing_entry_count}",
        f"Missing dashboard inputs: {report.dashboard_missing_entry_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Phase 1 pending after Module UUU: 0 modules.",
        f"- Completed total before Module WWW: {report.completed_total_before_module} modules.",
        f"- Completed total after Module WWW: {report.completed_total_after_module} modules.",
        f"- Phase 2 pending before Module WWW: {report.phase_2_pending_before_module} modules.",
        f"- Phase 2 pending after Module WWW: {report.phase_2_pending_after_module} modules.",
        f"- Full HQE product estimate after Module WWW: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Overview cards:",
    ]

    for card in report.overview_cards:
        lines.append(
            f"{card.card_index}. {card.label}: {card.value} [{card.status}] - {card.description}"
        )

    lines.extend(["", "Dashboard categories:"])
    for category in report.dashboard_categories:
        lines.append(f"- {category}")

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
        lines.append("- PASS: Dashboard overview snapshot is ready for future Streamlit layout.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {snapshot_json}",
            f"- {snapshot_txt}",
            f"- {cards_csv}",
            f"- {manifest_json}",
        ]
    )
    snapshot_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "dashboard_overview_snapshot_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_streamlit_layout": report.ready_for_future_streamlit_layout,
        "selected_dataset_path": report.selected_dataset_path,
        "card_count": report.card_count,
        "dashboard_entry_count": report.dashboard_entry_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_2_pending_after_module": report.phase_2_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "safety_notice": report.safety_notice,
        "outputs": {
            "dashboard_overview_snapshot_pack_json": str(snapshot_json),
            "dashboard_overview_snapshot_pack_txt": str(snapshot_txt),
            "dashboard_overview_cards_csv": str(cards_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "dashboard_overview_snapshot_pack_json": snapshot_json,
        "dashboard_overview_snapshot_pack_txt": snapshot_txt,
        "dashboard_overview_cards_csv": cards_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_dashboard_overview_snapshot_report(
    *,
    dashboard_input_index_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[DashboardOverviewSnapshotReport, dict[str, Path]]:
    report = build_dashboard_overview_snapshot_report(
        dashboard_input_index_path=dashboard_input_index_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_dashboard_overview_snapshot_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dashboard overview snapshot pack."
    )
    parser.add_argument(
        "--dashboard-input-index",
        default=(
            "reports/paper_trading/"
            "dashboard_input_index_pack/"
            "dashboard_input_index_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/dashboard_overview_snapshot_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_dashboard_overview_snapshot_report(
        dashboard_input_index_path=Path(args.dashboard_input_index),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE dashboard overview snapshot pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future Streamlit layout: {report.ready_for_future_streamlit_layout}")
    print(f"Overview cards: {report.card_count}")
    print(f"Dashboard overview snapshot: {outputs['dashboard_overview_snapshot_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
