import json
from pathlib import Path

from src.paper_trading.recorded_data_replay_readiness import (
    build_and_write_replay_readiness_report,
    build_replay_readiness_report,
    safety_notice,
    write_replay_readiness_report,
)


def _write_csv(root: Path, high: int = 110) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    source = root / "sample.csv"
    source.write_text(
        "timestamp,open,high,low,close,volume\n"
        f"2026-01-01T09:15:00+05:30,100,{high},95,105,1000\n"
        "2026-01-01T09:16:00+05:30,105,112,101,108,1200\n",
        encoding="utf-8",
    )
    return source


def test_safety_notice_preserves_readiness_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "real orders" in notice
    assert "prove profitability" in notice


def test_readiness_gate_passes_valid_recorded_data(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report = build_replay_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        min_events=1,
    )

    assert report.status == "pass"
    assert report.ready_for_future_paper_replay is True
    assert [stage.stage for stage in report.stage_results] == [
        "recorded_data_replay_evidence",
        "recorded_data_replay_acceptance",
    ]


def test_readiness_gate_fails_when_min_events_not_met(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report = build_replay_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        min_events=3,
    )

    assert report.status == "fail"
    assert report.ready_for_future_paper_replay is False
    assert report.stage_results[1].summary["accepted"] is False


def test_readiness_gate_fails_invalid_replay_evidence(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root, high=90)

    report = build_replay_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        min_events=1,
    )

    assert report.status == "fail"
    assert report.ready_for_future_paper_replay is False
    assert report.stage_results[0].status == "fail"
    assert report.stage_results[1].status == "fail"


def test_readiness_gate_can_allow_warning_readiness(tmp_path):
    recorded_root = tmp_path / "recorded"
    recorded_root.mkdir(parents=True, exist_ok=True)
    (recorded_root / "sample.csv").write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-01-01T09:16:00+05:30,105,112,101,108,1200\n"
        "2026-01-01T09:15:00+05:30,100,110,95,105,1000\n",
        encoding="utf-8",
    )

    report = build_replay_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        min_events=1,
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_paper_replay is True
    assert report.stage_results[1].accepted is True


def test_readiness_gate_blocks_warnings_by_default(tmp_path):
    recorded_root = tmp_path / "recorded"
    recorded_root.mkdir(parents=True, exist_ok=True)
    (recorded_root / "sample.csv").write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-01-01T09:16:00+05:30,105,112,101,108,1200\n"
        "2026-01-01T09:15:00+05:30,100,110,95,105,1000\n",
        encoding="utf-8",
    )

    report = build_replay_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        min_events=1,
        allow_warnings=False,
    )

    assert report.status == "fail"
    assert report.ready_for_future_paper_replay is False


def test_readiness_gate_max_records_flows_into_acceptance(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report = build_replay_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        min_events=2,
        max_records=1,
    )

    assert report.status == "fail"
    assert report.stage_results[1].summary["replayed_event_count"] == 1


def test_write_replay_readiness_report_creates_outputs(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)
    report = build_replay_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
    )

    outputs = write_replay_readiness_report(report, tmp_path / "readiness")

    assert outputs["readiness_report_json"].exists()
    assert outputs["readiness_report_txt"].exists()
    assert outputs["manifest_json"].exists()


def test_written_readiness_report_contains_safety_and_no_profit_claim(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report, outputs = build_and_write_replay_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
    )

    text_report = outputs["readiness_report_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.ready_for_future_paper_replay is True
    assert "does not run strategies" in text_report
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_paper_replay"] is True


def test_readiness_outputs_include_stage_file_references(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    _report, outputs = build_and_write_replay_readiness_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
    )

    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))
    evidence_stage = manifest["stages"][0]
    acceptance_stage = manifest["stages"][1]

    assert "evidence_summary_json" in evidence_stage["output_files"]
    assert "acceptance_gate_json" in acceptance_stage["output_files"]


def test_documentation_mentions_replay_readiness_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_REPLAY_READINESS.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_replay_readiness.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
