import json
from pathlib import Path

from src.paper_trading.recorded_data_strategy_replay_scenario import (
    build_and_write_strategy_replay_scenario_report,
    build_strategy_replay_scenario_report,
    safety_notice,
    write_strategy_replay_scenario_report,
)


def _bar(
    bar_index=1,
    source_path="sample.csv",
    timestamp="2026-01-01T09:15:00+05:30",
    close=105,
):
    return {
        "bar_index": bar_index,
        "timestamp": timestamp,
        "source_path": source_path,
        "source_type": "csv",
        "source_row_number": bar_index,
        "open": 100,
        "high": 110,
        "low": 95,
        "close": close,
        "volume": 1000,
        "data_mode": "recorded_replay",
        "execution_mode": "paper_simulation_only",
    }


def _write_bars(tmp_path, bars):
    path = tmp_path / "strategy_input_bars.jsonl"
    path.write_text(
        "\n".join(json.dumps(bar) for bar in bars) + "\n",
        encoding="utf-8",
    )
    return path


def _write_preflight(tmp_path, status="pass", ready=True):
    path = tmp_path / "preflight_report.json"
    path.write_text(
        json.dumps(
            {
                "status": status,
                "ready_for_future_paper_strategy_replay": ready,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_safety_notice_preserves_scenario_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "create signals" in notice
    assert "real orders" in notice
    assert "prove profitability" in notice


def test_missing_strategy_input_bars_fails(tmp_path):
    report = build_strategy_replay_scenario_report(
        strategy_input_bars_path=tmp_path / "missing.jsonl",
        preflight_report_path=tmp_path / "missing_preflight.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.scenario_count == 0
    assert any(issue.code == "strategy_input_bars_missing" for issue in report.issues)


def test_invalid_jsonl_line_fails(tmp_path):
    bars_path = tmp_path / "strategy_input_bars.jsonl"
    bars_path.write_text("{bad-json\n", encoding="utf-8")
    preflight = _write_preflight(tmp_path)

    report = build_strategy_replay_scenario_report(
        strategy_input_bars_path=bars_path,
        preflight_report_path=preflight,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_input_bars_invalid_jsonl" for issue in report.issues)


def test_valid_bars_create_one_scenario(tmp_path):
    bars_path = _write_bars(
        tmp_path,
        [
            _bar(1, "sample.csv", "2026-01-01T09:15:00+05:30", 105),
            _bar(2, "sample.csv", "2026-01-01T09:16:00+05:30", 108),
        ],
    )
    preflight = _write_preflight(tmp_path)

    report = build_strategy_replay_scenario_report(
        strategy_input_bars_path=bars_path,
        preflight_report_path=preflight,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.input_bar_count == 2
    assert report.scenario_count == 1
    assert report.scenarios[0].bar_count == 2
    assert report.scenarios[0].scenario_id == "recorded_strategy_replay_scenario_001"


def test_bars_are_grouped_by_source_path(tmp_path):
    bars_path = _write_bars(
        tmp_path,
        [
            _bar(1, "a.csv", "2026-01-01T09:15:00+05:30", 105),
            _bar(2, "b.csv", "2026-01-01T09:16:00+05:30", 108),
        ],
    )
    preflight = _write_preflight(tmp_path)

    report = build_strategy_replay_scenario_report(
        strategy_input_bars_path=bars_path,
        preflight_report_path=preflight,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.scenario_count == 2
    assert {scenario.source_path for scenario in report.scenarios} == {"a.csv", "b.csv"}


def test_min_bars_per_scenario_rule_can_fail(tmp_path):
    bars_path = _write_bars(tmp_path, [_bar()])
    preflight = _write_preflight(tmp_path)

    report = build_strategy_replay_scenario_report(
        strategy_input_bars_path=bars_path,
        preflight_report_path=preflight,
        output_dir=tmp_path / "out",
        min_bars_per_scenario=2,
    )

    assert report.status == "fail"
    assert report.scenario_count == 0
    assert any(issue.code == "scenario_below_min_bars" for issue in report.issues)


def test_preflight_not_ready_fails_manifest(tmp_path):
    bars_path = _write_bars(tmp_path, [_bar()])
    preflight = _write_preflight(tmp_path, status="fail", ready=False)

    report = build_strategy_replay_scenario_report(
        strategy_input_bars_path=bars_path,
        preflight_report_path=preflight,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "preflight_not_ready" for issue in report.issues)


def test_preflight_warning_creates_warning_manifest(tmp_path):
    bars_path = _write_bars(tmp_path, [_bar()])
    preflight = _write_preflight(tmp_path, status="warn", ready=True)

    report = build_strategy_replay_scenario_report(
        strategy_input_bars_path=bars_path,
        preflight_report_path=preflight,
        output_dir=tmp_path / "out",
    )

    assert report.status == "warn"
    assert report.scenario_count == 1
    assert any(issue.code == "preflight_warn" for issue in report.issues)


def test_unusable_bars_are_skipped_with_warning(tmp_path):
    bad_bar = _bar()
    bad_bar["execution_mode"] = "live"
    bars_path = _write_bars(tmp_path, [_bar(), bad_bar])
    preflight = _write_preflight(tmp_path)

    report = build_strategy_replay_scenario_report(
        strategy_input_bars_path=bars_path,
        preflight_report_path=preflight,
        output_dir=tmp_path / "out",
    )

    assert report.status == "warn"
    assert report.input_bar_count == 2
    assert report.scenario_count == 1
    assert any(issue.code == "skipped_unusable_bars" for issue in report.issues)


def test_write_strategy_replay_scenario_report_creates_outputs(tmp_path):
    bars_path = _write_bars(tmp_path, [_bar()])
    preflight = _write_preflight(tmp_path)
    report = build_strategy_replay_scenario_report(
        strategy_input_bars_path=bars_path,
        preflight_report_path=preflight,
        output_dir=tmp_path / "out",
    )

    outputs = write_strategy_replay_scenario_report(report, tmp_path / "out")

    assert outputs["scenario_manifest_json"].exists()
    assert outputs["scenarios_jsonl"].exists()
    assert outputs["scenario_manifest_txt"].exists()
    assert outputs["manifest_json"].exists()


def test_build_and_write_scenario_manifest_contains_safety_and_no_profit_claim(tmp_path):
    bars_path = _write_bars(tmp_path, [_bar()])
    preflight = _write_preflight(tmp_path)

    report, outputs = build_and_write_strategy_replay_scenario_report(
        strategy_input_bars_path=bars_path,
        preflight_report_path=preflight,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["scenario_manifest_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert "does not run strategy logic" in text_report
    assert "not a profitability claim" in text_report
    assert manifest["scenario_count"] == 1


def test_documentation_mentions_strategy_replay_scenario_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_STRATEGY_REPLAY_SCENARIO.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_strategy_replay_scenario.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
