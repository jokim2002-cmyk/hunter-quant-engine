"""
v1.0 Testing Edition operator handoff pack.

Module HHH in the fast-track v1.0 Testing Edition path.

This module converts the v1 testing release gate report into an operator-facing
handoff pack: run order, safety checklist, expected outputs, and release-close
readiness notes.

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
class OperatorHandoffIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class OperatorChecklistItem:
    item_index: int
    category: str
    action: str
    required: bool
    expected_result: str


@dataclass(frozen=True)
class OperatorHandoffPackReport:
    generated_at_utc: str
    v1_testing_release_gate_path: str
    output_directory: str
    status: str
    ready_for_future_v1_release_notes: bool
    safety_notice: str
    release_gate_status: str
    release_gate_accepted: bool
    final_backtest_report_path: str
    final_metrics_path: str
    final_trade_ledger_path: str
    checklist_item_count: int
    issues: list[OperatorHandoffIssue]
    checklist: list[OperatorChecklistItem]


def safety_notice() -> str:
    return (
        "Paper/simulation v1.0 Testing Edition operator handoff only. This pack "
        "is for reviewing recorded replay paper backtest evidence. It does not "
        "connect to brokers, request live market data, place real orders, use "
        "real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> OperatorHandoffIssue:
    return OperatorHandoffIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[OperatorHandoffIssue]) -> str:
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


def _load_gate(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[OperatorHandoffIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "v1_testing_release_gate_missing",
                1,
                f"v1 testing release gate report missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "v1_testing_release_gate_invalid_json",
                1,
                f"v1 testing release gate JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "v1_testing_release_gate_invalid_shape",
                1,
                "v1 testing release gate report must be a JSON object.",
            )
        ]

    return payload, []


def _gate_issues(
    gate: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
    require_final_outputs_exist: bool,
) -> list[OperatorHandoffIssue]:
    if gate is None:
        return []

    issues: list[OperatorHandoffIssue] = []

    status = str(gate.get("status") or "unknown").lower()
    accepted = bool(gate.get("accepted_for_future_v1_testing_release_close"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "v1_testing_release_gate_warn",
                1,
                "v1 testing release gate status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "v1_testing_release_gate_not_pass",
                1,
                f"v1 testing release gate status is not pass: {status}.",
            )
        )

    if not accepted:
        issues.append(
            _issue(
                "fail",
                "v1_testing_release_gate_not_accepted",
                1,
                "v1 testing release gate is not accepted for future release close.",
            )
        )

    forbidden = _forbidden(gate)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "v1_testing_release_gate_forbidden_fields",
                len(forbidden),
                "v1 testing release gate contains forbidden broker/order/real-money fields.",
            )
        )

    final_paths = [
        gate.get("final_backtest_report_path"),
        gate.get("final_metrics_path"),
        gate.get("final_trade_ledger_path"),
    ]

    missing_path_fields = [path for path in final_paths if not str(path or "").strip()]
    if missing_path_fields:
        issues.append(
            _issue(
                "fail",
                "final_output_paths_missing",
                len(missing_path_fields),
                "Release gate must include final backtest report, metrics, and ledger paths.",
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
                    "final_outputs_missing_on_disk",
                    len(missing_outputs),
                    "Final output files are missing on disk.",
                )
            )

    gate_issues = gate.get("issues")
    if isinstance(gate_issues, list):
        fail_gate_issue_count = sum(
            1
            for item in gate_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_gate_issue_count:
            issues.append(
                _issue(
                    "fail",
                    "release_gate_contains_fail_issues",
                    fail_gate_issue_count,
                    "Release gate report contains fail issues.",
                )
            )

    return issues


def _checklist() -> list[OperatorChecklistItem]:
    raw_items = [
        (
            "run_order",
            ".\\hqe_recorded_data_backtest_readiness_gate.bat",
            "Backtest readiness report is created.",
        ),
        (
            "run_order",
            ".\\hqe_v1_testing_release_gate.bat",
            "v1 testing release gate report is created.",
        ),
        (
            "operator_review",
            "Open the final backtest report and confirm it says paper/simulation only.",
            "Report reviewed without treating results as profitability proof.",
        ),
        (
            "operator_review",
            "Open the metrics and ledger reports and confirm they are simulated references.",
            "Metrics and ledger reviewed as paper-only evidence.",
        ),
        (
            "safety",
            "Confirm LONG maps to CE BUY paper plan only.",
            "No SHORT CE, no option selling.",
        ),
        (
            "safety",
            "Confirm SHORT maps to PE BUY paper plan only.",
            "No SHORT PE selling, no futures/equity execution.",
        ),
        (
            "safety",
            "Confirm NEUTRAL maps to no trade.",
            "Neutral bars do not produce trades.",
        ),
        (
            "safety",
            "Confirm no broker orders or real-money actions are present.",
            "Broker execution remains disabled.",
        ),
        (
            "release",
            "Confirm v0.6 tag exists before v1.0 release close.",
            "v0.6 recorded-data backtest readiness is frozen.",
        ),
        (
            "release",
            "Use this pack for final v1.0 Testing Edition release notes.",
            "Ready for future release-note close module.",
        ),
    ]

    return [
        OperatorChecklistItem(
            item_index=index,
            category=category,
            action=action,
            required=True,
            expected_result=expected,
        )
        for index, (category, action, expected) in enumerate(raw_items, start=1)
    ]


def build_operator_handoff_pack_report(
    *,
    v1_testing_release_gate_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
    require_final_outputs_exist: bool = True,
) -> OperatorHandoffPackReport:
    gate, load_issues = _load_gate(v1_testing_release_gate_path)
    issues: list[OperatorHandoffIssue] = []
    issues.extend(load_issues)
    issues.extend(
        _gate_issues(
            gate,
            allow_warnings=allow_warnings,
            require_final_outputs_exist=require_final_outputs_exist,
        )
    )

    status = _status(issues)
    checklist = _checklist()

    return OperatorHandoffPackReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        v1_testing_release_gate_path=str(v1_testing_release_gate_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_future_v1_release_notes=status in {"pass", "warn"},
        safety_notice=safety_notice(),
        release_gate_status=str((gate or {}).get("status") or ""),
        release_gate_accepted=bool((gate or {}).get("accepted_for_future_v1_testing_release_close")),
        final_backtest_report_path=str((gate or {}).get("final_backtest_report_path") or ""),
        final_metrics_path=str((gate or {}).get("final_metrics_path") or ""),
        final_trade_ledger_path=str((gate or {}).get("final_trade_ledger_path") or ""),
        checklist_item_count=len(checklist),
        issues=issues,
        checklist=checklist,
    )


def write_operator_handoff_pack_report(
    report: OperatorHandoffPackReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    pack_json = output_dir / "v1_testing_operator_handoff_pack.json"
    pack_txt = output_dir / "v1_testing_operator_handoff_pack.txt"
    checklist_csv = output_dir / "v1_testing_operator_checklist.csv"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["checklist"] = [asdict(item) for item in report.checklist]

    pack_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

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

    lines = [
        "HQE v1.0 Testing Edition Operator Handoff Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future v1.0 release notes: {report.ready_for_future_v1_release_notes}",
        f"Release gate status: {report.release_gate_status}",
        f"Release gate accepted: {report.release_gate_accepted}",
        "",
        "Final evidence outputs:",
        f"- Backtest report: {report.final_backtest_report_path}",
        f"- Metrics: {report.final_metrics_path}",
        f"- Trade ledger: {report.final_trade_ledger_path}",
        "",
        "Operator checklist:",
    ]

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
        lines.append("- PASS: Operator handoff pack is ready for future v1.0 release notes.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {pack_json}",
            f"- {pack_txt}",
            f"- {checklist_csv}",
            f"- {manifest_json}",
        ]
    )
    pack_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "v1_testing_operator_handoff_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_v1_release_notes": report.ready_for_future_v1_release_notes,
        "release_gate_status": report.release_gate_status,
        "release_gate_accepted": report.release_gate_accepted,
        "checklist_item_count": report.checklist_item_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "v1_testing_operator_handoff_pack_json": str(pack_json),
            "v1_testing_operator_handoff_pack_txt": str(pack_txt),
            "v1_testing_operator_checklist_csv": str(checklist_csv),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "v1_testing_operator_handoff_pack_json": pack_json,
        "v1_testing_operator_handoff_pack_txt": pack_txt,
        "v1_testing_operator_checklist_csv": checklist_csv,
        "manifest_json": manifest_json,
    }


def build_and_write_operator_handoff_pack_report(
    *,
    v1_testing_release_gate_path: Path,
    output_dir: Path,
    allow_warnings: bool = False,
    require_final_outputs_exist: bool = True,
) -> tuple[OperatorHandoffPackReport, dict[str, Path]]:
    report = build_operator_handoff_pack_report(
        v1_testing_release_gate_path=v1_testing_release_gate_path,
        output_dir=output_dir,
        allow_warnings=allow_warnings,
        require_final_outputs_exist=require_final_outputs_exist,
    )
    outputs = write_operator_handoff_pack_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build v1.0 Testing Edition operator handoff pack."
    )
    parser.add_argument(
        "--v1-testing-release-gate",
        default="reports/paper_trading/v1_testing_release_gate/v1_testing_release_gate.json",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/v1_testing_operator_handoff_pack",
    )
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--skip-final-output-existence-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_operator_handoff_pack_report(
        v1_testing_release_gate_path=Path(args.v1_testing_release_gate),
        output_dir=Path(args.output_dir),
        allow_warnings=args.allow_warnings,
        require_final_outputs_exist=not args.skip_final_output_existence_check,
    )

    print("HQE v1.0 Testing Edition operator handoff pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future v1.0 release notes: {report.ready_for_future_v1_release_notes}")
    print(f"Operator handoff pack: {outputs['v1_testing_operator_handoff_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
