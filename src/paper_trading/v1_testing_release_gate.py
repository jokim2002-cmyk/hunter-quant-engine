"""
v1.0 Testing Edition release gate.

Module GGG in the fast-track v1.0 Testing Edition path.

This module validates the recorded-data paper backtest readiness evidence and
release documentation before the final v1.0 Testing Edition close.

It does not connect to brokers, request live market data, place real orders,
use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPECTED_READINESS_STAGES = {
    "one_command_backtest_runner",
    "backtest_acceptance_gate",
}

REQUIRED_RELEASE_DOC_PHRASES = {
    "v0.6-recorded-data-backtest-readiness",
    "paper-only backtest readiness gate",
    "LONG = CE BUY paper plan only",
    "SHORT = PE BUY paper plan only",
    "NEUTRAL = no trade",
    "No option selling",
    "No broker orders",
    "No real money",
    "No profitability claim",
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
class V1TestingReleaseGateIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class V1TestingReleaseGateReport:
    generated_at_utc: str
    backtest_readiness_path: str
    release_doc_path: str
    output_directory: str
    status: str
    accepted_for_future_v1_testing_release_close: bool
    min_stage_count_required: int
    min_passed_stage_count_required: int
    readiness_stage_count: int
    readiness_passed_stage_count: int
    readiness_warning_stage_count: int
    readiness_failed_stage_count: int
    final_backtest_report_path: str
    final_metrics_path: str
    final_trade_ledger_path: str
    safety_notice: str
    issues: list[V1TestingReleaseGateIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation v1.0 Testing Edition release gate only. This gate "
        "validates recorded replay paper backtest readiness evidence. It does "
        "not connect to brokers, request live market data, place real orders, "
        "use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> V1TestingReleaseGateIssue:
    return V1TestingReleaseGateIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[V1TestingReleaseGateIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _to_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _load_json_object(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[V1TestingReleaseGateIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "backtest_readiness_missing",
                1,
                f"Backtest readiness report missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "backtest_readiness_invalid_json",
                1,
                f"Backtest readiness JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "backtest_readiness_invalid_shape",
                1,
                "Backtest readiness report must be a JSON object.",
            )
        ]

    return payload, []


def _release_doc_issues(release_doc_path: Path) -> list[V1TestingReleaseGateIssue]:
    if not release_doc_path.exists():
        return [
            _issue(
                "fail",
                "release_doc_missing",
                1,
                f"v0.6 release document missing: {release_doc_path}",
            )
        ]

    text = release_doc_path.read_text(encoding="utf-8")
    missing = [phrase for phrase in REQUIRED_RELEASE_DOC_PHRASES if phrase not in text]
    if missing:
        return [
            _issue(
                "fail",
                "release_doc_required_phrases_missing",
                len(missing),
                "v0.6 release document is missing required safety/release phrases.",
            )
        ]

    return []


def _readiness_issues(
    readiness: Mapping[str, Any] | None,
    *,
    min_stage_count: int,
    min_passed_stage_count: int,
    allow_warnings: bool,
    require_final_outputs_exist: bool,
) -> list[V1TestingReleaseGateIssue]:
    if readiness is None:
        return []

    issues: list[V1TestingReleaseGateIssue] = []

    status = str(readiness.get("status") or "unknown").lower()
    ready = bool(readiness.get("ready_for_future_v1_testing_release_gate"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "backtest_readiness_warn",
                1,
                "Backtest readiness status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "backtest_readiness_not_pass",
                1,
                f"Backtest readiness status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "backtest_readiness_not_ready",
                1,
                "Backtest readiness report is not ready for future v1.0 testing release gate.",
            )
        )

    forbidden = _forbidden(readiness)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "backtest_readiness_forbidden_fields",
                len(forbidden),
                "Backtest readiness contains forbidden broker/order/real-money fields.",
            )
        )

    stage_count = _to_int(readiness.get("stage_count")) or 0
    passed_stage_count = _to_int(readiness.get("passed_stage_count")) or 0
    warning_stage_count = _to_int(readiness.get("warning_stage_count")) or 0
    failed_stage_count = _to_int(readiness.get("failed_stage_count")) or 0
    accepted_stage_count = (
        passed_stage_count + warning_stage_count
        if allow_warnings
        else passed_stage_count
    )

    if stage_count < min_stage_count:
        issues.append(
            _issue(
                "fail",
                "insufficient_readiness_stages",
                min_stage_count - stage_count,
                f"Readiness stage count below minimum. Required={min_stage_count}, actual={stage_count}.",
            )
        )

    if accepted_stage_count < min_passed_stage_count:
        issues.append(
            _issue(
                "fail",
                "insufficient_accepted_readiness_stages",
                min_passed_stage_count - accepted_stage_count,
                (
                    "Readiness accepted-stage count below minimum. "
                    f"Required={min_passed_stage_count}, actual={accepted_stage_count}."
                ),
            )
        )

    if failed_stage_count:
        issues.append(
            _issue(
                "fail",
                "failed_readiness_stages_present",
                failed_stage_count,
                "Backtest readiness report contains failed stages.",
            )
        )

    stages = readiness.get("stages")
    if not isinstance(stages, list):
        issues.append(
            _issue(
                "fail",
                "readiness_stages_missing",
                1,
                "Backtest readiness report must include stages list.",
            )
        )
    else:
        stage_names = {
            str(stage.get("stage_name") or "")
            for stage in stages
            if isinstance(stage, Mapping)
        }
        missing_stages = EXPECTED_READINESS_STAGES - stage_names
        if missing_stages:
            issues.append(
                _issue(
                    "fail",
                    "expected_readiness_stages_missing",
                    len(missing_stages),
                    "Backtest readiness report is missing expected readiness stages.",
                )
            )

        not_ready_count = sum(
            1
            for stage in stages
            if isinstance(stage, Mapping) and not bool(stage.get("ready"))
        )
        if not_ready_count:
            issues.append(
                _issue(
                    "fail",
                    "readiness_stage_not_ready",
                    not_ready_count,
                    "Backtest readiness contains stages that are not ready.",
                )
            )

    final_paths = [
        readiness.get("final_backtest_report_path"),
        readiness.get("final_metrics_path"),
        readiness.get("final_trade_ledger_path"),
    ]

    missing_final_fields = [path for path in final_paths if not str(path or "").strip()]
    if missing_final_fields:
        issues.append(
            _issue(
                "fail",
                "final_backtest_output_paths_missing",
                len(missing_final_fields),
                "Backtest readiness must include final report, metrics, and ledger paths.",
            )
        )

    if require_final_outputs_exist:
        missing_outputs = [
            str(path)
            for path in final_paths
            if str(path or "").strip() and not Path(str(path)).exists()
        ]
        if missing_outputs:
            issues.append(
                _issue(
                    "fail",
                    "final_backtest_outputs_missing_on_disk",
                    len(missing_outputs),
                    "Backtest final output files are missing on disk.",
                )
            )

    return issues


def build_v1_testing_release_gate_report(
    *,
    backtest_readiness_path: Path,
    release_doc_path: Path,
    output_dir: Path,
    min_stage_count: int = 2,
    min_passed_stage_count: int = 2,
    allow_warnings: bool = False,
    require_final_outputs_exist: bool = True,
) -> V1TestingReleaseGateReport:
    min_stage_count = max(min_stage_count, 0)
    min_passed_stage_count = max(min_passed_stage_count, 0)

    issues: list[V1TestingReleaseGateIssue] = []

    readiness, load_issues = _load_json_object(backtest_readiness_path)
    issues.extend(load_issues)
    issues.extend(_release_doc_issues(release_doc_path))
    issues.extend(
        _readiness_issues(
            readiness,
            min_stage_count=min_stage_count,
            min_passed_stage_count=min_passed_stage_count,
            allow_warnings=allow_warnings,
            require_final_outputs_exist=require_final_outputs_exist,
        )
    )

    status = _status(issues)

    return V1TestingReleaseGateReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        backtest_readiness_path=str(backtest_readiness_path),
        release_doc_path=str(release_doc_path),
        output_directory=str(output_dir),
        status=status,
        accepted_for_future_v1_testing_release_close=status in {"pass", "warn"},
        min_stage_count_required=min_stage_count,
        min_passed_stage_count_required=min_passed_stage_count,
        readiness_stage_count=_to_int((readiness or {}).get("stage_count")) or 0,
        readiness_passed_stage_count=_to_int((readiness or {}).get("passed_stage_count")) or 0,
        readiness_warning_stage_count=_to_int((readiness or {}).get("warning_stage_count")) or 0,
        readiness_failed_stage_count=_to_int((readiness or {}).get("failed_stage_count")) or 0,
        final_backtest_report_path=str((readiness or {}).get("final_backtest_report_path") or ""),
        final_metrics_path=str((readiness or {}).get("final_metrics_path") or ""),
        final_trade_ledger_path=str((readiness or {}).get("final_trade_ledger_path") or ""),
        safety_notice=safety_notice(),
        issues=issues,
    )


def write_v1_testing_release_gate_report(
    report: V1TestingReleaseGateReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    gate_json = output_dir / "v1_testing_release_gate.json"
    gate_txt = output_dir / "v1_testing_release_gate.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]

    gate_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "HQE v1.0 Testing Edition Release Gate",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Accepted for future v1.0 testing release close: {report.accepted_for_future_v1_testing_release_close}",
        "",
        "Backtest readiness:",
        f"- Stage count: {report.readiness_stage_count}",
        f"- Passed stages: {report.readiness_passed_stage_count}",
        f"- Warning stages: {report.readiness_warning_stage_count}",
        f"- Failed stages: {report.readiness_failed_stage_count}",
        "",
        "Final backtest outputs:",
        f"- Backtest report: {report.final_backtest_report_path}",
        f"- Metrics: {report.final_metrics_path}",
        f"- Trade ledger: {report.final_trade_ledger_path}",
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

    if not report.issues:
        lines.append("- PASS: v1.0 Testing Edition release gate is accepted for future release close.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {gate_json}",
            f"- {gate_txt}",
            f"- {manifest_json}",
        ]
    )
    gate_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "v1_testing_release_gate",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted_for_future_v1_testing_release_close": report.accepted_for_future_v1_testing_release_close,
        "readiness_stage_count": report.readiness_stage_count,
        "readiness_passed_stage_count": report.readiness_passed_stage_count,
        "readiness_warning_stage_count": report.readiness_warning_stage_count,
        "readiness_failed_stage_count": report.readiness_failed_stage_count,
        "final_backtest_report_path": report.final_backtest_report_path,
        "final_metrics_path": report.final_metrics_path,
        "final_trade_ledger_path": report.final_trade_ledger_path,
        "safety_notice": report.safety_notice,
        "outputs": {
            "v1_testing_release_gate_json": str(gate_json),
            "v1_testing_release_gate_txt": str(gate_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "v1_testing_release_gate_json": gate_json,
        "v1_testing_release_gate_txt": gate_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_v1_testing_release_gate_report(
    *,
    backtest_readiness_path: Path,
    release_doc_path: Path,
    output_dir: Path,
    min_stage_count: int = 2,
    min_passed_stage_count: int = 2,
    allow_warnings: bool = False,
    require_final_outputs_exist: bool = True,
) -> tuple[V1TestingReleaseGateReport, dict[str, Path]]:
    report = build_v1_testing_release_gate_report(
        backtest_readiness_path=backtest_readiness_path,
        release_doc_path=release_doc_path,
        output_dir=output_dir,
        min_stage_count=min_stage_count,
        min_passed_stage_count=min_passed_stage_count,
        allow_warnings=allow_warnings,
        require_final_outputs_exist=require_final_outputs_exist,
    )
    outputs = write_v1_testing_release_gate_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate v1.0 Testing Edition release gate evidence."
    )
    parser.add_argument(
        "--backtest-readiness",
        default=(
            "reports/paper_trading/"
            "recorded_data_backtest_readiness_gate/"
            "backtest_readiness_gate.json"
        ),
    )
    parser.add_argument(
        "--release-doc",
        default="docs/V0_6_RECORDED_DATA_BACKTEST_READINESS_RELEASE.md",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/v1_testing_release_gate",
    )
    parser.add_argument("--min-stage-count", type=int, default=2)
    parser.add_argument("--min-passed-stage-count", type=int, default=2)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument(
        "--skip-final-output-existence-check",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_v1_testing_release_gate_report(
        backtest_readiness_path=Path(args.backtest_readiness),
        release_doc_path=Path(args.release_doc),
        output_dir=Path(args.output_dir),
        min_stage_count=args.min_stage_count,
        min_passed_stage_count=args.min_passed_stage_count,
        allow_warnings=args.allow_warnings,
        require_final_outputs_exist=not args.skip_final_output_existence_check,
    )

    print("HQE v1.0 Testing Edition release gate completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Accepted for future v1.0 testing release close: "
        f"{report.accepted_for_future_v1_testing_release_close}"
    )
    print(f"v1 testing release gate report: {outputs['v1_testing_release_gate_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
