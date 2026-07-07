import json
from pathlib import Path

from src.paper_trading.recorded_data_replay_evidence import (
    build_and_write_replay_evidence_bundle,
    build_replay_evidence_bundle,
    safety_notice,
    write_replay_evidence_bundle,
)


def _write_csv(root: Path, name: str = "sample.csv") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    source = root / name
    source.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-01-01T09:15:00+05:30,100,110,95,105,1000\n"
        "2026-01-01T09:16:00+05:30,105,112,101,108,1200\n",
        encoding="utf-8",
    )
    return source


def test_safety_notice_preserves_bundle_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "real orders" in notice
    assert "prove profitability" in notice


def test_replay_evidence_bundle_runs_all_stages(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report = build_replay_evidence_bundle(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        bundle_output_dir=tmp_path / "bundle",
    )

    assert report.status == "pass"
    assert [stage.stage for stage in report.stage_results] == [
        "recorded_data_replay_dataset",
        "recorded_data_replay_quality_gate",
        "recorded_data_replay_dry_run",
    ]


def test_bundle_summary_counts_replayed_events(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report = build_replay_evidence_bundle(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        bundle_output_dir=tmp_path / "bundle",
    )

    dry_run_stage = report.stage_results[2]
    assert dry_run_stage.summary["input_record_count"] == 2
    assert dry_run_stage.summary["replayed_event_count"] == 2


def test_max_records_is_passed_to_dry_run_stage(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report = build_replay_evidence_bundle(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        bundle_output_dir=tmp_path / "bundle",
        max_records=1,
    )

    dry_run_stage = report.stage_results[2]
    assert dry_run_stage.summary["input_record_count"] == 1
    assert dry_run_stage.summary["replayed_event_count"] == 1


def test_empty_recorded_roots_create_fail_bundle(tmp_path):
    report = build_replay_evidence_bundle(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[tmp_path / "missing_recorded"],
        base_output_dir=tmp_path / "reports",
        bundle_output_dir=tmp_path / "bundle",
    )

    statuses = [stage.status for stage in report.stage_results]
    assert report.status == "fail"
    assert statuses[0] == "warn"
    assert statuses[1] == "fail"
    assert statuses[2] == "fail"


def test_invalid_ohlc_creates_fail_bundle(tmp_path):
    recorded_root = tmp_path / "recorded"
    recorded_root.mkdir()
    (recorded_root / "bad.csv").write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-01-01T09:15:00+05:30,100,90,95,105,1000\n",
        encoding="utf-8",
    )

    report = build_replay_evidence_bundle(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        bundle_output_dir=tmp_path / "bundle",
    )

    assert report.status == "fail"
    assert report.stage_results[1].status == "fail"
    assert report.stage_results[2].status == "fail"


def test_inventory_path_can_drive_bundle_inputs(tmp_path):
    recorded_root = tmp_path / "recorded"
    source = _write_csv(recorded_root)
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps({"files": [{"file_path": str(source)}]}),
        encoding="utf-8",
    )

    report = build_replay_evidence_bundle(
        inventory_path=inventory,
        recorded_roots=[],
        base_output_dir=tmp_path / "reports",
        bundle_output_dir=tmp_path / "bundle",
    )

    assert report.status == "pass"
    assert report.stage_results[0].summary["normalized_record_count"] == 2


def test_write_replay_evidence_bundle_creates_outputs(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)
    report = build_replay_evidence_bundle(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        bundle_output_dir=tmp_path / "bundle",
    )

    outputs = write_replay_evidence_bundle(report, tmp_path / "bundle")

    assert outputs["evidence_summary_json"].exists()
    assert outputs["evidence_summary_txt"].exists()
    assert outputs["manifest_json"].exists()


def test_written_bundle_contains_safety_and_no_profit_claim(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)
    report, outputs = build_and_write_replay_evidence_bundle(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        bundle_output_dir=tmp_path / "bundle",
    )

    text_report = outputs["evidence_summary_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert "does not run strategies" in text_report
    assert "not a profitability claim" in text_report
    assert manifest["stage_count"] == 3


def test_bundle_manifest_includes_stage_output_files(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    _report, outputs = build_and_write_replay_evidence_bundle(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        bundle_output_dir=tmp_path / "bundle",
    )

    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))
    stage_outputs = manifest["stages"][0]["output_files"]

    assert "dataset_json" in stage_outputs
    assert "dataset_txt" in stage_outputs


def test_bundle_writes_stage_reports_under_base_output_dir(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)
    base_output = tmp_path / "reports"

    build_and_write_replay_evidence_bundle(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=base_output,
        bundle_output_dir=tmp_path / "bundle",
    )

    assert (base_output / "recorded_data_replay_dataset" / "dataset.json").exists()
    assert (
        base_output
        / "recorded_data_replay_quality_gate"
        / "quality_gate.json"
    ).exists()
    assert (
        base_output
        / "recorded_data_replay_dry_run"
        / "dry_run_events.jsonl"
    ).exists()


def test_documentation_mentions_replay_evidence_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_REPLAY_EVIDENCE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_replay_evidence.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
