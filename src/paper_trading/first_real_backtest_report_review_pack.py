"""
First real backtest report review pack.

Module OOO in the post-v1.0 Real Backtest Usage Sprint.

This module reads the first real backtest output verification pack and builds
an operator review pack for report, metrics, ledger, readiness, release gate,
and handoff evidence.

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
    "ledger",
    "metrics",
    "report",
    "readiness",
    "release_gate",
    "operator_handoff",
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
class ReportReviewChecklistItem:
    item_index: int
    category: str
    action: str
    required: bool
    expected_result: str


@dataclass(frozen=True)
class ReportReviewEvidencePath:
    category: str
    path: str
    exists: bool


@dataclass(frozen=True)
class ReportReviewIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class FirstBacktestReportReviewPack:
    generated_at_utc: str
    verification_pack_path: str
    output_directory: str
    status: str
    ready_for_future_strategy_tuning_review: bool
    selected_dataset_path: str
    safety_notice: str
    evidence_path_count: int
    checklist_item_count: int
    issues: list[ReportReviewIssue]
    evidence_paths: list[ReportReviewEvidencePath]
    checklist: list[ReportReviewChecklistItem]


def safety_notice() -> str:
    return (
        "Paper/simulation first real backtest report review pack only. This pack "
        "helps review recorded-data paper backtest outputs. It does not connect "
        "to brokers, request live market data, place real orders, use real "
        "money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> ReportReviewIssue:
    return ReportReviewIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[ReportReviewIssue]) -> str:
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


def _load_verification_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[ReportReviewIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "output_verification_pack_missing",
                1,
                f"First real backtest output verification pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "output_verification_pack_invalid_json",
                1,
                f"Output verification pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "output_verification_pack_invalid_shape",
                1,
                "Output verification pack must be a JSON object.",
            )
        ]

    return payload, []


def _verification_issues(
    verification: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[ReportReviewIssue]:
    if verification is None:
        return []

    issues: list[ReportReviewIssue] = []

    status = str(verification.get("status") or "unknown").lower()
    ready = bool(verification.get("ready_for_future_first_backtest_report_review"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "output_verification_pack_warn",
                1,
                "Output verification pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "output_verification_pack_not_pass",
                1,
                f"Output verification pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "output_verification_pack_not_ready",
                1,
                "Output verification pack is not ready for first backtest report review.",
            )
        )

    forbidden = _forbidden(verification)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "output_verification_pack_forbidden_fields",
                len(forbidden),
                "Output verification pack contains forbidden broker/order/real-money fields.",
            )
        )

    verification_issues = verification.get("issues")
    if isinstance(verification_issues, list):
        fail_count = sum(
            1
            for item in verification_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "output_verification_pack_contains_fail_issues",
                    fail_count,
                    "Output verification pack contains fail issues.",
                )
            )

    checks = verification.get("output_checks")
    if not isinstance(checks, list) or not checks:
        issues.append(
            _issue(
                "fail",
                "output_checks_missing",
                1,
                "Output verification pack must include output_checks.",
            )
        )

    return issues


def _evidence_paths(
    verification: Mapping[str, Any] | None,
) -> list[ReportReviewEvidencePath]:
    if verification is None:
        return []

    raw_checks = verification.get("output_checks")
    if not isinstance(raw_checks, list):
        return []

    evidence: list[ReportReviewEvidencePath] = []

    for item in raw_checks:
        if not isinstance(item, Mapping):
            continue

        category = str(item.get("category") or "other")
        path = str(item.get("output_path") or "").strip()
        if not path:
            continue

        if category in REQUIRED_REVIEW_CATEGORIES:
            evidence.append(
                ReportReviewEvidencePath(
                    category=category,
                    path=path,
                    exists=Path(path).exists(),
                )
            )

    return evidence


def _evidence_issues(
    evidence_paths: Sequence[ReportReviewEvidencePath],
    *,
    require_evidence_exists: bool,
) -> list[ReportReviewIssue]:
    issues: list[ReportReviewIssue] = []

    categories = {path.category for path in evidence_paths}
    missing_categories = REQUIRED_REVIEW_CATEGORIES - categories
    if missing_categories:
        issues.append(
            _issue(
                "fail",
                "required_review_evidence_categories_missing",
                len(missing_categories),
                "Required review evidence categories are missing.",
            )
        )

    missing_files = [path for path in evidence_paths if not path.exists]
    if require_evidence_exists and missing_files:
        issues.append(
            _issue(
                "fail",
                "required_review_evidence_files_missing_on_disk",
                len(missing_files),
                "Required review evidence files are missing on disk.",
            )
        )

    return issues


def _checklist() -> list[ReportReviewChecklistItem]:
    raw_items = [
        (
            "report",
            "Open the backtest report and confirm it says paper/simulation only.",
            "Report is reviewed without treating it as profitability proof.",
        ),
        (
            "metrics",
            "Open metrics and review trade count, win/loss/flat counts, drawdown reference, and expectancy reference.",
            "Metrics are reviewed as simulated references only.",
        ),
        (
            "ledger",
            "Open ledger and check each row uses CE BUY for LONG and PE BUY for SHORT.",
            "No option selling or broker execution is present.",
        ),
        (
            "quality",
            "Confirm quality gate did not fail on malformed OHLC, timestamps, or duplicate rows.",
            "Dataset quality is acceptable for review.",
        ),
        (
            "readiness",
            "Open backtest readiness gate and confirm status is pass.",
            "Readiness evidence is accepted for review.",
        ),
        (
            "release_gate",
            "Open v1 testing release gate and confirm it remains paper-only.",
            "Release gate evidence remains safe.",
        ),
        (
            "operator_handoff",
            "Open operator handoff pack and confirm safety checklist is present.",
            "Operator checklist is complete.",
        ),
        (
            "strategy_review",
            "Mark obvious bad behavior for future strategy tuning without changing live execution.",
            "Tuning candidates are identified without profitability claims.",
        ),
        (
            "safety",
            "Confirm no broker order IDs, exchange order IDs, or real-money fields appear.",
            "Broker/live execution remains disabled.",
        ),
        (
            "next_step",
            "Use this review pack as input to the future strategy tuning baseline module.",
            "Ready for future strategy tuning review.",
        ),
    ]

    return [
        ReportReviewChecklistItem(
            item_index=index,
            category=category,
            action=action,
            required=True,
            expected_result=expected_result,
        )
        for index, (category, action, expected_result) in enumerate(raw_items, start=1)
    ]


def build_first_backtest_report_review_pack(
    *,
    verification_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
    require_evidence_exists: bool = True,
) -> FirstBacktestReportReviewPack:
    verification, load_issues = _load_verification_pack(verification_pack_path)

    issues: list[ReportReviewIssue] = []
    issues.extend(load_issues)
    issues.extend(_verification_issues(verification, allow_warnings=allow_warnings))

    evidence_paths = _evidence_paths(verification)
    issues.extend(
        _evidence_issues(
            evidence_paths,
            require_evidence_exists=require_evidence_exists,
        )
    )

    checklist = _checklist()
    status = _status(issues)

    return FirstBacktestReportReviewPack(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        verification_pack_path=str(verification_pack_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_strategy_tuning_review=status in {"pass", "warn"},
        selected_dataset_path=str((verification or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        evidence_path_count=len(evidence_paths),
        checklist_item_count=len(checklist),
        issues=issues,
        evidence_paths=evidence_paths,
        checklist=checklist,
    )


def write_first_backtest_report_review_pack(
    report: FirstBacktestReportReviewPack,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    review_json = output_dir / "first_real_backtest_report_review_pack.json"
    review_txt = output_dir / "first_real_backtest_report_review_pack.txt"
    checklist_csv = output_dir / "first_real_backtest_report_review_checklist.csv"
    evidence_csv = output_dir / "first_real_backtest_report_review_evidence_paths.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["evidence_paths"] = [asdict(path) for path in report.evidence_paths]
    data["checklist"] = [asdict(item) for item in report.checklist]
    review_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with checklist_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item_index", "category", "required", "action", "expected_result"])
        for item in report.checklist:
            writer.writerow(
                [
                    item.item_index,
                    item.category,
                    item.required,
                    item.action,
                    item.expected_result,
                ]
            )

    with evidence_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["category", "exists", "path"])
        for evidence_path in report.evidence_paths:
            writer.writerow(
                [
                    evidence_path.category,
                    evidence_path.exists,
                    evidence_path.path,
                ]
            )

    lines = [
        "HQE First Real Backtest Report Review Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future strategy tuning review: {report.ready_for_future_strategy_tuning_review}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Evidence paths: {report.evidence_path_count}",
        f"Checklist items: {report.checklist_item_count}",
        "",
        "Evidence paths:",
    ]

    if not report.evidence_paths:
        lines.append("- No report review evidence paths were found.")
    else:
        for evidence_path in report.evidence_paths:
            lines.append(
                f"- {evidence_path.category}: exists={evidence_path.exists}, path={evidence_path.path}"
            )

    lines.extend(["", "Review checklist:"])
    for item in report.checklist:
        lines.append(
            f"{item.item_index}. [{item.category}] {item.action} -> {item.expected_result}"
        )

    lines.extend(
        [
            "",
            "Safety:",
            "- LONG = CE BUY paper plan only.",
            "- SHORT = PE BUY paper plan only.",
            "- NEUTRAL = no trade.",
            "- No option selling.",
            "- No broker orders.",
            "- No live market data.",
            "- No real money.",
            "- This report is not a profitability claim.",
            "",
            "Issues:",
        ]
    )

    if not report.issues:
        lines.append("- PASS: First real backtest report review pack is ready for future strategy tuning review.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {review_json}",
            f"- {review_txt}",
            f"- {checklist_csv}",
            f"- {evidence_csv}",
            f"- {manifest_json}",
        ]
    )
    review_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "first_real_backtest_report_review_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_strategy_tuning_review": report.ready_for_future_strategy_tuning_review,
        "selected_dataset_path": report.selected_dataset_path,
        "evidence_path_count": report.evidence_path_count,
        "checklist_item_count": report.checklist_item_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "first_real_backtest_report_review_pack_json": str(review_json),
            "first_real_backtest_report_review_pack_txt": str(review_txt),
            "first_real_backtest_report_review_checklist_csv": str(checklist_csv),
            "first_real_backtest_report_review_evidence_paths_csv": str(evidence_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "first_real_backtest_report_review_pack_json": review_json,
        "first_real_backtest_report_review_pack_txt": review_txt,
        "first_real_backtest_report_review_checklist_csv": checklist_csv,
        "first_real_backtest_report_review_evidence_paths_csv": evidence_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_first_backtest_report_review_pack(
    *,
    verification_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
    require_evidence_exists: bool = True,
) -> tuple[FirstBacktestReportReviewPack, dict[str, Path]]:
    report = build_first_backtest_report_review_pack(
        verification_pack_path=verification_pack_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
        require_evidence_exists=require_evidence_exists,
    )
    outputs = write_first_backtest_report_review_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build first real backtest report review pack."
    )
    parser.add_argument(
        "--verification-pack",
        default=(
            "reports/paper_trading/"
            "first_real_backtest_output_verification_pack/"
            "first_real_backtest_output_verification_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/first_real_backtest_report_review_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--skip-evidence-existence-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_first_backtest_report_review_pack(
        verification_pack_path=Path(args.verification_pack),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
        require_evidence_exists=not args.skip_evidence_existence_check,
    )

    print("HQE first real backtest report review pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future strategy tuning review: {report.ready_for_future_strategy_tuning_review}")
    print(f"Evidence paths: {report.evidence_path_count}")
    print(f"Review pack: {outputs['first_real_backtest_report_review_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
