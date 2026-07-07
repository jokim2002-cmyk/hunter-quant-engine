import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_replay_plan_readiness import (
    build_and_write_paper_strategy_replay_plan_readiness_report,
    build_paper_strategy_replay_plan_readiness_report,
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


def _build(tmp_path, **kwargs):
    readiness, manifest, bars = _write_inputs(
        tmp_path,
        readiness=kwargs.pop("readiness", None),
        manifest=kwargs.pop("manifest", None),
        bars=kwargs.pop("bars", None),
    )
    return build_paper_strategy_replay_plan_readiness_report(
        scenario_readiness_path=readiness,
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        plan_output_dir=tmp_path / "plan",
        plan_acceptance_output_dir=tmp_path / "acceptance",
        plan_readiness_output_dir=tmp_path / "readiness",
        **kwargs,
    )


def test_safety_notice_preserves_plan_readiness_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_plan_readiness_passes_valid_inputs(tmp_path):
    report = _build(tmp_path)

    assert report.status == "pass"
    assert report.ready_for_future_paper_strategy_replay_plan is True
    assert [stage.stage for stage in report.stage_results] == [
        "recorded_data_paper_strategy_replay_plan",
        "recorded_data_paper_strategy_replay_plan_acceptance",
    ]


def test_plan_readiness_fails_when_min_scenarios_not_met(tmp_path):
    report = _build(tmp_path, min_scenarios=2)

    assert report.status == "fail"
    assert report.ready_for_future_paper_strategy_replay_plan is False
    assert report.stage_results[0].accepted is False


def test_plan_readiness_fails_when_min_total_bars_not_met(tmp_path):
    report = _build(tmp_path, min_total_planned_bars=3)

    assert report.status == "fail"
    assert report.stage_results[1].accepted is False
    assert report.stage_results[1].summary["total_planned_bars"] == 2


def test_plan_readiness_blocks_warning_by_default(tmp_path):
    report = _build(tmp_path, readiness=_readiness(status="warn", ready=True))

    assert report.status == "fail"
    assert report.ready_for_future_paper_strategy_replay_plan is False


def test_plan_readiness_allows_warning_when_requested(tmp_path):
    report = _build(
        tmp_path,
        readiness=_readiness(status="warn", ready=True),
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_paper_strategy_replay_plan is True
    assert report.stage_results[1].accepted is True


def test_plan_readiness_fails_invalid_scenario_readiness(tmp_path):
    report = _build(tmp_path, readiness=_readiness(status="fail", ready=False))

    assert report.status == "fail"
    assert report.stage_results[0].status == "fail"


def test_plan_readiness_fails_forbidden_manifest_fields(tmp_path):
    manifest = _scenario_manifest()
    manifest["pnl"] = 99

    report = _build(tmp_path, manifest=manifest)

    assert report.status == "fail"
    assert report.stage_results[0].accepted is False


def test_plan_readiness_fails_when_source_bars_missing(tmp_path):
    manifest = _scenario_manifest(
        scenarios=[
            {
                "scenario_id": "recorded_strategy_replay_scenario_001",
                "source_path": "missing.csv",
                "source_type": "csv",
                "bar_count": 2,
                "first_timestamp": "2026-01-01T09:15:00+05:30",
                "last_timestamp": "2026-01-01T09:16:00+05:30",
                "data_mode": "recorded_replay",
                "execution_mode": "paper_simulation_only",
            }
        ]
    )

    report = _build(tmp_path, manifest=manifest)

    assert report.status == "fail"
    assert report.stage_results[0].summary["scenario_count"] == 0


def test_build_and_write_plan_readiness_contains_outputs_safety_and_no_profit_claim(tmp_path):
    readiness, manifest, bars = _write_inputs(tmp_path)

    report, outputs = build_and_write_paper_strategy_replay_plan_readiness_report(
        scenario_readiness_path=readiness,
        scenario_manifest_path=manifest,
        strategy_input_bars_path=bars,
        plan_output_dir=tmp_path / "plan",
        plan_acceptance_output_dir=tmp_path / "acceptance",
        plan_readiness_output_dir=tmp_path / "readiness",
    )

    text_report = outputs["paper_strategy_replay_plan_readiness_txt"].read_text(
        encoding="utf-8"
    )
    manifest_payload = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert outputs["paper_strategy_replay_plan_readiness_json"].exists()
    assert outputs["paper_strategy_replay_plan_readiness_txt"].exists()
    assert outputs["manifest_json"].exists()
    assert report.status == "pass"
    assert "not a profitability claim" in text_report
    assert manifest_payload["ready_for_future_paper_strategy_replay_plan"] is True


def test_documentation_mentions_paper_strategy_replay_plan_readiness_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_REPLAY_PLAN_READINESS.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_replay_plan_readiness.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
