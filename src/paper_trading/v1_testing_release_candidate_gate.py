"""
v1.0 Testing Edition release candidate gate.

Module JJJ in the fast-track v1.0 Testing Edition path.

This module validates the v1.0 Testing Edition release notes evidence before
the final release/tag close.

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


REQUIRED_SECTION_TITLES = {
    "Release summary",
    "Backtest evidence outputs",
    "Trading safety contract",
    "Release limitations",
    "Next release step",
}

REQUIRED_RELEASE_NOTE_PHRASES = {
    "LONG = CE BUY paper plan only",
    "SHORT = PE BUY paper plan only",
    "NEUTRAL = no trade",
    "No option selling",
    "No broker orders",
    "No real money",
    "not a profitability claim",
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
class ReleaseCandidateIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class ReleaseCandidateGateReport:
    generated_at_utc: str
    release_notes_path: str
    output_directory: str
    release_version: str
    status: str
    ready_for_final_v1_testing_release_close: bool
    min_section_count_required: int
    section_count: int
    safety_notice: str
    release_notes_status: str
    release_notes_ready: bool
    final_backtest_report_path: str
    final_metrics_path: str
    final_trade_ledger_path: str
    issues: list[ReleaseCandidateIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation v1.0 Testing Edition release candidate gate only. "
        "This gate validates release notes evidence for final testing-release "
        "close. It does not connect to brokers, request live market data, place "
        "real orders, use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> ReleaseCandidateIssue:
    return ReleaseCandidateIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[ReleaseCandidateIssue]) -> str:
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


def _load_release_notes(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[ReleaseCandidateIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "release_notes_missing",
                1,
                f"v1 testing release notes report missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "release_notes_invalid_json",
                1,
                f"v1 testing release notes JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "release_notes_invalid_shape",
                1,
                "v1 testing release notes report must be a JSON object.",
            )
        ]

    return payload, []


def _release_notes_text(notes: Mapping[str, Any]) -> str:
    pieces: list[str] = []

    for key in (
        "safety_notice",
        "release_version",
        "status",
        "final_backtest_report_path",
        "final_metrics_path",
        "final_trade_ledger_path",
    ):
        value = notes.get(key)
        if value is not None:
            pieces.append(str(value))

    sections = notes.get("sections")
    if isinstance(sections, list):
        for section in sections:
            if isinstance(section, Mapping):
                pieces.append(str(section.get("title") or ""))
                pieces.append(str(section.get("content") or ""))

    return "\n".join(pieces)


def _release_notes_issues(
    notes: Mapping[str, Any] | None,
    *,
    min_section_count: int,
    allow_warnings: bool,
    require_final_outputs_exist: bool,
) -> list[ReleaseCandidateIssue]:
    if notes is None:
        return []

    issues: list[ReleaseCandidateIssue] = []

    status = str(notes.get("status") or "unknown").lower()
    ready = bool(notes.get("ready_for_future_v1_release_candidate_gate"))

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "release_notes_warn",
                1,
                "Release notes status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "release_notes_not_pass",
                1,
                f"Release notes status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "release_notes_not_ready",
                1,
                "Release notes are not ready for future v1 release candidate gate.",
            )
        )

    forbidden = _forbidden(notes)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "release_notes_forbidden_fields",
                len(forbidden),
                "Release notes contain forbidden broker/order/real-money fields.",
            )
        )

    section_count = _to_int(notes.get("section_count")) or 0
    if section_count < min_section_count:
        issues.append(
            _issue(
                "fail",
                "insufficient_release_note_sections",
                min_section_count - section_count,
                f"Release notes section count below minimum. Required={min_section_count}, actual={section_count}.",
            )
        )

    sections = notes.get("sections")
    if not isinstance(sections, list) or not sections:
        issues.append(
            _issue(
                "fail",
                "release_note_sections_missing",
                1,
                "Release notes must include sections.",
            )
        )
    else:
        titles = {
            str(section.get("title") or "")
            for section in sections
            if isinstance(section, Mapping)
        }
        missing_titles = REQUIRED_SECTION_TITLES - titles
        if missing_titles:
            issues.append(
                _issue(
                    "fail",
                    "required_release_note_sections_missing",
                    len(missing_titles),
                    "Release notes are missing required sections.",
                )
            )

    text = _release_notes_text(notes)
    missing_phrases = [
        phrase
        for phrase in REQUIRED_RELEASE_NOTE_PHRASES
        if phrase.lower() not in text.lower()
    ]
    if missing_phrases:
        issues.append(
            _issue(
                "fail",
                "required_release_note_phrases_missing",
                len(missing_phrases),
                "Release notes are missing required safety/release phrases.",
            )
        )

    final_paths = [
        notes.get("final_backtest_report_path"),
        notes.get("final_metrics_path"),
        notes.get("final_trade_ledger_path"),
    ]

    missing_fields = [path for path in final_paths if not str(path or "").strip()]
    if missing_fields:
        issues.append(
            _issue(
                "fail",
                "release_note_final_output_paths_missing",
                len(missing_fields),
                "Release notes must include final report, metrics, and ledger paths.",
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
                    "release_note_final_outputs_missing_on_disk",
                    len(missing_outputs),
                    "Release note final output files are missing on disk.",
                )
            )

    note_issues = notes.get("issues")
    if isinstance(note_issues, list):
        fail_count = sum(
            1
            for item in note_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "release_notes_contain_fail_issues",
                    fail_count,
                    "Release notes report contains fail issues.",
                )
            )

    return issues


def build_release_candidate_gate_report(
    *,
    release_notes_path: Path,
    output_dir: Path,
    min_section_count: int = 5,
    allow_warnings: bool = False,
    require_final_outputs_exist: bool = True,
) -> ReleaseCandidateGateReport:
    min_section_count = max(min_section_count, 0)

    notes, load_issues = _load_release_notes(release_notes_path)
    issues: list[ReleaseCandidateIssue] = []
    issues.extend(load_issues)
    issues.extend(
        _release_notes_issues(
            notes,
            min_section_count=min_section_count,
            allow_warnings=allow_warnings,
            require_final_outputs_exist=require_final_outputs_exist,
        )
    )

    status = _status(issues)

    return ReleaseCandidateGateReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        release_notes_path=str(release_notes_path),
        output_directory=str(output_dir),
        release_version=str((notes or {}).get("release_version") or "v1.0-testing-edition"),
        status=status,
        ready_for_final_v1_testing_release_close=status in {"pass", "warn"},
        min_section_count_required=min_section_count,
        section_count=_to_int((notes or {}).get("section_count")) or 0,
        safety_notice=safety_notice(),
        release_notes_status=str((notes or {}).get("status") or ""),
        release_notes_ready=bool((notes or {}).get("ready_for_future_v1_release_candidate_gate")),
        final_backtest_report_path=str((notes or {}).get("final_backtest_report_path") or ""),
        final_metrics_path=str((notes or {}).get("final_metrics_path") or ""),
        final_trade_ledger_path=str((notes or {}).get("final_trade_ledger_path") or ""),
        issues=issues,
    )


def write_release_candidate_gate_report(
    report: ReleaseCandidateGateReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    gate_json = output_dir / "v1_testing_release_candidate_gate.json"
    gate_txt = output_dir / "v1_testing_release_candidate_gate.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    gate_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "HQE v1.0 Testing Edition Release Candidate Gate",
        "",
        report.safety_notice,
        "",
        f"Release version: {report.release_version}",
        f"Status: {report.status}",
        f"Ready for final v1.0 testing release close: {report.ready_for_final_v1_testing_release_close}",
        "",
        "Release notes evidence:",
        f"- Release notes status: {report.release_notes_status}",
        f"- Release notes ready: {report.release_notes_ready}",
        f"- Section count: {report.section_count}",
        "",
        "Final evidence outputs:",
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
        lines.append("- PASS: Release candidate gate is ready for final v1.0 testing release close.")
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
        "report_type": "v1_testing_release_candidate_gate",
        "generated_at_utc": report.generated_at_utc,
        "release_version": report.release_version,
        "status": report.status,
        "ready_for_final_v1_testing_release_close": report.ready_for_final_v1_testing_release_close,
        "section_count": report.section_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "v1_testing_release_candidate_gate_json": str(gate_json),
            "v1_testing_release_candidate_gate_txt": str(gate_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "v1_testing_release_candidate_gate_json": gate_json,
        "v1_testing_release_candidate_gate_txt": gate_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_release_candidate_gate_report(
    *,
    release_notes_path: Path,
    output_dir: Path,
    min_section_count: int = 5,
    allow_warnings: bool = False,
    require_final_outputs_exist: bool = True,
) -> tuple[ReleaseCandidateGateReport, dict[str, Path]]:
    report = build_release_candidate_gate_report(
        release_notes_path=release_notes_path,
        output_dir=output_dir,
        min_section_count=min_section_count,
        allow_warnings=allow_warnings,
        require_final_outputs_exist=require_final_outputs_exist,
    )
    outputs = write_release_candidate_gate_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate v1.0 Testing Edition release candidate evidence."
    )
    parser.add_argument(
        "--release-notes",
        default="reports/paper_trading/v1_testing_release_notes/v1_testing_release_notes.json",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/v1_testing_release_candidate_gate",
    )
    parser.add_argument("--min-section-count", type=int, default=5)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--skip-final-output-existence-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_release_candidate_gate_report(
        release_notes_path=Path(args.release_notes),
        output_dir=Path(args.output_dir),
        min_section_count=args.min_section_count,
        allow_warnings=args.allow_warnings,
        require_final_outputs_exist=not args.skip_final_output_existence_check,
    )

    print("HQE v1.0 Testing Edition release candidate gate completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for final v1.0 testing release close: {report.ready_for_final_v1_testing_release_close}")
    print(f"Release candidate gate report: {outputs['v1_testing_release_candidate_gate_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
