"""
First real backtest output verification pack.

Module NNN in the post-v1.0 Real Backtest Usage Sprint.

This module reads the first real dataset backtest run pack and verifies whether
the expected paper backtest output files exist after the operator run.

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
class BacktestOutputCheck:
    output_index: int
    output_path: str
    exists: bool
    category: str
    required: bool


@dataclass(frozen=True)
class BacktestOutputVerificationIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class BacktestOutputVerificationReport:
    generated_at_utc: str
    first_run_pack_path: str
    output_directory: str
    status: str
    ready_for_future_first_backtest_report_review: bool
    selected_dataset_path: str
    safety_notice: str
    expected_output_count: int
    existing_output_count: int
    missing_output_count: int
    issues: list[BacktestOutputVerificationIssue]
    output_checks: list[BacktestOutputCheck]


def safety_notice() -> str:
    return (
        "Paper/simulation first real backtest output verification pack only. "
        "This pack verifies expected recorded-data paper backtest files on disk. "
        "It does not connect to brokers, request live market data, place real "
        "orders, use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> BacktestOutputVerificationIssue:
    return BacktestOutputVerificationIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[BacktestOutputVerificationIssue]) -> str:
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


def _load_first_run_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[BacktestOutputVerificationIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "first_real_backtest_run_pack_missing",
                1,
                f"First real dataset backtest run pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "first_real_backtest_run_pack_invalid_json",
                1,
                f"First real backtest run pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "first_real_backtest_run_pack_invalid_shape",
                1,
                "First real backtest run pack must be a JSON object.",
            )
        ]

    return payload, []


def _category(path_text: str) -> str:
    lower = path_text.replace("\\", "/").lower()

    if "inventory" in lower:
        return "inventory"
    if "replay_dataset" in lower or lower.endswith("dataset.json"):
        return "dataset"
    if "quality_gate" in lower:
        return "quality"
    if "trade_ledger" in lower:
        return "ledger"
    if "metrics" in lower:
        return "metrics"
    if "backtest_report" in lower:
        return "report"
    if "backtest_readiness" in lower:
        return "readiness"
    if "v1_testing_release_gate" in lower:
        return "release_gate"
    if "operator_handoff" in lower:
        return "operator_handoff"
    return "other"


def _expected_outputs_from_pack(
    pack: Mapping[str, Any] | None,
) -> list[str]:
    if pack is None:
        return []

    raw_outputs = pack.get("expected_outputs")
    if isinstance(raw_outputs, list):
        return [str(item) for item in raw_outputs if str(item).strip()]

    return []


def _pack_issues(
    pack: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
) -> list[BacktestOutputVerificationIssue]:
    if pack is None:
        return []

    issues: list[BacktestOutputVerificationIssue] = []

    status = str(pack.get("status") or "unknown").lower()
    ready = bool(pack.get("ready_for_operator_first_real_backtest_run"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "first_real_backtest_run_pack_warn",
                1,
                "First real backtest run pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "first_real_backtest_run_pack_not_pass",
                1,
                f"First real backtest run pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "first_real_backtest_run_pack_not_ready",
                1,
                "First real backtest run pack is not ready for operator first real backtest run.",
            )
        )

    if _forbidden(pack):
        issues.append(
            _issue(
                "fail",
                "first_real_backtest_run_pack_forbidden_fields",
                len(_forbidden(pack)),
                "First real backtest run pack contains forbidden broker/order/real-money fields.",
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
                    "first_real_backtest_run_pack_contains_fail_issues",
                    fail_count,
                    "First real backtest run pack contains fail issues.",
                )
            )

    expected_outputs = _expected_outputs_from_pack(pack)
    if not expected_outputs:
        issues.append(
            _issue(
                "fail",
                "expected_outputs_missing",
                1,
                "First real backtest run pack must include expected_outputs.",
            )
        )

    return issues


def _build_checks(expected_outputs: Sequence[str]) -> list[BacktestOutputCheck]:
    checks: list[BacktestOutputCheck] = []

    for index, output_path in enumerate(expected_outputs, start=1):
        path_text = str(output_path)
        checks.append(
            BacktestOutputCheck(
                output_index=index,
                output_path=path_text,
                exists=Path(path_text).exists(),
                category=_category(path_text),
                required=True,
            )
        )

    return checks


def build_backtest_output_verification_report(
    *,
    first_run_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
    require_expected_outputs_exist: bool = True,
) -> BacktestOutputVerificationReport:
    pack, load_issues = _load_first_run_pack(first_run_pack_path)
    issues: list[BacktestOutputVerificationIssue] = []
    issues.extend(load_issues)
    issues.extend(_pack_issues(pack, allow_warnings=allow_warnings))

    expected_outputs = _expected_outputs_from_pack(pack)
    checks = _build_checks(expected_outputs)
    missing_checks = [check for check in checks if check.required and not check.exists]

    if require_expected_outputs_exist and missing_checks:
        issues.append(
            _issue(
                "fail",
                "expected_backtest_outputs_missing_on_disk",
                len(missing_checks),
                "One or more expected first real backtest output files are missing on disk.",
            )
        )

    existing_count = sum(1 for check in checks if check.exists)
    missing_count = sum(1 for check in checks if not check.exists)
    status = _status(issues)

    return BacktestOutputVerificationReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        first_run_pack_path=str(first_run_pack_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_first_backtest_report_review=status in {"pass", "warn"},
        selected_dataset_path=str((pack or {}).get("selected_dataset_path") or ""),
        safety_notice=safety_notice(),
        expected_output_count=len(checks),
        existing_output_count=existing_count,
        missing_output_count=missing_count,
        issues=issues,
        output_checks=checks,
    )


def write_backtest_output_verification_report(
    report: BacktestOutputVerificationReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    verification_json = output_dir / "first_real_backtest_output_verification_pack.json"
    verification_txt = output_dir / "first_real_backtest_output_verification_pack.txt"
    checks_csv = output_dir / "first_real_backtest_output_checks.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["output_checks"] = [asdict(check) for check in report.output_checks]
    verification_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    with checks_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["output_index", "category", "required", "exists", "output_path"])
        for check in report.output_checks:
            writer.writerow(
                [
                    check.output_index,
                    check.category,
                    check.required,
                    check.exists,
                    check.output_path,
                ]
            )

    lines = [
        "HQE First Real Backtest Output Verification Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future first backtest report review: {report.ready_for_future_first_backtest_report_review}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Expected outputs: {report.expected_output_count}",
        f"Existing outputs: {report.existing_output_count}",
        f"Missing outputs: {report.missing_output_count}",
        "",
        "Output checks:",
    ]

    if not report.output_checks:
        lines.append("- No expected outputs were provided.")
    else:
        for check in report.output_checks:
            lines.append(
                f"- {check.category}: exists={check.exists}, required={check.required}, path={check.output_path}"
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
        lines.append("- PASS: First real backtest outputs are ready for future report review.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {verification_json}",
            f"- {verification_txt}",
            f"- {checks_csv}",
            f"- {manifest_json}",
        ]
    )
    verification_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "first_real_backtest_output_verification_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_first_backtest_report_review": report.ready_for_future_first_backtest_report_review,
        "selected_dataset_path": report.selected_dataset_path,
        "expected_output_count": report.expected_output_count,
        "existing_output_count": report.existing_output_count,
        "missing_output_count": report.missing_output_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "first_real_backtest_output_verification_pack_json": str(verification_json),
            "first_real_backtest_output_verification_pack_txt": str(verification_txt),
            "first_real_backtest_output_checks_csv": str(checks_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "first_real_backtest_output_verification_pack_json": verification_json,
        "first_real_backtest_output_verification_pack_txt": verification_txt,
        "first_real_backtest_output_checks_csv": checks_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_backtest_output_verification_report(
    *,
    first_run_pack_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
    require_expected_outputs_exist: bool = True,
) -> tuple[BacktestOutputVerificationReport, dict[str, Path]]:
    report = build_backtest_output_verification_report(
        first_run_pack_path=first_run_pack_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
        require_expected_outputs_exist=require_expected_outputs_exist,
    )
    outputs = write_backtest_output_verification_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify first real dataset paper backtest output files."
    )
    parser.add_argument(
        "--first-run-pack",
        default=(
            "reports/paper_trading/"
            "first_real_dataset_backtest_run_pack/"
            "first_real_dataset_backtest_run_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/first_real_backtest_output_verification_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--skip-output-existence-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_backtest_output_verification_report(
        first_run_pack_path=Path(args.first_run_pack),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
        require_expected_outputs_exist=not args.skip_output_existence_check,
    )

    print("HQE first real backtest output verification pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Expected outputs: {report.expected_output_count}")
    print(f"Existing outputs: {report.existing_output_count}")
    print(f"Missing outputs: {report.missing_output_count}")
    print(f"Verification pack: {outputs['first_real_backtest_output_verification_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
