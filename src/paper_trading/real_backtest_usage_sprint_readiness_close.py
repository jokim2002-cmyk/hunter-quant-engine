"""
Real backtest usage sprint readiness close.

Module UUU closes the post-v1.0 Real Backtest Usage Sprint.

This module reads the cost-adjusted mode comparison pack and creates a final
paper-only readiness close report for the first real recorded-data backtest
usage sprint.

It does not run backtests, does not calculate profitability, does not select a
winning strategy, does not modify strategy logic, does not connect to brokers,
does not request live market data, does not place real orders, does not use real
money, or prove profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_MODES = {"strict", "balanced", "relaxed"}
REQUIRED_COST_ASSUMPTIONS = {
    "brokerage_reference",
    "slippage_reference",
    "taxes_and_charges_reference",
    "round_trip_cost_formula",
}

REQUIRED_CHAIN_MODULES = [
    "real_dataset_backtest_input_pack",
    "first_real_dataset_backtest_run_pack",
    "first_real_backtest_output_verification_pack",
    "first_real_backtest_report_review_pack",
    "strategy_tuning_baseline_pack",
    "strategy_mode_comparison_pack",
    "strategy_mode_backtest_run_matrix_pack",
    "strategy_mode_backtest_result_comparison_pack",
    "strategy_mode_cost_adjusted_comparison_pack",
    "real_backtest_usage_sprint_readiness_close",
]

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
class SprintReadinessChecklistItem:
    item_index: int
    item_name: str
    status: str
    evidence: str


@dataclass(frozen=True)
class SprintReadinessIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class RealBacktestUsageSprintReadinessCloseReport:
    generated_at_utc: str
    cost_adjusted_pack_path: str
    output_directory: str
    status: str
    phase_1_closed: bool
    ready_for_future_dashboard_sprint: bool
    selected_dataset_path: str
    safety_notice: str
    completed_total_before_module: int
    completed_total_after_module: int
    phase_1_pending_before_module: int
    phase_1_pending_after_module: int
    full_hqe_product_estimate_after_module: str
    chain_module_count: int
    checklist_item_count: int
    issues: list[SprintReadinessIssue]
    checklist: list[SprintReadinessChecklistItem]
    chain_modules: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation real backtest usage sprint readiness close only. This "
        "report closes the first real recorded-data backtest usage sprint as a "
        "paper-only evidence workflow. It does not run backtests, does not "
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
) -> SprintReadinessIssue:
    return SprintReadinessIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[SprintReadinessIssue]) -> str:
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


def _load_cost_adjusted_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[SprintReadinessIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "cost_adjusted_mode_comparison_pack_missing",
                1,
                f"Cost-adjusted mode comparison pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "cost_adjusted_mode_comparison_pack_invalid_json",
                1,
                f"Cost-adjusted mode comparison pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "cost_adjusted_mode_comparison_pack_invalid_shape",
                1,
                "Cost-adjusted mode comparison pack must be a JSON object.",
            )
        ]

    return payload, []


def _cost_adjusted_pack_issues(
    pack: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[SprintReadinessIssue]:
    if pack is None:
        return []

    issues: list[SprintReadinessIssue] = []

    status = str(pack.get("status") or "unknown").lower()
    ready = bool(pack.get("ready_for_future_strategy_selection_review"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "cost_adjusted_mode_comparison_pack_warn",
                1,
                "Cost-adjusted mode comparison pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "cost_adjusted_mode_comparison_pack_not_pass",
                1,
                f"Cost-adjusted mode comparison pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "cost_adjusted_mode_comparison_pack_not_ready",
                1,
                "Cost-adjusted mode comparison pack is not ready for future strategy selection review.",
            )
        )

    forbidden = _forbidden(pack)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "cost_adjusted_mode_comparison_pack_forbidden_fields",
                len(forbidden),
                "Cost-adjusted mode comparison pack contains forbidden broker/order/real-money fields.",
            )
        )

    pack_issues = pack.get("issues")
    if isinstance(pack_issues, list):
        fail_count = sum(
            1
            for item in pack_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "cost_adjusted_mode_comparison_pack_contains_fail_issues",
                    fail_count,
                    "Cost-adjusted mode comparison pack contains fail issues.",
                )
            )

    return issues


def _mode_names(pack: Mapping[str, Any] | None) -> list[str]:
    if pack is None:
        return []

    raw_names = pack.get("mode_names")
    if isinstance(raw_names, list):
        return sorted(
            {
                str(name).strip().lower()
                for name in raw_names
                if str(name).strip()
            }
        )

    raw_items = pack.get("review_items")
    if not isinstance(raw_items, list):
        return []

    return sorted(
        {
            str(item.get("mode_name") or "").strip().lower()
            for item in raw_items
            if isinstance(item, Mapping) and str(item.get("mode_name") or "").strip()
        }
    )


def _cost_assumption_names(pack: Mapping[str, Any] | None) -> list[str]:
    if pack is None:
        return []

    raw_assumptions = pack.get("cost_assumptions")
    if not isinstance(raw_assumptions, list):
        return []

    return sorted(
        {
            str(item.get("assumption_name") or "").strip().lower()
            for item in raw_assumptions
            if isinstance(item, Mapping) and str(item.get("assumption_name") or "").strip()
        }
    )


def _readiness_issues(
    *,
    mode_names: Sequence[str],
    cost_assumption_names: Sequence[str],
) -> list[SprintReadinessIssue]:
    issues: list[SprintReadinessIssue] = []

    missing_modes = REQUIRED_MODES - set(mode_names)
    if missing_modes:
        issues.append(
            _issue(
                "fail",
                "phase_1_required_modes_missing",
                len(missing_modes),
                "Required strict, balanced, and relaxed modes are missing.",
            )
        )

    missing_assumptions = REQUIRED_COST_ASSUMPTIONS - set(cost_assumption_names)
    if missing_assumptions:
        issues.append(
            _issue(
                "fail",
                "phase_1_required_cost_assumptions_missing",
                len(missing_assumptions),
                "Required cost adjustment assumptions are missing.",
            )
        )

    return issues


def _checklist(status: str, pack: Mapping[str, Any] | None) -> list[SprintReadinessChecklistItem]:
    selected_dataset_path = str((pack or {}).get("selected_dataset_path") or "")
    ready_text = "pass" if status == "pass" else "blocked"

    raw_items = [
        (
            "real_dataset_input",
            ready_text,
            "Real/saved recorded dataset input workflow exists.",
        ),
        (
            "first_run_pack",
            ready_text,
            "Operator run order exists for first real recorded-data paper backtest.",
        ),
        (
            "output_verification",
            ready_text,
            "Expected output verification workflow exists.",
        ),
        (
            "report_review",
            ready_text,
            "Report, metrics, ledger, readiness, gate, and handoff review workflow exists.",
        ),
        (
            "strategy_tuning_baseline",
            ready_text,
            "Tuning baseline questions exist without changing strategy logic.",
        ),
        (
            "mode_comparison",
            ready_text,
            "Strict, balanced, and relaxed paper-only modes exist.",
        ),
        (
            "mode_run_matrix",
            ready_text,
            "Future mode backtest run matrix exists.",
        ),
        (
            "mode_result_comparison",
            ready_text,
            "Mode result comparison workflow exists.",
        ),
        (
            "cost_adjusted_review",
            ready_text,
            "Cost/slippage scaffold exists without profitability claim.",
        ),
        (
            "safety_boundary",
            ready_text,
            "No broker orders, no live market data, no real money, no option selling.",
        ),
        (
            "selected_dataset_path",
            ready_text,
            selected_dataset_path or "Selected dataset path not provided.",
        ),
    ]

    return [
        SprintReadinessChecklistItem(
            item_index=index,
            item_name=item_name,
            status=item_status,
            evidence=evidence,
        )
        for index, (item_name, item_status, evidence) in enumerate(raw_items, start=1)
    ]


def build_real_backtest_usage_sprint_readiness_close_report(
    *,
    cost_adjusted_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> RealBacktestUsageSprintReadinessCloseReport:
    pack, load_issues = _load_cost_adjusted_pack(cost_adjusted_pack_path)

    issues: list[SprintReadinessIssue] = []
    issues.extend(load_issues)
    issues.extend(_cost_adjusted_pack_issues(pack, allow_warnings=allow_warnings))

    mode_names = _mode_names(pack)
    cost_assumption_names = _cost_assumption_names(pack)
    issues.extend(
        _readiness_issues(
            mode_names=mode_names,
            cost_assumption_names=cost_assumption_names,
        )
    )

    status = _status(issues)
    checklist = _checklist(status, pack)

    return RealBacktestUsageSprintReadinessCloseReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        cost_adjusted_pack_path=str(cost_adjusted_pack_path),
        output_directory=str(output_dir),
        status=status,
        phase_1_closed=status in {"pass", "warn"},
        ready_for_future_dashboard_sprint=status in {"pass", "warn"},
        selected_dataset_path=str((pack or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        completed_total_before_module=72,
        completed_total_after_module=73,
        phase_1_pending_before_module=1,
        phase_1_pending_after_module=0,
        full_hqe_product_estimate_after_module="65-70%",
        chain_module_count=len(REQUIRED_CHAIN_MODULES),
        checklist_item_count=len(checklist),
        issues=issues,
        checklist=checklist,
        chain_modules=list(REQUIRED_CHAIN_MODULES),
    )


def write_real_backtest_usage_sprint_readiness_close_report(
    report: RealBacktestUsageSprintReadinessCloseReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    close_json = output_dir / "real_backtest_usage_sprint_readiness_close.json"
    close_txt = output_dir / "real_backtest_usage_sprint_readiness_close.txt"
    checklist_json = output_dir / "real_backtest_usage_sprint_checklist.json"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["checklist"] = [asdict(item) for item in report.checklist]
    close_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    checklist_json.write_text(
        json.dumps(
            {
                "checklist_item_count": report.checklist_item_count,
                "checklist": [asdict(item) for item in report.checklist],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    lines = [
        "HQE Real Backtest Usage Sprint Readiness Close",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Phase 1 closed: {report.phase_1_closed}",
        f"Ready for future dashboard sprint: {report.ready_for_future_dashboard_sprint}",
        f"Selected dataset path: {report.selected_dataset_path}",
        "",
        "Progress:",
        f"- v1.0 Testing Edition: 63/63 modules complete.",
        f"- v1.0 pending: 0 modules.",
        f"- Completed total before Module UUU: {report.completed_total_before_module} modules.",
        f"- Completed total after Module UUU: {report.completed_total_after_module} modules.",
        f"- Phase 1 pending before Module UUU: {report.phase_1_pending_before_module} module.",
        f"- Phase 1 pending after Module UUU: {report.phase_1_pending_after_module} modules.",
        f"- Full HQE product estimate after Module UUU: {report.full_hqe_product_estimate_after_module}.",
        "",
        "Closed chain modules:",
    ]

    for module in report.chain_modules:
        lines.append(f"- {module}")

    lines.extend(["", "Readiness checklist:"])
    for item in report.checklist:
        lines.append(
            f"{item.item_index}. {item.item_name}: {item.status} -> {item.evidence}"
        )

    lines.extend(
        [
            "",
            "Safety:",
            "- This close report does not run backtests.",
            "- This close report does not calculate profitability.",
            "- This close report does not select a winning strategy.",
            "- This close report does not change strategy logic.",
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
        lines.append("- PASS: Real Backtest Usage Sprint is closed as a paper-only evidence workflow.")
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
            f"- {checklist_json}",
            f"- {manifest_json}",
        ]
    )
    close_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "real_backtest_usage_sprint_readiness_close",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "phase_1_closed": report.phase_1_closed,
        "ready_for_future_dashboard_sprint": report.ready_for_future_dashboard_sprint,
        "selected_dataset_path": report.selected_dataset_path,
        "completed_total_after_module": report.completed_total_after_module,
        "phase_1_pending_after_module": report.phase_1_pending_after_module,
        "full_hqe_product_estimate_after_module": report.full_hqe_product_estimate_after_module,
        "safety_notice": report.safety_notice,
        "outputs": {
            "real_backtest_usage_sprint_readiness_close_json": str(close_json),
            "real_backtest_usage_sprint_readiness_close_txt": str(close_txt),
            "real_backtest_usage_sprint_checklist_json": str(checklist_json),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "real_backtest_usage_sprint_readiness_close_json": close_json,
        "real_backtest_usage_sprint_readiness_close_txt": close_txt,
        "real_backtest_usage_sprint_checklist_json": checklist_json,
        "manifest_json": manifest_json,
    }


def build_and_write_real_backtest_usage_sprint_readiness_close_report(
    *,
    cost_adjusted_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[RealBacktestUsageSprintReadinessCloseReport, dict[str, Path]]:
    report = build_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=cost_adjusted_pack_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_real_backtest_usage_sprint_readiness_close_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Close the Real Backtest Usage Sprint readiness chain."
    )
    parser.add_argument(
        "--cost-adjusted-pack",
        default=(
            "reports/paper_trading/"
            "strategy_mode_cost_adjusted_comparison_pack/"
            "strategy_mode_cost_adjusted_comparison_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/real_backtest_usage_sprint_readiness_close",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=Path(args.cost_adjusted_pack),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE real backtest usage sprint readiness close completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Phase 1 closed: {report.phase_1_closed}")
    print(f"Ready for future dashboard sprint: {report.ready_for_future_dashboard_sprint}")
    print(f"Close report: {outputs['real_backtest_usage_sprint_readiness_close_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
