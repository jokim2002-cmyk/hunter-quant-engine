"""
Recorded data strategy replay scenario acceptance gate.

Evidence-only acceptance gate for recorded-data strategy replay scenarios. This
gate validates that scenario manifest output is structurally acceptable before a
future paper/simulation strategy replay phase.

It never runs strategies, creates signals, creates trade plans, connects to
brokers, requests live market data, places orders, uses real money, or proves
profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ScenarioAcceptanceIssue:
    """One scenario acceptance finding."""

    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class ScenarioAcceptanceReport:
    """Acceptance report for recorded-data strategy replay scenarios."""

    generated_at_utc: str
    scenario_manifest_path: str
    output_directory: str
    status: str
    accepted: bool
    min_scenarios_required: int
    min_bars_per_scenario: int
    allow_warnings: bool
    manifest_status: str
    scenario_count: int
    total_bar_count: int
    safety_notice: str
    issues: list[ScenarioAcceptanceIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data strategy replay "
        "scenario acceptance gate does not run strategies, create signals, "
        "create trade plans, connect to brokers, request live market data, "
        "place real orders, use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> ScenarioAcceptanceIssue:
    return ScenarioAcceptanceIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status_from_issues(issues: Sequence[ScenarioAcceptanceIssue]) -> str:
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


def _safe_scenarios(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    scenarios = payload.get("scenarios", [])
    if not isinstance(scenarios, list):
        return []
    return [scenario for scenario in scenarios if isinstance(scenario, Mapping)]


def _load_scenario_manifest(
    scenario_manifest_path: Path,
) -> tuple[Mapping[str, Any] | None, list[ScenarioAcceptanceIssue]]:
    if not scenario_manifest_path.exists():
        return None, [
            _issue(
                "fail",
                "scenario_manifest_missing",
                1,
                "Scenario manifest JSON does not exist. Run the scenario manifest module first.",
            )
        ]

    try:
        payload = json.loads(scenario_manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "scenario_manifest_invalid_json",
                1,
                f"Scenario manifest JSON could not be parsed safely: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "scenario_manifest_invalid_shape",
                1,
                "Scenario manifest JSON must be an object.",
            )
        ]

    return payload, []


def _scenario_field_issues(
    scenarios: Sequence[Mapping[str, Any]],
    *,
    min_bars_per_scenario: int,
) -> tuple[list[ScenarioAcceptanceIssue], int]:
    issues: list[ScenarioAcceptanceIssue] = []
    total_bar_count = 0
    missing_required = 0
    wrong_modes = 0
    below_min_bars = 0

    for scenario in scenarios:
        bar_count = _as_int(scenario.get("bar_count")) or 0
        total_bar_count += bar_count

        required_values = [
            scenario.get("scenario_id"),
            scenario.get("source_path"),
            scenario.get("first_timestamp"),
            scenario.get("last_timestamp"),
        ]
        if any(value in (None, "") for value in required_values):
            missing_required += 1

        data_mode = str(scenario.get("data_mode") or "").strip()
        execution_mode = str(scenario.get("execution_mode") or "").strip()
        if data_mode != "recorded_replay" or execution_mode != "paper_simulation_only":
            wrong_modes += 1

        if bar_count < min_bars_per_scenario:
            below_min_bars += 1

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "scenario_missing_required_fields",
                missing_required,
                f"{missing_required} scenarios are missing required identity/source/timestamp fields.",
            )
        )

    if wrong_modes:
        issues.append(
            _issue(
                "fail",
                "scenario_wrong_mode",
                wrong_modes,
                f"{wrong_modes} scenarios are not recorded_replay and paper_simulation_only.",
            )
        )

    if below_min_bars:
        issues.append(
            _issue(
                "fail",
                "scenario_below_min_bars",
                below_min_bars,
                (
                    "One or more scenarios have fewer bars than required. "
                    f"Minimum bars per scenario={min_bars_per_scenario}."
                ),
            )
        )

    return issues, total_bar_count


def build_scenario_acceptance_report(
    *,
    scenario_manifest_path: Path,
    output_dir: Path,
    min_scenarios: int = 1,
    min_bars_per_scenario: int = 1,
    allow_warnings: bool = False,
) -> ScenarioAcceptanceReport:
    """Build an acceptance report for a scenario manifest."""

    normalized_min_scenarios = max(min_scenarios, 0)
    normalized_min_bars = max(min_bars_per_scenario, 0)

    payload, issues = _load_scenario_manifest(scenario_manifest_path)

    if payload is None:
        status = _status_from_issues(issues)
        return ScenarioAcceptanceReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            scenario_manifest_path=str(scenario_manifest_path),
            output_directory=str(output_dir),
            status=status,
            accepted=False,
            min_scenarios_required=normalized_min_scenarios,
            min_bars_per_scenario=normalized_min_bars,
            allow_warnings=allow_warnings,
            manifest_status="unknown",
            scenario_count=0,
            total_bar_count=0,
            safety_notice=safety_notice(),
            issues=issues,
        )

    manifest_status = str(payload.get("status") or "unknown").lower()
    scenarios = _safe_scenarios(payload)

    if manifest_status == "fail":
        issues.append(
            _issue(
                "fail",
                "scenario_manifest_failed",
                1,
                "Scenario manifest status is fail.",
            )
        )
    elif manifest_status == "warn":
        severity = "warn" if allow_warnings else "fail"
        issues.append(
            _issue(
                severity,
                "scenario_manifest_warn",
                1,
                "Scenario manifest status is warn.",
            )
        )
    elif manifest_status != "pass":
        issues.append(
            _issue(
                "fail",
                "scenario_manifest_unknown_status",
                1,
                f"Scenario manifest status is unknown: {manifest_status}.",
            )
        )

    if len(scenarios) < normalized_min_scenarios:
        issues.append(
            _issue(
                "fail",
                "insufficient_scenarios",
                normalized_min_scenarios - len(scenarios),
                (
                    "Scenario manifest has fewer accepted scenarios than required. "
                    f"Required={normalized_min_scenarios}, actual={len(scenarios)}."
                ),
            )
        )

    scenario_issues, total_bar_count = _scenario_field_issues(
        scenarios,
        min_bars_per_scenario=normalized_min_bars,
    )
    issues.extend(scenario_issues)

    if scenarios and total_bar_count == 0:
        issues.append(
            _issue(
                "fail",
                "zero_total_bars",
                1,
                "Scenario manifest contains scenarios but total bar count is zero.",
            )
        )

    status = _status_from_issues(issues)
    accepted = status == "pass" or (status == "warn" and allow_warnings)

    return ScenarioAcceptanceReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        scenario_manifest_path=str(scenario_manifest_path),
        output_directory=str(output_dir),
        status=status,
        accepted=accepted,
        min_scenarios_required=normalized_min_scenarios,
        min_bars_per_scenario=normalized_min_bars,
        allow_warnings=allow_warnings,
        manifest_status=manifest_status,
        scenario_count=len(scenarios),
        total_bar_count=total_bar_count,
        safety_notice=safety_notice(),
        issues=issues,
    )


def write_scenario_acceptance_report(
    report: ScenarioAcceptanceReport,
    output_dir: Path,
) -> dict[str, Path]:
    """Write scenario acceptance gate reports."""

    output_dir.mkdir(parents=True, exist_ok=True)

    acceptance_json = output_dir / "scenario_acceptance.json"
    acceptance_txt = output_dir / "scenario_acceptance.txt"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["issues"] = [asdict(issue) for issue in report.issues]

    acceptance_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Strategy Replay Scenario Acceptance Gate",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Scenario manifest path: {report.scenario_manifest_path}",
        f"Status: {report.status}",
        f"Accepted for future paper strategy replay: {report.accepted}",
        f"Minimum scenarios required: {report.min_scenarios_required}",
        f"Minimum bars per scenario: {report.min_bars_per_scenario}",
        f"Allow warnings: {report.allow_warnings}",
        f"Manifest status: {report.manifest_status}",
        f"Scenario count: {report.scenario_count}",
        f"Total bar count: {report.total_bar_count}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Scenario manifest meets this acceptance scaffold.")
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
            "This gate only checks structural scenario readiness.",
            "This report is not a profitability claim.",
        ]
    )
    acceptance_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_strategy_replay_scenario_acceptance",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted": report.accepted,
        "min_scenarios_required": report.min_scenarios_required,
        "min_bars_per_scenario": report.min_bars_per_scenario,
        "allow_warnings": report.allow_warnings,
        "manifest_status": report.manifest_status,
        "scenario_count": report.scenario_count,
        "total_bar_count": report.total_bar_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "scenario_acceptance_json": str(acceptance_json),
            "scenario_acceptance_txt": str(acceptance_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "scenario_acceptance_json": acceptance_json,
        "scenario_acceptance_txt": acceptance_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_scenario_acceptance_report(
    *,
    scenario_manifest_path: Path,
    output_dir: Path,
    min_scenarios: int = 1,
    min_bars_per_scenario: int = 1,
    allow_warnings: bool = False,
) -> tuple[ScenarioAcceptanceReport, dict[str, Path]]:
    report = build_scenario_acceptance_report(
        scenario_manifest_path=scenario_manifest_path,
        output_dir=output_dir,
        min_scenarios=min_scenarios,
        min_bars_per_scenario=min_bars_per_scenario,
        allow_warnings=allow_warnings,
    )
    outputs = write_scenario_acceptance_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate a paper-only recorded-data strategy replay scenario manifest."
    )
    parser.add_argument(
        "--scenario-manifest",
        default="reports/paper_trading/recorded_data_strategy_replay_scenario/scenario_manifest.json",
        help="Path to strategy replay scenario manifest JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_strategy_replay_scenario_acceptance",
        help="Directory where scenario acceptance reports are written.",
    )
    parser.add_argument(
        "--min-scenarios",
        type=int,
        default=1,
        help="Minimum accepted scenarios required for pass status.",
    )
    parser.add_argument(
        "--min-bars-per-scenario",
        type=int,
        default=1,
        help="Minimum bars required in each accepted scenario.",
    )
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="Allow warn-status scenario manifests to be accepted with warning status.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_scenario_acceptance_report(
        scenario_manifest_path=Path(args.scenario_manifest),
        output_dir=Path(args.output_dir),
        min_scenarios=args.min_scenarios,
        min_bars_per_scenario=args.min_bars_per_scenario,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data strategy replay scenario acceptance gate completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for future paper strategy replay: {report.accepted}")
    print(f"Scenario count: {report.scenario_count}")
    print(f"Scenario acceptance report: {outputs['scenario_acceptance_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
