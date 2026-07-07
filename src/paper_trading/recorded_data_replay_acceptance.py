"""
Recorded data replay acceptance gate.

Evidence-only acceptance gate for the recorded-data replay evidence bundle. This
gate decides whether the generated replay evidence is structurally acceptable
for a future paper/simulation strategy replay phase.

It never runs strategies, creates trade plans, connects to brokers, requests
live market data, places orders, uses real money, or proves profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_STAGE_NAMES = (
    "recorded_data_replay_dataset",
    "recorded_data_replay_quality_gate",
    "recorded_data_replay_dry_run",
)


@dataclass(frozen=True)
class ReplayAcceptanceIssue:
    """One acceptance-gate finding."""

    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class ReplayAcceptanceReport:
    """Acceptance-gate report for a replay evidence bundle."""

    generated_at_utc: str
    evidence_summary_path: str
    output_directory: str
    status: str
    accepted: bool
    min_events_required: int
    allow_warnings: bool
    bundle_status: str
    stage_count: int
    replayed_event_count: int
    safety_notice: str
    issues: list[ReplayAcceptanceIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data replay acceptance "
        "gate does not run strategies, create trade plans, connect to brokers, "
        "request live market data, place real orders, use real money, or prove "
        "profitability."
    )


def _issue(severity: str, code: str, count: int, message: str) -> ReplayAcceptanceIssue:
    return ReplayAcceptanceIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status_from_issues(issues: Sequence[ReplayAcceptanceIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _safe_stage_results(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    stages = payload.get("stage_results", [])
    if not isinstance(stages, list):
        return []
    return [stage for stage in stages if isinstance(stage, Mapping)]


def _stage_by_name(
    stages: Sequence[Mapping[str, Any]],
    stage_name: str,
) -> Mapping[str, Any] | None:
    for stage in stages:
        if stage.get("stage") == stage_name:
            return stage
    return None


def _stage_status(stage: Mapping[str, Any]) -> str:
    return str(stage.get("status") or "unknown").lower()


def _stage_summary(stage: Mapping[str, Any]) -> Mapping[str, Any]:
    summary = stage.get("summary", {})
    if isinstance(summary, Mapping):
        return summary
    return {}


def _load_summary(
    evidence_summary_path: Path,
) -> tuple[Mapping[str, Any] | None, list[ReplayAcceptanceIssue]]:
    if not evidence_summary_path.exists():
        return None, [
            _issue(
                "fail",
                "evidence_summary_missing",
                1,
                "Replay evidence summary JSON does not exist. Run the replay evidence bundle first.",
            )
        ]

    try:
        payload = json.loads(evidence_summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "evidence_summary_invalid_json",
                1,
                f"Replay evidence summary JSON could not be parsed safely: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "evidence_summary_invalid_shape",
                1,
                "Replay evidence summary JSON must be an object.",
            )
        ]

    return payload, []


def build_acceptance_report(
    *,
    evidence_summary_path: Path,
    output_dir: Path,
    min_events: int = 1,
    allow_warnings: bool = False,
) -> ReplayAcceptanceReport:
    """Build a replay acceptance report from the combined evidence summary."""

    normalized_min_events = max(min_events, 0)
    payload, issues = _load_summary(evidence_summary_path)

    if payload is None:
        status = _status_from_issues(issues)
        return ReplayAcceptanceReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            evidence_summary_path=str(evidence_summary_path),
            output_directory=str(output_dir),
            status=status,
            accepted=False,
            min_events_required=normalized_min_events,
            allow_warnings=allow_warnings,
            bundle_status="unknown",
            stage_count=0,
            replayed_event_count=0,
            safety_notice=safety_notice(),
            issues=issues,
        )

    bundle_status = str(payload.get("status") or "unknown").lower()
    stages = _safe_stage_results(payload)
    replayed_event_count = 0

    if len(stages) < len(REQUIRED_STAGE_NAMES):
        issues.append(
            _issue(
                "fail",
                "missing_stage_results",
                len(REQUIRED_STAGE_NAMES) - len(stages),
                "Replay evidence summary does not contain all required stage results.",
            )
        )

    for stage_name in REQUIRED_STAGE_NAMES:
        stage = _stage_by_name(stages, stage_name)
        if stage is None:
            issues.append(
                _issue(
                    "fail",
                    "missing_required_stage",
                    1,
                    f"Required replay evidence stage is missing: {stage_name}.",
                )
            )
            continue

        status = _stage_status(stage)
        if status == "fail":
            issues.append(
                _issue(
                    "fail",
                    f"{stage_name}_failed",
                    1,
                    f"Required replay evidence stage failed: {stage_name}.",
                )
            )
        elif status == "warn":
            severity = "warn" if allow_warnings else "fail"
            issues.append(
                _issue(
                    severity,
                    f"{stage_name}_warn",
                    1,
                    f"Required replay evidence stage has warning status: {stage_name}.",
                )
            )
        elif status != "pass":
            issues.append(
                _issue(
                    "fail",
                    f"{stage_name}_unknown_status",
                    1,
                    f"Required replay evidence stage has unknown status: {stage_name}.",
                )
            )

    dry_run_stage = _stage_by_name(stages, "recorded_data_replay_dry_run")
    if dry_run_stage is not None:
        replayed_event_count = (
            _as_int(_stage_summary(dry_run_stage).get("replayed_event_count")) or 0
        )

    if bundle_status == "fail":
        issues.append(
            _issue(
                "fail",
                "bundle_failed",
                1,
                "Replay evidence bundle status is fail.",
            )
        )
    elif bundle_status == "warn":
        severity = "warn" if allow_warnings else "fail"
        issues.append(
            _issue(
                severity,
                "bundle_warn",
                1,
                "Replay evidence bundle status is warn.",
            )
        )
    elif bundle_status != "pass":
        issues.append(
            _issue(
                "fail",
                "bundle_unknown_status",
                1,
                f"Replay evidence bundle status is unknown: {bundle_status}.",
            )
        )

    if replayed_event_count < normalized_min_events:
        issues.append(
            _issue(
                "fail",
                "insufficient_replayed_events",
                normalized_min_events - replayed_event_count,
                (
                    "Replay dry-run produced fewer events than the acceptance "
                    f"minimum. Required={normalized_min_events}, actual={replayed_event_count}."
                ),
            )
        )

    status = _status_from_issues(issues)
    accepted = status == "pass" or (status == "warn" and allow_warnings)

    return ReplayAcceptanceReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        evidence_summary_path=str(evidence_summary_path),
        output_directory=str(output_dir),
        status=status,
        accepted=accepted,
        min_events_required=normalized_min_events,
        allow_warnings=allow_warnings,
        bundle_status=bundle_status,
        stage_count=len(stages),
        replayed_event_count=replayed_event_count,
        safety_notice=safety_notice(),
        issues=issues,
    )


def write_acceptance_report(
    report: ReplayAcceptanceReport,
    output_dir: Path,
) -> dict[str, Path]:
    """Write acceptance-gate reports."""

    output_dir.mkdir(parents=True, exist_ok=True)

    acceptance_json = output_dir / "acceptance_gate.json"
    acceptance_txt = output_dir / "acceptance_gate.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["issues"] = [asdict(issue) for issue in report.issues]

    acceptance_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Replay Acceptance Gate",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Evidence summary path: {report.evidence_summary_path}",
        f"Status: {report.status}",
        f"Accepted for future paper replay: {report.accepted}",
        f"Minimum events required: {report.min_events_required}",
        f"Allow warnings: {report.allow_warnings}",
        f"Bundle status: {report.bundle_status}",
        f"Stage count: {report.stage_count}",
        f"Replayed event count: {report.replayed_event_count}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Replay evidence bundle meets this acceptance scaffold.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: "
                f"{issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {acceptance_json}",
            f"- {acceptance_txt}",
            f"- {manifest_json}",
            "",
            "This gate only checks structural replay evidence readiness.",
            "This report is not a profitability claim.",
        ]
    )
    acceptance_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_replay_acceptance_gate",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted": report.accepted,
        "min_events_required": report.min_events_required,
        "allow_warnings": report.allow_warnings,
        "bundle_status": report.bundle_status,
        "stage_count": report.stage_count,
        "replayed_event_count": report.replayed_event_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "acceptance_gate_json": str(acceptance_json),
            "acceptance_gate_txt": str(acceptance_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "acceptance_gate_json": acceptance_json,
        "acceptance_gate_txt": acceptance_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_acceptance_report(
    *,
    evidence_summary_path: Path,
    output_dir: Path,
    min_events: int = 1,
    allow_warnings: bool = False,
) -> tuple[ReplayAcceptanceReport, dict[str, Path]]:
    report = build_acceptance_report(
        evidence_summary_path=evidence_summary_path,
        output_dir=output_dir,
        min_events=min_events,
        allow_warnings=allow_warnings,
    )
    outputs = write_acceptance_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate a paper-only recorded-data replay evidence bundle."
    )
    parser.add_argument(
        "--evidence-summary",
        default="reports/paper_trading/recorded_data_replay_evidence/evidence_summary.json",
        help="Path to the recorded-data replay evidence summary JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_replay_acceptance",
        help="Directory where acceptance-gate reports are written.",
    )
    parser.add_argument(
        "--min-events",
        type=int,
        default=1,
        help="Minimum replay dry-run events required for acceptance.",
    )
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="Allow warn-status evidence bundles to be accepted with warning status.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_acceptance_report(
        evidence_summary_path=Path(args.evidence_summary),
        output_dir=Path(args.output_dir),
        min_events=args.min_events,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data replay acceptance gate completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for future paper replay: {report.accepted}")
    print(f"Replayed events: {report.replayed_event_count}")
    print(f"Acceptance report: {outputs['acceptance_gate_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
