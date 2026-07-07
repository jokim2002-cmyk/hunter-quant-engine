import json
from pathlib import Path

from src.paper_trading.recorded_data_strategy_replay_scenario_readiness import (
    build_and_write_strategy_replay_scenario_readiness_report,
    build_strategy_replay_scenario_readiness_report,
    safety_notice,
    write_strategy_replay_scenario_readiness_report,
)


def _write_csv(root: Path, rows: list[str] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    source = root / "sample.csv"
    body = rows or [
        "2026-01-01T09:15:00+05:30,100,110,95,105,1000",
        "2026-01-01T09:16:00+05:30,105,112,101,108,1200",
    ]
    source.write_text(
        "timestamp,open,high,low,close,volume\n" + "\n".join(body) + "\n",
        encoding="utf-8",
    )
    return source


def _build_report(tmp_path, *, rows=None, **kwargs):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root, rows=rows)
    return build_strategy_replay_scenario_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        replay_acceptance_output_dir=tmp_path / "replay_acceptance",
        replay_readiness_output_dir=tmp_path / "replay_readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
        scenario_output_dir=tmp_path / "scenario",
        scenario_acceptance_output_dir=tmp_path / "scenario_acceptance",
        scenario_readiness_output_dir=tmp_path / "scenario_readiness",
        **kwargs,
    )


def test_safety_notice_preserves_scenario_readiness_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "create signals" in notice
    assert "real orders" in notice
    assert "prove profitability" in notice


def test_scenario_readiness_passes_valid_recorded_data(tmp_path):
    report = _build_report(
        tmp_path,
        min_events=1,
        min_bars=1,
        min_scenarios=1,
        min_bars_per_scenario=1,
    )

    assert report.status == "pass"
    assert report.ready_for_future_paper_strategy_replay is True
    assert [stage.stage for stage in report.stage_results] == [
        "recorded_data_strategy_replay_preflight",
        "recorded_data_strategy_replay_scenario",
        "recorded_data_strategy_replay_scenario_acceptance",
    ]


def test_scenario_readiness_fails_when_min_events_not_met(tmp_path):
    report = _build_report(
        tmp_path,
        min_events=3,
        min_bars=1,
        min_scenarios=1,
        min_bars_per_scenario=1,
    )

    assert report.status == "fail"
    assert report.ready_for_future_paper_strategy_replay is False
    assert report.stage_results[0].accepted is False


def test_scenario_readiness_fails_when_min_bars_not_met(tmp_path):
    report = _build_report(
        tmp_path,
        min_events=1,
        min_bars=3,
        min_scenarios=1,
        min_bars_per_scenario=1,
    )

    assert report.status == "fail"
    assert report.stage_results[0].status == "fail"


def test_scenario_readiness_fails_when_min_scenarios_not_met(tmp_path):
    report = _build_report(
        tmp_path,
        min_events=1,
        min_bars=1,
        min_scenarios=2,
        min_bars_per_scenario=1,
    )

    assert report.status == "fail"
    assert report.stage_results[2].accepted is False
    assert report.stage_results[2].summary["scenario_count"] == 1


def test_scenario_readiness_fails_invalid_recorded_data(tmp_path):
    report = _build_report(
        tmp_path,
        rows=["2026-01-01T09:15:00+05:30,100,90,95,105,1000"],
        min_events=1,
        min_bars=1,
        min_scenarios=1,
        min_bars_per_scenario=1,
    )

    assert report.status == "fail"
    assert report.ready_for_future_paper_strategy_replay is False
    assert report.stage_results[0].status == "fail"


def test_scenario_readiness_can_allow_warning_status(tmp_path):
    report = _build_report(
        tmp_path,
        rows=[
            "2026-01-01T09:16:00+05:30,105,112,101,108,1200",
            "2026-01-01T09:15:00+05:30,100,110,95,105,1000",
        ],
        min_events=1,
        min_bars=1,
        min_scenarios=1,
        min_bars_per_scenario=1,
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_paper_strategy_replay is True


def test_scenario_readiness_blocks_warning_status_by_default(tmp_path):
    report = _build_report(
        tmp_path,
        rows=[
            "2026-01-01T09:16:00+05:30,105,112,101,108,1200",
            "2026-01-01T09:15:00+05:30,100,110,95,105,1000",
        ],
        min_events=1,
        min_bars=1,
        min_scenarios=1,
        min_bars_per_scenario=1,
        allow_warnings=False,
    )

    assert report.status == "fail"
    assert report.ready_for_future_paper_strategy_replay is False


def test_scenario_readiness_max_scenarios_can_drive_acceptance_failure(tmp_path):
    first_root = tmp_path / "recorded"
    first_root.mkdir(parents=True, exist_ok=True)
    _write_csv(first_root / "a")
    _write_csv(first_root / "b")

    report = build_strategy_replay_scenario_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[first_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        replay_acceptance_output_dir=tmp_path / "replay_acceptance",
        replay_readiness_output_dir=tmp_path / "replay_readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
        scenario_output_dir=tmp_path / "scenario",
        scenario_acceptance_output_dir=tmp_path / "scenario_acceptance",
        scenario_readiness_output_dir=tmp_path / "scenario_readiness",
        min_events=1,
        min_bars=1,
        min_scenarios=2,
        min_bars_per_scenario=1,
        max_scenarios=1,
    )

    assert report.status == "fail"
    assert report.stage_results[1].summary["scenario_count"] == 1
    assert report.stage_results[2].accepted is False


def test_write_scenario_readiness_report_creates_outputs(tmp_path):
    report = _build_report(tmp_path)

    outputs = write_strategy_replay_scenario_readiness_report(
        report,
        tmp_path / "scenario_readiness",
    )

    assert outputs["scenario_readiness_report_json"].exists()
    assert outputs["scenario_readiness_report_txt"].exists()
    assert outputs["manifest_json"].exists()


def test_build_and_write_scenario_readiness_contains_safety_and_no_profit_claim(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report, outputs = build_and_write_strategy_replay_scenario_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        replay_acceptance_output_dir=tmp_path / "replay_acceptance",
        replay_readiness_output_dir=tmp_path / "replay_readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
        scenario_output_dir=tmp_path / "scenario",
        scenario_acceptance_output_dir=tmp_path / "scenario_acceptance",
        scenario_readiness_output_dir=tmp_path / "scenario_readiness",
    )

    text_report = outputs["scenario_readiness_report_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.ready_for_future_paper_strategy_replay is True
    assert "does not run strategies" in text_report
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_paper_strategy_replay"] is True


def test_documentation_mentions_strategy_replay_scenario_readiness_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_STRATEGY_REPLAY_SCENARIO_READINESS.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_strategy_replay_scenario_readiness.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
