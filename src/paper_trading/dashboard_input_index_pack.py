"""
Dashboard input index pack.

Module VVV starts the post-v1.0 Dashboard Sprint.

This module reads the Real Backtest Usage Sprint readiness close report and
creates a paper-only dashboard input index. It does not start a dashboard UI,
run backtests, calculate profitability, select a winning strategy, connect to
brokers, request live market data, place real orders, or use real money.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


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
class DashboardInputEntry:
    entry_index: int
    entry_name: str
    category: str
    path: str
    exists: bool
    required_for_dashboard: bool
    description: str


@dataclass(frozen=True)
class DashboardInputIndexIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class DashboardInputIndexReport:
    generated_at_utc: str
    readiness_close_path: str
    output_directory: str
    status: str
    ready_for_future_streamlit_dashboard: bool
    selected_dataset_path: str
    safety_notice: str
    entry_count: int
    existing_entry_count: int
    missing_entry_count: int
    completed_total_before_module: int
    completed_total_after_module: int
    phase_2_pending_before_module: int
    phase_2_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    issues: list[DashboardInputIndexIssue]
    entries: list[DashboardInputEntry]


def safety_notice() -> str:
    return (
        "Paper/simulation dashboard input index pack only. This pack creates "
        "a dashboard data index from paper-only evidence reports. It does not "
        "start a dashboard UI, does not run backtests, does not calculate "
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
) -> DashboardInputIndexIssue:
    return DashboardInputIndexIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[DashboardInputIndexIssue]) -> str:
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


def _load_readiness_close(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[DashboardInputIndexIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "real_backtest_usage_sprint_readiness_close_missing",
                1,
                f"Real Backtest Usage Sprint readiness close missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "real_backtest_usage_sprint_readiness_close_invalid_json",
                1,
                f"Readiness close JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "real_backtest_usage_sprint_readiness_close_invalid_shape",
                1,
                "Readiness close must be a JSON object.",
            )
        ]

    return payload, []


def _close_pack_issues(
    close_pack: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[DashboardInputIndexIssue]:
    if close_pack is None:
        return []

    issues: list[DashboardInputIndexIssue] = []

    status = str(close_pack.get("status") or "unknown").lower()
    phase_1_closed = bool(close_pack.get("phase_1_closed"))
    ready_for_dashboard = bool(close_pack.get("ready_for_future_dashboard_sprint"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "real_backtest_usage_sprint_readiness_close_warn",
                1,
                "Real Backtest Usage Sprint readiness close status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "real_backtest_usage_sprint_readiness_close_not_pass",
                1,
                f"Readiness close status is not pass: {status}.",
            )
        )

    if not phase_1_closed:
        issues.append(
            _issue(
                "fail",
                "real_backtest_usage_sprint_not_closed",
                1,
                "Phase 1 is not closed.",
            )
        )

    if not ready_for_dashboard:
        issues.append(
            _issue(
                "fail",
                "not_ready_for_future_dashboard_sprint",
                1,
                "Readiness close is not ready for future dashboard sprint.",
            )
        )

    forbidden = _forbidden(close_pack)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "readiness_close_forbidden_fields",
                len(forbidden),
                "Readiness close contains forbidden broker/order/real-money fields.",
            )
        )

    close_issues = close_pack.get("issues")
    if isinstance(close_issues, list):
        fail_count = sum(
            1
            for item in close_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "readiness_close_contains_fail_issues",
                    fail_count,
                    "Readiness close contains fail issues.",
                )
            )

    return issues


def _entry(
    index: int,
    name: str,
    category: str,
    path: str,
    required: bool,
    description: str,
) -> DashboardInputEntry:
    return DashboardInputEntry(
        entry_index=index,
        entry_name=name,
        category=category,
        path=path,
        exists=Path(path).exists(),
        required_for_dashboard=required,
        description=description,
    )


def _dashboard_entries(readiness_close_path: Path) -> list[DashboardInputEntry]:
    raw_entries = [
        (
            "real_backtest_usage_sprint_readiness_close",
            "readiness",
            str(readiness_close_path),
            True,
            "Phase 1 close report and dashboard sprint handoff input.",
        ),
        (
            "real_dataset_backtest_input_pack",
            "dataset",
            "reports/paper_trading/real_dataset_backtest_input_pack/real_dataset_backtest_input_pack.json",
            False,
            "Saved recorded-data discovery evidence.",
        ),
        (
            "first_real_dataset_backtest_run_pack",
            "run_order",
            "reports/paper_trading/first_real_dataset_backtest_run_pack/first_real_dataset_backtest_run_pack.json",
            False,
            "First paper backtest run order evidence.",
        ),
        (
            "first_real_backtest_output_verification_pack",
            "verification",
            "reports/paper_trading/first_real_backtest_output_verification_pack/first_real_backtest_output_verification_pack.json",
            False,
            "Expected output verification evidence.",
        ),
        (
            "first_real_backtest_report_review_pack",
            "review",
            "reports/paper_trading/first_real_backtest_report_review_pack/first_real_backtest_report_review_pack.json",
            False,
            "Report, metrics, and ledger review evidence.",
        ),
        (
            "strategy_tuning_baseline_pack",
            "tuning",
            "reports/paper_trading/strategy_tuning_baseline_pack/strategy_tuning_baseline_pack.json",
            False,
            "Safe tuning baseline questions.",
        ),
        (
            "strategy_mode_comparison_pack",
            "mode_config",
            "reports/paper_trading/strategy_mode_comparison_pack/strategy_mode_comparison_pack.json",
            False,
            "Strict, balanced, and relaxed mode definitions.",
        ),
        (
            "strategy_mode_backtest_run_matrix_pack",
            "mode_run_matrix",
            "reports/paper_trading/strategy_mode_backtest_run_matrix_pack/strategy_mode_backtest_run_matrix_pack.json",
            False,
            "Future paper-only mode run matrix.",
        ),
        (
            "strategy_mode_backtest_result_comparison_pack",
            "mode_results",
            "reports/paper_trading/strategy_mode_backtest_result_comparison_pack/strategy_mode_backtest_result_comparison_pack.json",
            False,
            "Mode result output comparison evidence.",
        ),
        (
            "strategy_mode_cost_adjusted_comparison_pack",
            "cost_review",
            "reports/paper_trading/strategy_mode_cost_adjusted_comparison_pack/strategy_mode_cost_adjusted_comparison_pack.json",
            False,
            "Paper-only cost/slippage review scaffold.",
        ),
    ]

    return [
        _entry(index, name, category, path, required, description)
        for index, (name, category, path, required, description)
        in enumerate(raw_entries, start=1)
    ]


def _entry_issues(
    entries: Sequence[DashboardInputEntry],
    *,
    require_required_entries_exist: bool,
) -> list[DashboardInputIndexIssue]:
    missing_required = [
        entry
        for entry in entries
        if entry.required_for_dashboard and not entry.exists
    ]

    if require_required_entries_exist and missing_required:
        return [
            _issue(
                "fail",
                "required_dashboard_input_entries_missing_on_disk",
                len(missing_required),
                "One or more required dashboard input entries are missing on disk.",
            )
        ]

    return []


def build_dashboard_input_index_report(
    *,
    readiness_close_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
    require_required_entries_exist: bool = True,
) -> DashboardInputIndexReport:
    close_pack, load_issues = _load_readiness_close(readiness_close_path)

    issues: list[DashboardInputIndexIssue] = []
    issues.extend(load_issues)
    issues.extend(_close_pack_issues(close_pack, allow_warnings=allow_warnings))

    entries = _dashboard_entries(readiness_close_path)
    issues.extend(
        _entry_issues(
            entries,
            require_required_entries_exist=require_required_entries_exist,
        )
    )

    status = _status(issues)

    return DashboardInputIndexReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        readiness_close_path=str(readiness_close_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_streamlit_dashboard=status in {"pass", "warn"},
        selected_dataset_path=str((close_pack or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        entry_count=len(entries),
        existing_entry_count=sum(1 for entry in entries if entry.exists),
        missing_entry_count=sum(1 for entry in entries if not entry.exists),
        completed_total_before_module=73,
        completed_total_after_module=74,
        phase_2_pending_before_module=8,
        phase_2_pending_after_module=7,
        full_hqe_product_estimate_after_module="66-71%",
        issues=issues,
        entries=entries,
    )


def write_dashboard_input_index_report(
    report: DashboardInputIndexReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    index_json = output_dir / "dashboard_input_index_pack.json"
    index_txt = output_dir / "dashboard_input_index_pack.txt"
    entries_csv = output_dir / "dashboard_input_entries.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["entries"] = [asdict(entry) for entry in report.entries]
    index_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with entries_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "entry_index",
                "entry_name",
                "category",
                "required_for_dashboard",
                "exists",
                "path",
                "description",
            ]
        )
        for entry in report.entries:
            writer.writerow(
                [
                    entry.entry_index,
                    entry.entry_name,
                    entry.category,
                    entry.required_for_dashboard,
                    entry.exists,
                    entry.path,
                    entry.description,
                ]
            )

    lines = [
        "HQE Dashboard Input Index Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future Streamlit dashboard: {report.ready_for_future_streamlit_dashboard}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Dashboard input entries: {report.entry_count}",
        f"Existing entries: {report.existing_entry_count}",
        f"Missing entries: {report.missing_entry_count}",
        "",
        "Progress:",
        "- v1.0 Testing Edition: 63/63 modules complete.",
        "- v1.0 pending: 0 modules.",
        "- Phase 1 pending after Module UUU: 0 modules.",
        f"- Completed total before Module VVV: {report.completed_total_before_module} modules.",
        f"- Completed total after Module VVV: {report.completed_total_after_module} modules.",
        f"- Phase 2 pending before Module VVV: {report.phase_2_pending_before_module} modules.",
        f"- Phase 2 pending after Module VVV: {report.phase_2_pending_after_module} modules.",
        f"- Full HQE product estimate after Module VVV: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Dashboard inputs:",
    ]

    for entry in report.entries:
        lines.append(
            (
                f"{entry.entry_index}. {entry.entry_name} "
                f"[{entry.category}] exists={entry.exists}, "
                f"required={entry.required_for_dashboard}, path={entry.path}"
            )
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
        lines.append("- PASS: Dashboard input index is ready for future Streamlit dashboard.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {index_json}",
            f"- {index_txt}",
            f"- {entries_csv}",
            f"- {manifest_json}",
        ]
    )
    index_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "dashboard_input_index_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_streamlit_dashboard": report.ready_for_future_streamlit_dashboard,
        "selected_dataset_path": report.selected_dataset_path,
        "entry_count": report.entry_count,
        "existing_entry_count": report.existing_entry_count,
        "missing_entry_count": report.missing_entry_count,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_2_pending_after_module": report.phase_2_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "safety_notice": report.safety_notice,
        "outputs": {
            "dashboard_input_index_pack_json": str(index_json),
            "dashboard_input_index_pack_txt": str(index_txt),
            "dashboard_input_entries_csv": str(entries_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "dashboard_input_index_pack_json": index_json,
        "dashboard_input_index_pack_txt": index_txt,
        "dashboard_input_entries_csv": entries_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_dashboard_input_index_report(
    *,
    readiness_close_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
    require_required_entries_exist: bool = True,
) -> tuple[DashboardInputIndexReport, dict[str, Path]]:
    report = build_dashboard_input_index_report(
        readiness_close_path=readiness_close_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
        require_required_entries_exist=require_required_entries_exist,
    )
    outputs = write_dashboard_input_index_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dashboard input index pack."
    )
    parser.add_argument(
        "--readiness-close",
        default=(
            "reports/paper_trading/"
            "real_backtest_usage_sprint_readiness_close/"
            "real_backtest_usage_sprint_readiness_close.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/dashboard_input_index_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--skip-required-entry-existence-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_dashboard_input_index_report(
        readiness_close_path=Path(args.readiness_close),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
        require_required_entries_exist=not args.skip_required_entry_existence_check,
    )

    print("HQE dashboard input index pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future Streamlit dashboard: {report.ready_for_future_streamlit_dashboard}")
    print(f"Dashboard input entries: {report.entry_count}")
    print(f"Dashboard input index: {outputs['dashboard_input_index_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
