"""
Recorded data strategy replay scenario manifest.

Evidence-only scenario builder for a future paper/simulation strategy replay.
It packages accepted strategy input bars into deterministic replay scenarios.

This module never runs strategies, creates signals, creates trade plans,
connects to brokers, requests live market data, places orders, uses real money,
or proves profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class StrategyReplayScenarioIssue:
    """One scenario-manifest finding."""

    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class StrategyReplayScenario:
    """One deterministic future paper replay scenario."""

    scenario_id: str
    source_path: str
    source_type: str
    bar_count: int
    first_timestamp: str | None
    last_timestamp: str | None
    first_bar_index: int | None
    last_bar_index: int | None
    data_mode: str
    execution_mode: str


@dataclass(frozen=True)
class StrategyReplayScenarioReport:
    """Scenario manifest report."""

    generated_at_utc: str
    strategy_input_bars_path: str
    preflight_report_path: str
    output_directory: str
    status: str
    min_bars_per_scenario: int
    input_bar_count: int
    scenario_count: int
    safety_notice: str
    issues: list[StrategyReplayScenarioIssue]
    scenarios: list[StrategyReplayScenario]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This recorded-data strategy replay "
        "scenario manifest does not run strategies, create signals, create trade "
        "plans, connect to brokers, request live market data, place real orders, "
        "use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> StrategyReplayScenarioIssue:
    return StrategyReplayScenarioIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status_from_issues(issues: Sequence[StrategyReplayScenarioIssue]) -> str:
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
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _load_jsonl_objects(path: Path) -> tuple[list[Mapping[str, Any]], list[StrategyReplayScenarioIssue]]:
    if not path.exists():
        return [], [
            _issue(
                "fail",
                "strategy_input_bars_missing",
                1,
                "Strategy input bars JSONL does not exist. Run the strategy replay preflight first.",
            )
        ]

    rows: list[Mapping[str, Any]] = []
    issues: list[StrategyReplayScenarioIssue] = []
    invalid_json_lines = 0
    invalid_shape_lines = 0

    with path.open("r", encoding="utf-8") as file_handle:
        for line in file_handle:
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                invalid_json_lines += 1
                continue

            if not isinstance(payload, Mapping):
                invalid_shape_lines += 1
                continue

            rows.append(payload)

    if invalid_json_lines:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bars_invalid_jsonl",
                invalid_json_lines,
                f"{invalid_json_lines} strategy input bar lines are invalid JSON.",
            )
        )

    if invalid_shape_lines:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bars_invalid_shape",
                invalid_shape_lines,
                f"{invalid_shape_lines} strategy input bar lines are not JSON objects.",
            )
        )

    return rows, issues


def _preflight_issues(preflight_report_path: Path) -> list[StrategyReplayScenarioIssue]:
    if not preflight_report_path.exists():
        return [
            _issue(
                "info",
                "preflight_report_missing",
                1,
                "Strategy replay preflight report was not found; scenario manifest stayed evidence-only.",
            )
        ]

    try:
        payload = json.loads(preflight_report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [
            _issue(
                "warn",
                "preflight_report_invalid_json",
                1,
                "Strategy replay preflight report could not be parsed safely.",
            )
        ]

    if not isinstance(payload, Mapping):
        return [
            _issue(
                "warn",
                "preflight_report_invalid_shape",
                1,
                "Strategy replay preflight report must be a JSON object.",
            )
        ]

    status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_paper_strategy_replay"))

    if status == "fail" or not ready:
        return [
            _issue(
                "fail",
                "preflight_not_ready",
                1,
                "Strategy replay preflight is not ready, so scenario manifest is not accepted.",
            )
        ]

    if status == "warn":
        return [
            _issue(
                "warn",
                "preflight_warn",
                1,
                "Strategy replay preflight has warning status.",
            )
        ]

    if status == "pass":
        return []

    return [
        _issue(
            "warn",
            "preflight_unknown_status",
            1,
            f"Strategy replay preflight status is unknown: {status}.",
        )
    ]


def _bar_is_usable(bar: Mapping[str, Any]) -> bool:
    timestamp = _as_text(bar.get("timestamp"))
    close_value = bar.get("close")
    data_mode = str(bar.get("data_mode") or "").strip()
    execution_mode = str(bar.get("execution_mode") or "").strip()

    return (
        timestamp is not None
        and close_value is not None
        and data_mode == "recorded_replay"
        and execution_mode == "paper_simulation_only"
    )


def _scenario_from_group(
    scenario_index: int,
    source_path: str,
    bars: Sequence[Mapping[str, Any]],
) -> StrategyReplayScenario:
    first_bar = bars[0] if bars else {}
    last_bar = bars[-1] if bars else {}
    source_type = str(first_bar.get("source_type") or "")

    return StrategyReplayScenario(
        scenario_id=f"recorded_strategy_replay_scenario_{scenario_index:03d}",
        source_path=source_path,
        source_type=source_type,
        bar_count=len(bars),
        first_timestamp=_as_text(first_bar.get("timestamp")),
        last_timestamp=_as_text(last_bar.get("timestamp")),
        first_bar_index=_as_int(first_bar.get("bar_index")),
        last_bar_index=_as_int(last_bar.get("bar_index")),
        data_mode="recorded_replay",
        execution_mode="paper_simulation_only",
    )


def build_strategy_replay_scenario_report(
    *,
    strategy_input_bars_path: Path,
    preflight_report_path: Path,
    output_dir: Path,
    min_bars_per_scenario: int = 1,
    max_scenarios: int | None = None,
) -> StrategyReplayScenarioReport:
    """Build a deterministic scenario manifest from strategy input bars."""

    normalized_min_bars = max(min_bars_per_scenario, 0)
    bars, issues = _load_jsonl_objects(strategy_input_bars_path)
    issues.extend(_preflight_issues(preflight_report_path))

    if not bars:
        issues.append(
            _issue(
                "fail",
                "no_strategy_input_bars",
                1,
                "No strategy input bars were available for scenario manifest generation.",
            )
        )

    usable_bars: list[Mapping[str, Any]] = []
    skipped_bars = 0
    for bar in bars:
        if _bar_is_usable(bar):
            usable_bars.append(bar)
        else:
            skipped_bars += 1

    if skipped_bars:
        issues.append(
            _issue(
                "warn",
                "skipped_unusable_bars",
                skipped_bars,
                f"{skipped_bars} bars were skipped because required contract fields were missing.",
            )
        )

    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for bar in usable_bars:
        source_path = str(bar.get("source_path") or "unknown_source")
        grouped.setdefault(source_path, []).append(bar)

    scenarios: list[StrategyReplayScenario] = []
    too_small_groups = 0

    for source_path in sorted(grouped):
        group = grouped[source_path]
        if len(group) < normalized_min_bars:
            too_small_groups += 1
            continue

        scenarios.append(_scenario_from_group(len(scenarios) + 1, source_path, group))
        if max_scenarios is not None and max_scenarios >= 0:
            if len(scenarios) >= max_scenarios:
                break

    if too_small_groups:
        issues.append(
            _issue(
                "fail",
                "scenario_below_min_bars",
                too_small_groups,
                (
                    "One or more source groups had fewer bars than required. "
                    f"Minimum bars per scenario={normalized_min_bars}."
                ),
            )
        )

    if usable_bars and not scenarios:
        issues.append(
            _issue(
                "fail",
                "no_accepted_scenarios",
                1,
                "Usable bars existed, but no scenario met the acceptance rules.",
            )
        )

    return StrategyReplayScenarioReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        strategy_input_bars_path=str(strategy_input_bars_path),
        preflight_report_path=str(preflight_report_path),
        output_directory=str(output_dir),
        status=_status_from_issues(issues),
        min_bars_per_scenario=normalized_min_bars,
        input_bar_count=len(bars),
        scenario_count=len(scenarios),
        safety_notice=safety_notice(),
        issues=issues,
        scenarios=scenarios,
    )


def write_strategy_replay_scenario_report(
    report: StrategyReplayScenarioReport,
    output_dir: Path,
) -> dict[str, Path]:
    """Write scenario manifest reports."""

    output_dir.mkdir(parents=True, exist_ok=True)

    scenario_json = output_dir / "scenario_manifest.json"
    scenario_txt = output_dir / "scenario_manifest.txt"
    scenarios_jsonl = output_dir / "scenarios.jsonl"
    manifest_json = output_dir / "manifest.json"

    report_data = asdict(report)
    report_data["issues"] = [asdict(issue) for issue in report.issues]
    report_data["scenarios"] = [asdict(scenario) for scenario in report.scenarios]

    scenario_json.write_text(
        json.dumps(report_data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with scenarios_jsonl.open("w", encoding="utf-8", newline="\n") as file_handle:
        for scenario in report.scenarios:
            file_handle.write(json.dumps(asdict(scenario), sort_keys=True))
            file_handle.write("\n")

    lines = [
        "HQE Recorded Data Strategy Replay Scenario Manifest",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Strategy input bars path: {report.strategy_input_bars_path}",
        f"Preflight report path: {report.preflight_report_path}",
        f"Status: {report.status}",
        f"Minimum bars per scenario: {report.min_bars_per_scenario}",
        f"Input bars: {report.input_bar_count}",
        f"Accepted scenarios: {report.scenario_count}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Strategy input bars satisfy this scenario manifest scaffold.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: "
                f"{issue.message} Count={issue.count}"
            )

    lines.append("")
    lines.append("Scenarios:")
    if not report.scenarios:
        lines.append("- No accepted scenarios.")
    else:
        for scenario in report.scenarios:
            lines.append(
                f"- {scenario.scenario_id}: bars={scenario.bar_count}, "
                f"source={scenario.source_path}, "
                f"first={scenario.first_timestamp}, last={scenario.last_timestamp}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {scenario_json}",
            f"- {scenarios_jsonl}",
            f"- {scenario_txt}",
            f"- {manifest_json}",
            "",
            "This manifest does not run strategy logic, create signals, or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    scenario_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_strategy_replay_scenario_manifest",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "min_bars_per_scenario": report.min_bars_per_scenario,
        "input_bar_count": report.input_bar_count,
        "scenario_count": report.scenario_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "scenario_manifest_json": str(scenario_json),
            "scenarios_jsonl": str(scenarios_jsonl),
            "scenario_manifest_txt": str(scenario_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "scenario_manifest_json": scenario_json,
        "scenarios_jsonl": scenarios_jsonl,
        "scenario_manifest_txt": scenario_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_strategy_replay_scenario_report(
    *,
    strategy_input_bars_path: Path,
    preflight_report_path: Path,
    output_dir: Path,
    min_bars_per_scenario: int = 1,
    max_scenarios: int | None = None,
) -> tuple[StrategyReplayScenarioReport, dict[str, Path]]:
    report = build_strategy_replay_scenario_report(
        strategy_input_bars_path=strategy_input_bars_path,
        preflight_report_path=preflight_report_path,
        output_dir=output_dir,
        min_bars_per_scenario=min_bars_per_scenario,
        max_scenarios=max_scenarios,
    )
    outputs = write_strategy_replay_scenario_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a paper-only recorded-data strategy replay scenario manifest."
    )
    parser.add_argument(
        "--strategy-input-bars",
        default="reports/paper_trading/recorded_data_strategy_input_contract/strategy_input_bars.jsonl",
        help="Path to strategy input bars JSONL.",
    )
    parser.add_argument(
        "--preflight-report",
        default="reports/paper_trading/recorded_data_strategy_replay_preflight/preflight_report.json",
        help="Path to strategy replay preflight report JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/recorded_data_strategy_replay_scenario",
        help="Directory where scenario manifest reports are written.",
    )
    parser.add_argument(
        "--min-bars-per-scenario",
        type=int,
        default=1,
        help="Minimum bars required per accepted scenario.",
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=None,
        help="Optional maximum accepted scenarios.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_strategy_replay_scenario_report(
        strategy_input_bars_path=Path(args.strategy_input_bars),
        preflight_report_path=Path(args.preflight_report),
        output_dir=Path(args.output_dir),
        min_bars_per_scenario=args.min_bars_per_scenario,
        max_scenarios=args.max_scenarios,
    )

    print("HQE recorded data strategy replay scenario manifest completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Input bars: {report.input_bar_count}")
    print(f"Accepted scenarios: {report.scenario_count}")
    print(f"Scenario manifest: {outputs['scenario_manifest_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
