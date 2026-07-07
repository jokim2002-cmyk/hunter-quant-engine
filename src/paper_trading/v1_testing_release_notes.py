"""
v1.0 Testing Edition release notes pack.

Module III in the fast-track v1.0 Testing Edition path.

This module converts the v1 testing operator handoff pack into release-notes
evidence for the final v1.0 Testing Edition release candidate gate.

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
class ReleaseNotesIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class ReleaseNotesSection:
    section_index: int
    title: str
    content: str


@dataclass(frozen=True)
class V1TestingReleaseNotesReport:
    generated_at_utc: str
    operator_handoff_pack_path: str
    output_directory: str
    release_version: str
    status: str
    ready_for_future_v1_release_candidate_gate: bool
    safety_notice: str
    handoff_status: str
    handoff_ready: bool
    final_backtest_report_path: str
    final_metrics_path: str
    final_trade_ledger_path: str
    section_count: int
    issues: list[ReleaseNotesIssue]
    sections: list[ReleaseNotesSection]


def safety_notice() -> str:
    return (
        "Paper/simulation v1.0 Testing Edition release notes only. These notes "
        "summarize recorded replay paper backtest evidence. This module does not connect "
        "to brokers, request live market data, place real orders, use real money, "
        "or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> ReleaseNotesIssue:
    return ReleaseNotesIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[ReleaseNotesIssue]) -> str:
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


def _load_handoff(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[ReleaseNotesIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "operator_handoff_pack_missing",
                1,
                f"v1 testing operator handoff pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "operator_handoff_pack_invalid_json",
                1,
                f"Operator handoff pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "operator_handoff_pack_invalid_shape",
                1,
                "Operator handoff pack must be a JSON object.",
            )
        ]

    return payload, []


def _handoff_issues(
    handoff: Mapping[str, Any] | None,
    *,
    allow_warnings: bool,
    require_final_outputs_exist: bool,
) -> list[ReleaseNotesIssue]:
    if handoff is None:
        return []

    issues: list[ReleaseNotesIssue] = []

    status = str(handoff.get("status") or "unknown").lower()
    ready = bool(handoff.get("ready_for_future_v1_release_notes"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "operator_handoff_pack_warn",
                1,
                "Operator handoff pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "operator_handoff_pack_not_pass",
                1,
                f"Operator handoff pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "operator_handoff_pack_not_ready",
                1,
                "Operator handoff pack is not ready for future v1 release notes.",
            )
        )

    forbidden = _forbidden(handoff)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "operator_handoff_pack_forbidden_fields",
                len(forbidden),
                "Operator handoff pack contains forbidden broker/order/real-money fields.",
            )
        )

    final_paths = [
        handoff.get("final_backtest_report_path"),
        handoff.get("final_metrics_path"),
        handoff.get("final_trade_ledger_path"),
    ]

    missing_fields = [path for path in final_paths if not str(path or "").strip()]
    if missing_fields:
        issues.append(
            _issue(
                "fail",
                "handoff_final_output_paths_missing",
                len(missing_fields),
                "Handoff pack must include final report, metrics, and ledger paths.",
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
                    "handoff_final_outputs_missing_on_disk",
                    len(missing_outputs),
                    "Handoff final output files are missing on disk.",
                )
            )

    handoff_issues = handoff.get("issues")
    if isinstance(handoff_issues, list):
        fail_count = sum(
            1
            for item in handoff_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "handoff_contains_fail_issues",
                    fail_count,
                    "Operator handoff pack contains fail issues.",
                )
            )

    checklist = handoff.get("checklist")
    if not isinstance(checklist, list) or not checklist:
        issues.append(
            _issue(
                "fail",
                "operator_checklist_missing",
                1,
                "Operator handoff pack must include a non-empty checklist.",
            )
        )

    return issues


def _sections(handoff: Mapping[str, Any] | None) -> list[ReleaseNotesSection]:
    final_report = str((handoff or {}).get("final_backtest_report_path") or "")
    metrics = str((handoff or {}).get("final_metrics_path") or "")
    ledger = str((handoff or {}).get("final_trade_ledger_path") or "")

    raw_sections = [
        (
            "Release summary",
            (
                "HQE v1.0 Testing Edition is a paper/simulation-only testing release. "
                "It validates recorded-data replay, CE/PE option-buy paper planning, "
                "paper fill/exit simulation, ledger, metrics, report, gates, and operator handoff."
            ),
        ),
        (
            "Backtest evidence outputs",
            (
                f"Final backtest report: {final_report}\n"
                f"Final metrics: {metrics}\n"
                f"Final trade ledger: {ledger}"
            ),
        ),
        (
            "Trading safety contract",
            (
                "LONG = CE BUY paper plan only.\n"
                "SHORT = PE BUY paper plan only.\n"
                "NEUTRAL = no trade.\n"
                "No option selling.\n"
                "No broker orders.\n"
                "No live market data dependency.\n"
                "No real money."
            ),
        ),
        (
            "Release limitations",
            (
                "This release is not a profitability claim. It is not real broker PnL. "
                "It does not execute live orders, and generated reports remain ignored evidence files."
            ),
        ),
        (
            "Next release step",
            (
                "Use these release notes as input to the future v1.0 release candidate gate "
                "and final v1.0 Testing Edition tag close."
            ),
        ),
    ]

    return [
        ReleaseNotesSection(section_index=index, title=title, content=content)
        for index, (title, content) in enumerate(raw_sections, start=1)
    ]


def build_v1_testing_release_notes_report(
    *,
    operator_handoff_pack_path: Path,
    output_dir: Path,
    release_version: str = "v1.0-testing-edition",
    allow_warnings: bool = False,
    require_final_outputs_exist: bool = True,
) -> V1TestingReleaseNotesReport:
    handoff, load_issues = _load_handoff(operator_handoff_pack_path)
    issues: list[ReleaseNotesIssue] = []
    issues.extend(load_issues)
    issues.extend(
        _handoff_issues(
            handoff,
            allow_warnings=allow_warnings,
            require_final_outputs_exist=require_final_outputs_exist,
        )
    )

    status = _status(issues)
    sections = _sections(handoff)

    return V1TestingReleaseNotesReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        operator_handoff_pack_path=str(operator_handoff_pack_path),
        output_directory=str(output_dir),
        release_version=release_version,
        status=status,
        ready_for_future_v1_release_candidate_gate=status in {"pass", "warn"},
        safety_notice=safety_notice(),
        handoff_status=str((handoff or {}).get("status") or ""),
        handoff_ready=bool((handoff or {}).get("ready_for_future_v1_release_notes")),
        final_backtest_report_path=str((handoff or {}).get("final_backtest_report_path") or ""),
        final_metrics_path=str((handoff or {}).get("final_metrics_path") or ""),
        final_trade_ledger_path=str((handoff or {}).get("final_trade_ledger_path") or ""),
        section_count=len(sections),
        issues=issues,
        sections=sections,
    )


def write_v1_testing_release_notes_report(
    report: V1TestingReleaseNotesReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    notes_json = output_dir / "v1_testing_release_notes.json"
    notes_md = output_dir / "v1_testing_release_notes.md"
    notes_txt = output_dir / "v1_testing_release_notes.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["sections"] = [asdict(section) for section in report.sections]
    notes_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    md_lines = [
        "# HQE v1.0 Testing Edition Release Notes",
        "",
        report.safety_notice,
        "",
        f"Release version: `{report.release_version}`",
        f"Status: `{report.status}`",
        f"Ready for future v1 release candidate gate: `{report.ready_for_future_v1_release_candidate_gate}`",
        "",
    ]
    for section in report.sections:
        md_lines.extend([f"## {section.title}", "", section.content, ""])

    md_lines.extend(
        [
            "## Safety boundary",
            "",
            "- LONG = CE BUY paper plan only.",
            "- SHORT = PE BUY paper plan only.",
            "- NEUTRAL = no trade.",
            "- No option selling.",
            "- No broker orders.",
            "- No live market data.",
            "- No real money.",
            "- This report is not a profitability claim.",
            "",
            "## Issues",
            "",
        ]
    )
    if not report.issues:
        md_lines.append("- PASS: v1.0 Testing Edition release notes are ready for release candidate gate.")
    else:
        for issue in report.issues:
            md_lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    notes_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    txt_lines = [
        "HQE v1.0 Testing Edition Release Notes",
        "",
        report.safety_notice,
        "",
        f"Release version: {report.release_version}",
        f"Status: {report.status}",
        f"Ready for future v1 release candidate gate: {report.ready_for_future_v1_release_candidate_gate}",
        "",
        "Sections:",
    ]
    for section in report.sections:
        txt_lines.extend(["", f"{section.section_index}. {section.title}", section.content])

    txt_lines.extend(
        [
            "",
            "This release is paper/simulation only.",
            "This release does not use real money.",
            "This release is not a profitability claim.",
            "",
            "Outputs:",
            f"- {notes_json}",
            f"- {notes_md}",
            f"- {notes_txt}",
            f"- {manifest_json}",
        ]
    )
    notes_txt.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "v1_testing_release_notes",
        "generated_at_utc": report.generated_at_utc,
        "release_version": report.release_version,
        "status": report.status,
        "ready_for_future_v1_release_candidate_gate": report.ready_for_future_v1_release_candidate_gate,
        "section_count": report.section_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "v1_testing_release_notes_json": str(notes_json),
            "v1_testing_release_notes_md": str(notes_md),
            "v1_testing_release_notes_txt": str(notes_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "v1_testing_release_notes_json": notes_json,
        "v1_testing_release_notes_md": notes_md,
        "v1_testing_release_notes_txt": notes_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_v1_testing_release_notes_report(
    *,
    operator_handoff_pack_path: Path,
    output_dir: Path,
    release_version: str = "v1.0-testing-edition",
    allow_warnings: bool = False,
    require_final_outputs_exist: bool = True,
) -> tuple[V1TestingReleaseNotesReport, dict[str, Path]]:
    report = build_v1_testing_release_notes_report(
        operator_handoff_pack_path=operator_handoff_pack_path,
        output_dir=output_dir,
        release_version=release_version,
        allow_warnings=allow_warnings,
        require_final_outputs_exist=require_final_outputs_exist,
    )
    outputs = write_v1_testing_release_notes_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build v1.0 Testing Edition release notes evidence."
    )
    parser.add_argument(
        "--operator-handoff-pack",
        default=(
            "reports/paper_trading/"
            "v1_testing_operator_handoff_pack/"
            "v1_testing_operator_handoff_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/v1_testing_release_notes",
    )
    parser.add_argument("--release-version", default="v1.0-testing-edition")
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--skip-final-output-existence-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_v1_testing_release_notes_report(
        operator_handoff_pack_path=Path(args.operator_handoff_pack),
        output_dir=Path(args.output_dir),
        release_version=args.release_version,
        allow_warnings=args.allow_warnings,
        require_final_outputs_exist=not args.skip_final_output_existence_check,
    )

    print("HQE v1.0 Testing Edition release notes pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(
        "Ready for future v1 release candidate gate: "
        f"{report.ready_for_future_v1_release_candidate_gate}"
    )
    print(f"Release notes: {outputs['v1_testing_release_notes_md']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

