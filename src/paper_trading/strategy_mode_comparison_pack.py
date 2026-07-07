"""
Strategy mode comparison pack.

Module QQQ in the post-v1.0 Real Backtest Usage Sprint.

This module reads the strategy tuning baseline pack and writes paper-only
strict, balanced, and relaxed mode definitions for future comparison.

It does not modify strategy logic, connect to brokers, request live market
data, place real orders, use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_TUNING_CANDIDATES = {
    "decision_threshold",
    "max_holding_bars",
    "stop_loss_points",
    "target_points",
    "neutral_filter",
    "quality_filter",
    "cost_assumption",
    "session_window",
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
class StrategyModeDefinition:
    mode_name: str
    description: str
    decision_threshold: float
    max_holding_bars: int
    stop_loss_points: float
    target_points: float
    neutral_filter: str
    quality_filter: str
    cost_assumption: str
    session_window: str


@dataclass(frozen=True)
class StrategyModeComparisonIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class StrategyModeComparisonReport:
    generated_at_utc: str
    baseline_pack_path: str
    output_directory: str
    status: str
    ready_for_future_paper_mode_backtest: bool
    selected_dataset_path: str
    safety_notice: str
    mode_count: int
    tuning_candidate_count: int
    issues: list[StrategyModeComparisonIssue]
    modes: list[StrategyModeDefinition]
    tuning_candidate_categories: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation strategy mode comparison pack only. This pack defines "
        "strict, balanced, and relaxed paper-only mode settings for future "
        "recorded-data comparison. It does not modify strategy logic, does "
        "not connect to brokers, request live market data, place real orders, use real "
        "money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> StrategyModeComparisonIssue:
    return StrategyModeComparisonIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[StrategyModeComparisonIssue]) -> str:
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


def _load_baseline_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[StrategyModeComparisonIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "strategy_tuning_baseline_pack_missing",
                1,
                f"Strategy tuning baseline pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "strategy_tuning_baseline_pack_invalid_json",
                1,
                f"Strategy tuning baseline pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "strategy_tuning_baseline_pack_invalid_shape",
                1,
                "Strategy tuning baseline pack must be a JSON object.",
            )
        ]

    return payload, []


def _baseline_issues(
    baseline: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[StrategyModeComparisonIssue]:
    if baseline is None:
        return []

    issues: list[StrategyModeComparisonIssue] = []

    status = str(baseline.get("status") or "unknown").lower()
    ready = bool(baseline.get("ready_for_future_strategy_mode_comparison"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "strategy_tuning_baseline_pack_warn",
                1,
                "Strategy tuning baseline pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "strategy_tuning_baseline_pack_not_pass",
                1,
                f"Strategy tuning baseline pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "strategy_tuning_baseline_pack_not_ready",
                1,
                "Strategy tuning baseline pack is not ready for future strategy mode comparison.",
            )
        )

    forbidden = _forbidden(baseline)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "strategy_tuning_baseline_pack_forbidden_fields",
                len(forbidden),
                "Strategy tuning baseline pack contains forbidden broker/order/real-money fields.",
            )
        )

    baseline_issues = baseline.get("issues")
    if isinstance(baseline_issues, list):
        fail_count = sum(
            1
            for item in baseline_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "strategy_tuning_baseline_pack_contains_fail_issues",
                    fail_count,
                    "Strategy tuning baseline pack contains fail issues.",
                )
            )

    return issues


def _candidate_categories(
    baseline: Mapping[str, Any] | None,
) -> list[str]:
    if baseline is None:
        return []

    raw_candidates = baseline.get("tuning_candidates")
    if not isinstance(raw_candidates, list):
        return []

    categories = sorted(
        {
            str(item.get("category") or "")
            for item in raw_candidates
            if isinstance(item, Mapping) and str(item.get("category") or "").strip()
        }
    )
    return categories


def _candidate_issues(
    candidate_categories: Sequence[str],
) -> list[StrategyModeComparisonIssue]:
    category_set = set(candidate_categories)
    missing = REQUIRED_TUNING_CANDIDATES - category_set

    if missing:
        return [
            _issue(
                "fail",
                "required_strategy_mode_candidate_categories_missing",
                len(missing),
                "Required tuning candidate categories are missing before mode comparison.",
            )
        ]

    return []


def _mode_definitions() -> list[StrategyModeDefinition]:
    return [
        StrategyModeDefinition(
            mode_name="strict",
            description="Fewer paper trades, stronger no-trade filtering, tighter quality requirements.",
            decision_threshold=1.50,
            max_holding_bars=3,
            stop_loss_points=8.0,
            target_points=12.0,
            neutral_filter="high",
            quality_filter="strict",
            cost_assumption="cost_reference_required",
            session_window="core_session_only",
        ),
        StrategyModeDefinition(
            mode_name="balanced",
            description="Baseline paper mode for first comparison after report review.",
            decision_threshold=1.00,
            max_holding_bars=5,
            stop_loss_points=10.0,
            target_points=15.0,
            neutral_filter="medium",
            quality_filter="standard",
            cost_assumption="cost_reference_required",
            session_window="standard_session",
        ),
        StrategyModeDefinition(
            mode_name="relaxed",
            description="More paper trades, lower decision threshold, still CE/PE buy-only.",
            decision_threshold=0.70,
            max_holding_bars=7,
            stop_loss_points=12.0,
            target_points=18.0,
            neutral_filter="low",
            quality_filter="standard",
            cost_assumption="cost_reference_required",
            session_window="standard_session",
        ),
    ]


def build_strategy_mode_comparison_report(
    *,
    baseline_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> StrategyModeComparisonReport:
    baseline, load_issues = _load_baseline_pack(baseline_pack_path)

    issues: list[StrategyModeComparisonIssue] = []
    issues.extend(load_issues)
    issues.extend(_baseline_issues(baseline, allow_warnings=allow_warnings))

    candidate_categories = _candidate_categories(baseline)
    issues.extend(_candidate_issues(candidate_categories))

    modes = _mode_definitions()
    status = _status(issues)

    return StrategyModeComparisonReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        baseline_pack_path=str(baseline_pack_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_paper_mode_backtest=status in {"pass", "warn"},
        selected_dataset_path=str((baseline or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        mode_count=len(modes),
        tuning_candidate_count=len(candidate_categories),
        issues=issues,
        modes=modes,
        tuning_candidate_categories=candidate_categories,
    )


def write_strategy_mode_comparison_report(
    report: StrategyModeComparisonReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    comparison_json = output_dir / "strategy_mode_comparison_pack.json"
    comparison_txt = output_dir / "strategy_mode_comparison_pack.txt"
    modes_csv = output_dir / "strategy_mode_definitions.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["modes"] = [asdict(mode) for mode in report.modes]
    comparison_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with modes_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "mode_name",
                "description",
                "decision_threshold",
                "max_holding_bars",
                "stop_loss_points",
                "target_points",
                "neutral_filter",
                "quality_filter",
                "cost_assumption",
                "session_window",
            ]
        )
        for mode in report.modes:
            writer.writerow(
                [
                    mode.mode_name,
                    mode.description,
                    mode.decision_threshold,
                    mode.max_holding_bars,
                    mode.stop_loss_points,
                    mode.target_points,
                    mode.neutral_filter,
                    mode.quality_filter,
                    mode.cost_assumption,
                    mode.session_window,
                ]
            )

    lines = [
        "HQE Strategy Mode Comparison Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future paper mode backtest: {report.ready_for_future_paper_mode_backtest}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Modes: {report.mode_count}",
        f"Tuning candidate categories: {report.tuning_candidate_count}",
        "",
        "Mode definitions:",
    ]

    for mode in report.modes:
        lines.append(
            (
                f"- {mode.mode_name}: threshold={mode.decision_threshold}, "
                f"max_holding_bars={mode.max_holding_bars}, "
                f"stop_loss={mode.stop_loss_points}, target={mode.target_points}, "
                f"neutral_filter={mode.neutral_filter}, quality_filter={mode.quality_filter}"
            )
        )

    lines.extend(["", "Tuning candidate categories:"])
    if not report.tuning_candidate_categories:
        lines.append("- No tuning candidate categories found.")
    else:
        for category in report.tuning_candidate_categories:
            lines.append(f"- {category}")

    lines.extend(
        [
            "",
            "Safety:",
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
        lines.append("- PASS: Strategy mode comparison pack is ready for future paper-only mode backtest.")
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
            f"- {modes_csv}",
            f"- {manifest_json}",
        ]
    )
    comparison_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "strategy_mode_comparison_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_paper_mode_backtest": report.ready_for_future_paper_mode_backtest,
        "selected_dataset_path": report.selected_dataset_path,
        "mode_count": report.mode_count,
        "tuning_candidate_count": report.tuning_candidate_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "strategy_mode_comparison_pack_json": str(comparison_json),
            "strategy_mode_comparison_pack_txt": str(comparison_txt),
            "strategy_mode_definitions_csv": str(modes_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "strategy_mode_comparison_pack_json": comparison_json,
        "strategy_mode_comparison_pack_txt": comparison_txt,
        "strategy_mode_definitions_csv": modes_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_mode_comparison_report(
    *,
    baseline_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[StrategyModeComparisonReport, dict[str, Path]]:
    report = build_strategy_mode_comparison_report(
        baseline_pack_path=baseline_pack_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_strategy_mode_comparison_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build strategy mode comparison pack from tuning baseline."
    )
    parser.add_argument(
        "--baseline-pack",
        default=(
            "reports/paper_trading/"
            "strategy_tuning_baseline_pack/"
            "strategy_tuning_baseline_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/strategy_mode_comparison_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_strategy_mode_comparison_report(
        baseline_pack_path=Path(args.baseline_pack),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE strategy mode comparison pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future paper mode backtest: {report.ready_for_future_paper_mode_backtest}")
    print(f"Modes: {report.mode_count}")
    print(f"Comparison pack: {outputs['strategy_mode_comparison_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
