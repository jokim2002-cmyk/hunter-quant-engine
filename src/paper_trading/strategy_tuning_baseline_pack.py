"""
Strategy tuning baseline pack.

Module PPP in the post-v1.0 Real Backtest Usage Sprint.

This module reads the first real backtest report review pack and creates a
safe tuning baseline. It does not modify strategy logic; it only documents
what to inspect next.

It does not connect to brokers, request live market data, place real orders,
use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_REVIEW_CATEGORIES = {
    "report",
    "metrics",
    "ledger",
    "readiness",
    "release_gate",
    "operator_handoff",
}

TUNING_CANDIDATE_CATEGORIES = {
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
class StrategyTuningCandidate:
    candidate_index: int
    category: str
    current_scope: str
    review_question: str
    safe_next_action: str


@dataclass(frozen=True)
class StrategyTuningBaselineIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class StrategyTuningBaselineReport:
    generated_at_utc: str
    report_review_pack_path: str
    output_directory: str
    status: str
    ready_for_future_strategy_mode_comparison: bool
    selected_dataset_path: str
    safety_notice: str
    tuning_candidate_count: int
    evidence_category_count: int
    issues: list[StrategyTuningBaselineIssue]
    tuning_candidates: list[StrategyTuningCandidate]
    evidence_categories: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation strategy tuning baseline pack only. This pack reviews "
        "recorded-data paper backtest evidence and prepares safe tuning questions. "
        "It does not connect to brokers, request live market data, place real "
        "orders, use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> StrategyTuningBaselineIssue:
    return StrategyTuningBaselineIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[StrategyTuningBaselineIssue]) -> str:
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


def _load_review_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[StrategyTuningBaselineIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "report_review_pack_missing",
                1,
                f"First real backtest report review pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "report_review_pack_invalid_json",
                1,
                f"Report review pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "report_review_pack_invalid_shape",
                1,
                "Report review pack must be a JSON object.",
            )
        ]

    return payload, []


def _review_pack_issues(
    review: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[StrategyTuningBaselineIssue]:
    if review is None:
        return []

    issues: list[StrategyTuningBaselineIssue] = []

    status = str(review.get("status") or "unknown").lower()
    ready = bool(review.get("ready_for_future_strategy_tuning_review"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "report_review_pack_warn",
                1,
                "Report review pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "report_review_pack_not_pass",
                1,
                f"Report review pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "report_review_pack_not_ready",
                1,
                "Report review pack is not ready for future strategy tuning review.",
            )
        )

    forbidden = _forbidden(review)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "report_review_pack_forbidden_fields",
                len(forbidden),
                "Report review pack contains forbidden broker/order/real-money fields.",
            )
        )

    review_issues = review.get("issues")
    if isinstance(review_issues, list):
        fail_count = sum(
            1
            for item in review_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "report_review_pack_contains_fail_issues",
                    fail_count,
                    "Report review pack contains fail issues.",
                )
            )

    return issues


def _evidence_categories(review: Mapping[str, Any] | None) -> list[str]:
    if review is None:
        return []

    raw_paths = review.get("evidence_paths")
    if not isinstance(raw_paths, list):
        return []

    categories = sorted(
        {
            str(item.get("category") or "")
            for item in raw_paths
            if isinstance(item, Mapping) and str(item.get("category") or "").strip()
        }
    )
    return categories


def _evidence_issues(categories: Sequence[str]) -> list[StrategyTuningBaselineIssue]:
    category_set = set(categories)
    missing = REQUIRED_REVIEW_CATEGORIES - category_set

    if missing:
        return [
            _issue(
                "fail",
                "required_tuning_evidence_categories_missing",
                len(missing),
                "Required evidence categories are missing before strategy tuning baseline.",
            )
        ]

    return []


def _tuning_candidates() -> list[StrategyTuningCandidate]:
    raw_candidates = [
        (
            "decision_threshold",
            "Decision audit threshold that decides LONG, SHORT, or NEUTRAL.",
            "Are too many tiny moves being converted into trades?",
            "Compare strict, balanced, and relaxed thresholds in a future paper-only mode comparison.",
        ),
        (
            "max_holding_bars",
            "Paper fill/exit simulator maximum holding bars.",
            "Are exits too early or too late in recorded-data paper evidence?",
            "Review holding-bars distribution before changing defaults.",
        ),
        (
            "stop_loss_points",
            "Paper-only stop-loss reference points.",
            "Are simulated losses clustering around avoidable conditions?",
            "Compare stop variants only in paper backtest reports.",
        ),
        (
            "target_points",
            "Paper-only target reference points.",
            "Are targets too close or too far for the recorded dataset?",
            "Compare target variants only through paper metrics and ledger evidence.",
        ),
        (
            "neutral_filter",
            "NEUTRAL decision behavior.",
            "Should low-conviction bars produce no trade more often?",
            "Increase no-trade filtering only after report review evidence.",
        ),
        (
            "quality_filter",
            "Dataset quality and replay sanity filters.",
            "Are bad timestamps, duplicate bars, or malformed OHLC affecting decisions?",
            "Tighten data-quality gates before strategy changes.",
        ),
        (
            "cost_assumption",
            "Paper-only cost/slippage assumption placeholder.",
            "Would results change materially after estimated costs?",
            "Add cost-adjusted report module before any live thinking.",
        ),
        (
            "session_window",
            "Market session/window filter placeholder.",
            "Are poor trades concentrated in specific time windows?",
            "Compare paper-only session windows after baseline report review.",
        ),
    ]

    return [
        StrategyTuningCandidate(
            candidate_index=index,
            category=category,
            current_scope=current_scope,
            review_question=review_question,
            safe_next_action=safe_next_action,
        )
        for index, (category, current_scope, review_question, safe_next_action)
        in enumerate(raw_candidates, start=1)
    ]


def build_strategy_tuning_baseline_report(
    *,
    report_review_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> StrategyTuningBaselineReport:
    review, load_issues = _load_review_pack(report_review_pack_path)

    issues: list[StrategyTuningBaselineIssue] = []
    issues.extend(load_issues)
    issues.extend(_review_pack_issues(review, allow_warnings=allow_warnings))

    categories = _evidence_categories(review)
    issues.extend(_evidence_issues(categories))

    candidates = _tuning_candidates()
    status = _status(issues)

    return StrategyTuningBaselineReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        report_review_pack_path=str(report_review_pack_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_strategy_mode_comparison=status in {"pass", "warn"},
        selected_dataset_path=str((review or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        tuning_candidate_count=len(candidates),
        evidence_category_count=len(categories),
        issues=issues,
        tuning_candidates=candidates,
        evidence_categories=categories,
    )


def write_strategy_tuning_baseline_report(
    report: StrategyTuningBaselineReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_json = output_dir / "strategy_tuning_baseline_pack.json"
    baseline_txt = output_dir / "strategy_tuning_baseline_pack.txt"
    candidates_csv = output_dir / "strategy_tuning_candidates.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["tuning_candidates"] = [asdict(candidate) for candidate in report.tuning_candidates]
    baseline_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with candidates_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "candidate_index",
                "category",
                "current_scope",
                "review_question",
                "safe_next_action",
            ]
        )
        for candidate in report.tuning_candidates:
            writer.writerow(
                [
                    candidate.candidate_index,
                    candidate.category,
                    candidate.current_scope,
                    candidate.review_question,
                    candidate.safe_next_action,
                ]
            )

    lines = [
        "HQE Strategy Tuning Baseline Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future strategy mode comparison: {report.ready_for_future_strategy_mode_comparison}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Evidence categories: {report.evidence_category_count}",
        f"Tuning candidates: {report.tuning_candidate_count}",
        "",
        "Evidence categories:",
    ]

    if not report.evidence_categories:
        lines.append("- No evidence categories found.")
    else:
        for category in report.evidence_categories:
            lines.append(f"- {category}")

    lines.extend(["", "Tuning candidates:"])
    for candidate in report.tuning_candidates:
        lines.append(
            (
                f"{candidate.candidate_index}. [{candidate.category}] "
                f"{candidate.review_question} -> {candidate.safe_next_action}"
            )
        )

    lines.extend(
        [
            "",
            "Safety:",
            "- This pack does not change strategy logic.",
            "- This pack does not claim profitability.",
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
        lines.append("- PASS: Strategy tuning baseline is ready for future paper-only mode comparison.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {baseline_json}",
            f"- {baseline_txt}",
            f"- {candidates_csv}",
            f"- {manifest_json}",
        ]
    )
    baseline_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "strategy_tuning_baseline_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_strategy_mode_comparison": report.ready_for_future_strategy_mode_comparison,
        "selected_dataset_path": report.selected_dataset_path,
        "tuning_candidate_count": report.tuning_candidate_count,
        "evidence_category_count": report.evidence_category_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "strategy_tuning_baseline_pack_json": str(baseline_json),
            "strategy_tuning_baseline_pack_txt": str(baseline_txt),
            "strategy_tuning_candidates_csv": str(candidates_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "strategy_tuning_baseline_pack_json": baseline_json,
        "strategy_tuning_baseline_pack_txt": baseline_txt,
        "strategy_tuning_candidates_csv": candidates_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_tuning_baseline_report(
    *,
    report_review_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
) -> tuple[StrategyTuningBaselineReport, dict[str, Path]]:
    report = build_strategy_tuning_baseline_report(
        report_review_pack_path=report_review_pack_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
    )
    outputs = write_strategy_tuning_baseline_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build strategy tuning baseline pack from first backtest review evidence."
    )
    parser.add_argument(
        "--report-review-pack",
        default=(
            "reports/paper_trading/"
            "first_real_backtest_report_review_pack/"
            "first_real_backtest_report_review_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/strategy_tuning_baseline_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_strategy_tuning_baseline_report(
        report_review_pack_path=Path(args.report_review_pack),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
    )

    print("HQE strategy tuning baseline pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future strategy mode comparison: {report.ready_for_future_strategy_mode_comparison}")
    print(f"Tuning candidates: {report.tuning_candidate_count}")
    print(f"Baseline pack: {outputs['strategy_tuning_baseline_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
