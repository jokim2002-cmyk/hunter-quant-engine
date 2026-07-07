"""
Strategy mode cost-adjusted comparison pack.

Module TTT in the post-v1.0 Real Backtest Usage Sprint.

This module reads the strategy mode backtest result comparison pack and creates
a paper-only cost/slippage adjustment review scaffold for strict, balanced, and
relaxed mode results.

It does not run backtests, does not calculate profitability, does not select a
winning strategy, does not modify strategy logic, does not connect to brokers,
does not request live market data, does not place real orders, does not use real
money, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_MODES = {"strict", "balanced", "relaxed"}
REQUIRED_RESULT_CATEGORIES = {"ledger", "metrics", "report", "readiness"}

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
class CostAdjustmentAssumption:
    assumption_name: str
    value: str
    purpose: str


@dataclass(frozen=True)
class ModeCostAdjustedReviewItem:
    mode_name: str
    ledger_path: str
    metrics_path: str
    report_path: str
    readiness_path: str
    cost_review_status: str
    review_instruction: str


@dataclass(frozen=True)
class CostAdjustedModeComparisonIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class CostAdjustedModeComparisonReport:
    generated_at_utc: str
    result_comparison_pack_path: str
    output_directory: str
    status: str
    ready_for_future_strategy_selection_review: bool
    selected_dataset_path: str
    safety_notice: str
    mode_count: int
    cost_assumption_count: int
    review_item_count: int
    issues: list[CostAdjustedModeComparisonIssue]
    cost_assumptions: list[CostAdjustmentAssumption]
    review_items: list[ModeCostAdjustedReviewItem]
    mode_names: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation cost-adjusted mode comparison pack only. This pack "
        "creates a cost and slippage review scaffold for strict, balanced, and "
        "relaxed paper-only results. It does not run backtests, does not "
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
) -> CostAdjustedModeComparisonIssue:
    return CostAdjustedModeComparisonIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[CostAdjustedModeComparisonIssue]) -> str:
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


def _load_result_comparison_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[CostAdjustedModeComparisonIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "strategy_mode_result_comparison_pack_missing",
                1,
                f"Strategy mode result comparison pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "strategy_mode_result_comparison_pack_invalid_json",
                1,
                f"Strategy mode result comparison pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "strategy_mode_result_comparison_pack_invalid_shape",
                1,
                "Strategy mode result comparison pack must be a JSON object.",
            )
        ]

    return payload, []


def _result_comparison_issues(
    comparison: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[CostAdjustedModeComparisonIssue]:
    if comparison is None:
        return []

    issues: list[CostAdjustedModeComparisonIssue] = []

    status = str(comparison.get("status") or "unknown").lower()
    ready = bool(comparison.get("ready_for_future_cost_adjusted_mode_comparison"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "strategy_mode_result_comparison_pack_warn",
                1,
                "Strategy mode result comparison pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "strategy_mode_result_comparison_pack_not_pass",
                1,
                f"Strategy mode result comparison pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "strategy_mode_result_comparison_pack_not_ready",
                1,
                "Strategy mode result comparison pack is not ready for cost-adjusted mode comparison.",
            )
        )

    forbidden = _forbidden(comparison)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "strategy_mode_result_comparison_pack_forbidden_fields",
                len(forbidden),
                "Strategy mode result comparison pack contains forbidden broker/order/real-money fields.",
            )
        )

    comparison_issues = comparison.get("issues")
    if isinstance(comparison_issues, list):
        fail_count = sum(
            1
            for item in comparison_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "strategy_mode_result_comparison_pack_contains_fail_issues",
                    fail_count,
                    "Strategy mode result comparison pack contains fail issues.",
                )
            )

    return issues


def _mode_names_from_summaries(comparison: Mapping[str, Any] | None) -> list[str]:
    if comparison is None:
        return []

    raw_summaries = comparison.get("mode_summaries")
    if not isinstance(raw_summaries, list):
        return []

    return sorted(
        {
            str(item.get("mode_name") or "").strip().lower()
            for item in raw_summaries
            if isinstance(item, Mapping) and str(item.get("mode_name") or "").strip()
        }
    )


def _paths_by_mode_and_category(
    comparison: Mapping[str, Any] | None,
) -> dict[str, dict[str, str]]:
    if comparison is None:
        return {}

    raw_paths = comparison.get("result_paths")
    if not isinstance(raw_paths, list):
        return {}

    paths: dict[str, dict[str, str]] = {}
    for item in raw_paths:
        if not isinstance(item, Mapping):
            continue

        mode_name = str(item.get("mode_name") or "").strip().lower()
        category = str(item.get("category") or "").strip().lower()
        path = str(item.get("path") or "").strip()

        if not mode_name or not category or not path:
            continue

        paths.setdefault(mode_name, {})[category] = path

    return paths


def _mode_and_path_issues(
    mode_names: Sequence[str],
    paths_by_mode: Mapping[str, Mapping[str, str]],
) -> list[CostAdjustedModeComparisonIssue]:
    issues: list[CostAdjustedModeComparisonIssue] = []
    mode_set = set(mode_names)

    missing_modes = REQUIRED_MODES - mode_set
    if missing_modes:
        issues.append(
            _issue(
                "fail",
                "required_cost_adjusted_modes_missing",
                len(missing_modes),
                "Required strict, balanced, and relaxed mode summaries are missing.",
            )
        )

    missing_category_count = 0
    for mode_name in REQUIRED_MODES:
        categories = set(paths_by_mode.get(mode_name, {}).keys())
        missing_category_count += len(REQUIRED_RESULT_CATEGORIES - categories)

    if missing_category_count:
        issues.append(
            _issue(
                "fail",
                "required_cost_adjusted_result_categories_missing",
                missing_category_count,
                "Required ledger, metrics, report, or readiness paths are missing for one or more modes.",
            )
        )

    return issues


def _cost_assumptions() -> list[CostAdjustmentAssumption]:
    return [
        CostAdjustmentAssumption(
            "brokerage_reference",
            "operator_supplied",
            "Brokerage is a review input only and must not imply live broker execution.",
        ),
        CostAdjustmentAssumption(
            "slippage_reference",
            "operator_supplied",
            "Slippage is a paper-only estimate for future report review.",
        ),
        CostAdjustmentAssumption(
            "taxes_and_charges_reference",
            "operator_supplied",
            "Taxes and exchange charges are review assumptions only.",
        ),
        CostAdjustmentAssumption(
            "round_trip_cost_formula",
            "brokerage + slippage + taxes_and_charges",
            "Formula scaffold for future paper-only cost-adjusted comparison.",
        ),
    ]


def _review_items(
    paths_by_mode: Mapping[str, Mapping[str, str]],
) -> list[ModeCostAdjustedReviewItem]:
    items: list[ModeCostAdjustedReviewItem] = []

    for mode_name in ["strict", "balanced", "relaxed"]:
        paths = paths_by_mode.get(mode_name, {})
        items.append(
            ModeCostAdjustedReviewItem(
                mode_name=mode_name,
                ledger_path=paths.get("ledger", ""),
                metrics_path=paths.get("metrics", ""),
                report_path=paths.get("report", ""),
                readiness_path=paths.get("readiness", ""),
                cost_review_status="requires_operator_cost_inputs",
                review_instruction=(
                    "Review trade count, gross simulated reference, and drawdown reference "
                    "with operator-supplied cost assumptions. Do not treat this as profitability proof."
                ),
            )
        )

    return items


def build_cost_adjusted_mode_comparison_report(
    *,
    result_comparison_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> CostAdjustedModeComparisonReport:
    comparison, load_issues = _load_result_comparison_pack(result_comparison_pack_path)

    issues: list[CostAdjustedModeComparisonIssue] = []
    issues.extend(load_issues)
    issues.extend(_result_comparison_issues(comparison, allow_warnings=allow_warnings))

    mode_names = _mode_names_from_summaries(comparison)
    paths_by_mode = _paths_by_mode_and_category(comparison)
    issues.extend(_mode_and_path_issues(mode_names, paths_by_mode))

    assumptions = _cost_assumptions()
    review_items = _review_items(paths_by_mode)
    status = _status(issues)

    return CostAdjustedModeComparisonReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        result_comparison_pack_path=str(result_comparison_pack_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_strategy_selection_review=status in {"pass", "warn"},
        selected_dataset_path=str((comparison or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        mode_count=len(mode_names),
        cost_assumption_count=len(assumptions),
        review_item_count=len(review_items),
        issues=issues,
        cost_assumptions=assumptions,
        review_items=review_items,
        mode_names=mode_names,
    )


def write_cost_adjusted_mode_comparison_report(
    report: CostAdjustedModeComparisonReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    comparison_json = output_dir / "strategy_mode_cost_adjusted_comparison_pack.json"
    comparison_txt = output_dir / "strategy_mode_cost_adjusted_comparison_pack.txt"
    assumptions_csv = output_dir / "cost_adjustment_assumptions.csv"
    review_csv = output_dir / "cost_adjusted_mode_review_items.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["cost_assumptions"] = [asdict(assumption) for assumption in report.cost_assumptions]
    data["review_items"] = [asdict(item) for item in report.review_items]
    comparison_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with assumptions_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["assumption_name", "value", "purpose"])
        for assumption in report.cost_assumptions:
            writer.writerow([assumption.assumption_name, assumption.value, assumption.purpose])

    with review_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "mode_name",
                "ledger_path",
                "metrics_path",
                "report_path",
                "readiness_path",
                "cost_review_status",
                "review_instruction",
            ]
        )
        for item in report.review_items:
            writer.writerow(
                [
                    item.mode_name,
                    item.ledger_path,
                    item.metrics_path,
                    item.report_path,
                    item.readiness_path,
                    item.cost_review_status,
                    item.review_instruction,
                ]
            )

    lines = [
        "HQE Strategy Mode Cost-Adjusted Comparison Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future strategy selection review: {report.ready_for_future_strategy_selection_review}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Modes: {report.mode_count}",
        f"Cost assumptions: {report.cost_assumption_count}",
        f"Review items: {report.review_item_count}",
        "",
        "Cost assumptions:",
    ]

    for assumption in report.cost_assumptions:
        lines.append(f"- {assumption.assumption_name}: {assumption.value} -> {assumption.purpose}")

    lines.extend(["", "Mode review items:"])
    for item in report.review_items:
        lines.append(
            (
                f"- {item.mode_name}: {item.cost_review_status}; "
                f"ledger={item.ledger_path}; metrics={item.metrics_path}"
            )
        )

    lines.extend(
        [
            "",
            "Safety:",
            "- This pack does not run backtests.",
            "- This pack does not calculate profitability.",
            "- This pack does not select a winning strategy.",
            "- This pack does not change strategy logic.",
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
        lines.append("- PASS: Cost-adjusted comparison scaffold is ready for future strategy selection review.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {comparison_json}",
            f"- {comparison_txt}",
            f"- {assumptions_csv}",
            f"- {review_csv}",
            f"- {manifest_json}",
        ]
    )
    comparison_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "strategy_mode_cost_adjusted_comparison_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_strategy_selection_review": report.ready_for_future_strategy_selection_review,
        "selected_dataset_path": report.selected_dataset_path,
        "mode_count": report.mode_count,
        "cost_assumption_count": report.cost_assumption_count,
        "review_item_count": report.review_item_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "strategy_mode_cost_adjusted_comparison_pack_json": str(comparison_json),
            "strategy_mode_cost_adjusted_comparison_pack_txt": str(comparison_txt),
            "cost_adjustment_assumptions_csv": str(assumptions_csv),
            "cost_adjusted_mode_review_items_csv": str(review_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "strategy_mode_cost_adjusted_comparison_pack_json": comparison_json,
        "strategy_mode_cost_adjusted_comparison_pack_txt": comparison_txt,
        "cost_adjustment_assumptions_csv": assumptions_csv,
        "cost_adjusted_mode_review_items_csv": review_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_cost_adjusted_mode_comparison_report(
    *,
    result_comparison_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[CostAdjustedModeComparisonReport, dict[str, Path]]:
    report = build_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=result_comparison_pack_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_cost_adjusted_mode_comparison_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build strategy mode cost-adjusted comparison pack."
    )
    parser.add_argument(
        "--result-comparison-pack",
        default=(
            "reports/paper_trading/"
            "strategy_mode_backtest_result_comparison_pack/"
            "strategy_mode_backtest_result_comparison_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/strategy_mode_cost_adjusted_comparison_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=Path(args.result_comparison_pack),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE strategy mode cost-adjusted comparison pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future strategy selection review: {report.ready_for_future_strategy_selection_review}")
    print(f"Review items: {report.review_item_count}")
    print(f"Cost-adjusted comparison pack: {outputs['strategy_mode_cost_adjusted_comparison_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
