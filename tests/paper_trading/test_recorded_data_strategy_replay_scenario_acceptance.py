import json
from pathlib import Path

from src.paper_trading.recorded_data_strategy_replay_scenario_acceptance import (
    build_and_write_scenario_acceptance_report,
    build_scenario_acceptance_report,
    safety_notice,
    write_scenario_acceptance_report,
)


def _scenario(
    scenario_id="recorded_strategy_replay_scenario_001",
    bar_count=2,
    source_path="sample.csv",
):
    return {
        "scenario_id": scenario_id,
        "source_path": source_path,
        "source_type": "csv",
        "bar_count": bar_count,
        "first_timestamp": "2026-01-01T09:15:00+05:30",
        "last_timestamp": "2026-01-01T09:16:00+05:30",
        "first_bar_index": 1,
        "last_bar_index": bar_count,
        "data_mode": "recorded_replay",
        "execution_mode": "paper_simulation_only",
    }


def _manifest(status="pass", scenarios=None):
    return {
        "status": status,
        "scenario_count": len(scenarios or [_scenario()]),
        "scenarios": scenarios or [_scenario()],
    }


def _write_manifest(tmp_path, payload):
    path = tmp_path / "scenario_manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_scenario_acceptance_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "create signals" in notice
    assert "real orders" in notice
    assert "prove profitability" in notice


def test_missing_scenario_manifest_fails(tmp_path):
    report = build_scenario_acceptance_report(
        scenario_manifest_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "scenario_manifest_missing" for issue in report.issues)


def test_invalid_json_fails(tmp_path):
    path = tmp_path / "scenario_manifest.json"
    path.write_text("{bad-json", encoding="utf-8")

    report = build_scenario_acceptance_report(
        scenario_manifest_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "scenario_manifest_invalid_json" for issue in report.issues)


def test_invalid_shape_fails(tmp_path):
    path = _write_manifest(tmp_path, ["not", "object"])

    report = build_scenario_acceptance_report(
        scenario_manifest_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "scenario_manifest_invalid_shape" for issue in report.issues)


def test_valid_manifest_is_accepted(tmp_path):
    path = _write_manifest(tmp_path, _manifest())

    report = build_scenario_acceptance_report(
        scenario_manifest_path=path,
        output_dir=tmp_path / "out",
        min_scenarios=1,
        min_bars_per_scenario=1,
    )

    assert report.status == "pass"
    assert report.accepted is True
    assert report.scenario_count == 1
    assert report.total_bar_count == 2


def test_min_scenarios_rule_can_fail(tmp_path):
    path = _write_manifest(tmp_path, _manifest(scenarios=[_scenario()]))

    report = build_scenario_acceptance_report(
        scenario_manifest_path=path,
        output_dir=tmp_path / "out",
        min_scenarios=2,
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "insufficient_scenarios" for issue in report.issues)


def test_min_bars_per_scenario_rule_can_fail(tmp_path):
    path = _write_manifest(tmp_path, _manifest(scenarios=[_scenario(bar_count=1)]))

    report = build_scenario_acceptance_report(
        scenario_manifest_path=path,
        output_dir=tmp_path / "out",
        min_bars_per_scenario=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "scenario_below_min_bars" for issue in report.issues)


def test_manifest_fail_status_fails_acceptance(tmp_path):
    path = _write_manifest(tmp_path, _manifest(status="fail"))

    report = build_scenario_acceptance_report(
        scenario_manifest_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "scenario_manifest_failed" for issue in report.issues)


def test_manifest_warn_is_failed_by_default(tmp_path):
    path = _write_manifest(tmp_path, _manifest(status="warn"))

    report = build_scenario_acceptance_report(
        scenario_manifest_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "scenario_manifest_warn" for issue in report.issues)


def test_manifest_warn_can_be_accepted_when_allowed(tmp_path):
    path = _write_manifest(tmp_path, _manifest(status="warn"))

    report = build_scenario_acceptance_report(
        scenario_manifest_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.accepted is True
    assert any(issue.code == "scenario_manifest_warn" for issue in report.issues)


def test_write_scenario_acceptance_report_creates_outputs(tmp_path):
    path = _write_manifest(tmp_path, _manifest())
    report = build_scenario_acceptance_report(
        scenario_manifest_path=path,
        output_dir=tmp_path / "out",
    )

    outputs = write_scenario_acceptance_report(report, tmp_path / "out")

    assert outputs["scenario_acceptance_json"].exists()
    assert outputs["scenario_acceptance_txt"].exists()
    assert outputs["manifest_json"].exists()
    assert "not a profitability claim" in outputs["scenario_acceptance_txt"].read_text(
        encoding="utf-8"
    )


def test_build_and_write_scenario_acceptance_manifest(tmp_path):
    path = _write_manifest(tmp_path, _manifest())

    report, outputs = build_and_write_scenario_acceptance_report(
        scenario_manifest_path=path,
        output_dir=tmp_path / "out",
    )

    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))
    assert report.accepted is True
    assert manifest["accepted"] is True
    assert manifest["scenario_count"] == 1


def test_documentation_mentions_strategy_replay_scenario_acceptance_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_STRATEGY_REPLAY_SCENARIO_ACCEPTANCE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_strategy_replay_scenario_acceptance.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
