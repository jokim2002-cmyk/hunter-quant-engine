import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_replay_plan import (
    build_and_write_paper_strategy_replay_plan_report,
    build_paper_strategy_replay_plan_report,
    safety_notice,
)


def _readiness(status="pass", ready=True):
    return {
        "status": status,
        "ready_for_future_paper_strategy_replay": ready,
    }


def _scenario_manifest(status="pass", scenarios=None):
    return {
        "status": status,
        "scenarios": scenarios
        or [
            {
                "scenario_id": "recorded_strategy_replay_scenario_001",
                "source_path": "sample.csv",
                "source_type": "csv",
                "bar_count": 2,
                "first_timestamp": "2026-01-01T09:15:00+05:30",
                "last_timestamp": "2026-01-01T09:16:00+05:30",
                "data_mode": "recorded_replay",
                "execution_mode": "paper_simulation_only",
            }
        ],
    }


def _bar(index=1, source_path="sample.csv", close=105):
    return {
        "bar_index": index,
        "timestamp": f"2026-01-01T09:1{index + 4}:00+05:30",
        "source_path": source_path,
        "source_type": "csv",
        "source_row_number": index,
        "open": 100,
        "high": 110,
        "low": 95,
        "close": close,
        "volume": 1000,
        "data_mode": "recorded_replay",
        "execution_mode": "paper_simulation_only",
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_bars(path, bars):
    path.write_text(
        "\n".join(json.dumps(bar) for bar in bars) + "\n",
        encoding="utf-8",
    )
    return path


def _write_inputs(tmp_path, *, readiness=None, manifest=None, bars=None):
    readiness_path = _write_json(
        tmp_path / "scenario_readiness_report.json",
        readiness or _readiness(),
    )
    manifest_path = _write_json(
        tmp_path / "scenario_manifest.json",
        manifest or _scenario_manifest(),
    )
    bars_path = _write_bars(
        tmp_path / "strategy_input_bars.jsonl",
        bars or [_bar(1), _bar(2, close=108)],
    )
    return readiness_path, manifest_path, bars_path


def test_safety_notice_preserves_plan_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_scenario_readiness_fails(tmp_path):
    manifest = _write_json(tmp_path / "scenario_manifest.json", _scenario_manifest())
    bars = _write_bars(tmp_path / "strategy_input_bars.jsonl", [_bar()])

    report = build_paper_strategy_replay_plan_report(
        scenario_readiness_path=tmp_path / "missing.json",
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "scenario_readiness_missing" for issue in report.issues)


def test_valid_inputs_create_no_execution_replay_plan(tmp_path):
    readiness, manifest, bars = _write_inputs(tmp_path)

    report = build_paper_strategy_replay_plan_report(
        scenario_readiness_path=readiness,
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
        min_scenarios=1,
        min_bars=1,
    )

    assert report.status == "pass"
    assert report.ready_to_plan is True
    assert report.scenario_count == 1
    assert report.total_planned_bars == 2
    assert report.scenario_plans[0].strategy_execution_mode == "not_executed_planning_only"
    assert report.scenario_plans[0].broker_execution_mode == "broker_disabled"


def test_readiness_not_ready_fails_plan(tmp_path):
    readiness, manifest, bars = _write_inputs(
        tmp_path,
        readiness=_readiness(status="fail", ready=False),
    )

    report = build_paper_strategy_replay_plan_report(
        scenario_readiness_path=readiness,
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "scenario_readiness_not_ready" for issue in report.issues)


def test_warning_readiness_fails_by_default(tmp_path):
    readiness, manifest, bars = _write_inputs(
        tmp_path,
        readiness=_readiness(status="warn", ready=True),
    )

    report = build_paper_strategy_replay_plan_report(
        scenario_readiness_path=readiness,
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "warnings_not_allowed" for issue in report.issues)


def test_warning_readiness_can_remain_warning_when_allowed(tmp_path):
    readiness, manifest, bars = _write_inputs(
        tmp_path,
        readiness=_readiness(status="warn", ready=True),
    )

    report = build_paper_strategy_replay_plan_report(
        scenario_readiness_path=readiness,
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_to_plan is True


def test_min_scenarios_rule_can_fail(tmp_path):
    readiness, manifest, bars = _write_inputs(tmp_path)

    report = build_paper_strategy_replay_plan_report(
        scenario_readiness_path=readiness,
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
        min_scenarios=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_scenarios" for issue in report.issues)


def test_min_bars_rule_can_fail(tmp_path):
    readiness, manifest, bars = _write_inputs(
        tmp_path,
        manifest=_scenario_manifest(
            scenarios=[
                {
                    "scenario_id": "recorded_strategy_replay_scenario_001",
                    "source_path": "sample.csv",
                    "source_type": "csv",
                    "bar_count": 1,
                    "first_timestamp": "2026-01-01T09:15:00+05:30",
                    "last_timestamp": "2026-01-01T09:15:00+05:30",
                    "data_mode": "recorded_replay",
                    "execution_mode": "paper_simulation_only",
                }
            ]
        ),
        bars=[_bar(1)],
    )

    report = build_paper_strategy_replay_plan_report(
        scenario_readiness_path=readiness,
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
        min_bars=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "scenario_below_min_bars" for issue in report.issues)


def test_forbidden_execution_fields_fail_plan(tmp_path):
    readiness, manifest, bars = _write_inputs(
        tmp_path,
        manifest={
            **_scenario_manifest(),
            "pnl": 100,
        },
    )

    report = build_paper_strategy_replay_plan_report(
        scenario_readiness_path=readiness,
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "forbidden_manifest_fields" for issue in report.issues)


def test_build_and_write_plan_contains_outputs_safety_and_no_profit_claim(tmp_path):
    readiness, manifest, bars = _write_inputs(tmp_path)

    report, outputs = build_and_write_paper_strategy_replay_plan_report(
        scenario_readiness_path=readiness,
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["paper_strategy_replay_plan_txt"].read_text(encoding="utf-8")
    manifest_payload = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert outputs["paper_strategy_replay_plan_json"].exists()
    assert outputs["paper_strategy_replay_plans_jsonl"].exists()
    assert outputs["paper_strategy_replay_plan_txt"].exists()
    assert outputs["manifest_json"].exists()
    assert report.status == "pass"
    assert "does not run strategy logic" in text_report
    assert "not a profitability claim" in text_report
    assert manifest_payload["scenario_count"] == 1


def test_documentation_mentions_paper_strategy_replay_plan_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_REPLAY_PLAN.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_replay_plan.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
