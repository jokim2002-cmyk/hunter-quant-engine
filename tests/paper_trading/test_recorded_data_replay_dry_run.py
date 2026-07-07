import json
from pathlib import Path

from src.paper_trading.recorded_data_replay_dry_run import (
    build_and_write_replay_dry_run_report,
    build_replay_dry_run_report,
    safety_notice,
    write_replay_dry_run_report,
)


def _valid_dataset_payload():
    return {
        "sources": [
            {
                "path": "sample.csv",
                "status": "parsed",
                "discovered_records": 2,
                "normalized_records": 2,
                "skipped_records": 0,
            }
        ],
        "records": [
            {
                "source_path": "sample.csv",
                "source_type": "csv",
                "row_number": 1,
                "timestamp": "2026-01-01T09:15:00+05:30",
                "open": 100,
                "high": 110,
                "low": 95,
                "close": 105,
                "volume": 1000,
                "missing_fields": [],
            },
            {
                "source_path": "sample.csv",
                "source_type": "csv",
                "row_number": 2,
                "timestamp": "2026-01-01T09:16:00+05:30",
                "open": "105",
                "high": "112",
                "low": "101",
                "close": "108",
                "volume": "1,200",
                "missing_fields": [],
            },
        ],
    }


def _write_dataset(tmp_path, payload=None):
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(payload or _valid_dataset_payload()), encoding="utf-8")
    return dataset


def _write_quality_gate(tmp_path, status="pass"):
    quality_gate = tmp_path / "quality_gate.json"
    quality_gate.write_text(json.dumps({"status": status}), encoding="utf-8")
    return quality_gate


def test_safety_notice_preserves_replay_dry_run_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "real orders" in notice
    assert "prove profitability" in notice


def test_missing_dataset_fails(tmp_path):
    report = build_replay_dry_run_report(
        dataset_path=tmp_path / "missing.json",
        quality_gate_path=tmp_path / "quality_gate.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.replayed_event_count == 0
    assert any(issue.code == "dataset_missing" for issue in report.issues)


def test_invalid_dataset_json_fails(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text("{bad-json", encoding="utf-8")

    report = build_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=tmp_path / "quality_gate.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dataset_invalid_json" for issue in report.issues)


def test_invalid_dataset_shape_fails(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(["not", "object"]), encoding="utf-8")

    report = build_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=tmp_path / "quality_gate.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dataset_invalid_shape" for issue in report.issues)


def test_valid_dataset_produces_deterministic_events(tmp_path):
    dataset = _write_dataset(tmp_path)
    quality_gate = _write_quality_gate(tmp_path, "pass")

    report = build_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=quality_gate,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.input_record_count == 2
    assert report.replayed_event_count == 2
    assert report.events[0].event_index == 1
    assert report.events[1].event_index == 2
    assert report.first_timestamp == "2026-01-01T09:15:00+05:30"
    assert report.last_timestamp == "2026-01-01T09:16:00+05:30"


def test_max_records_limits_dry_run(tmp_path):
    dataset = _write_dataset(tmp_path)
    quality_gate = _write_quality_gate(tmp_path, "pass")

    report = build_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=quality_gate,
        output_dir=tmp_path / "out",
        max_records=1,
    )

    assert report.input_record_count == 1
    assert report.replayed_event_count == 1
    assert report.last_timestamp == "2026-01-01T09:15:00+05:30"


def test_missing_timestamp_or_close_records_are_skipped_with_warning(tmp_path):
    payload = _valid_dataset_payload()
    payload["records"].append(
        {
            "source_path": "sample.csv",
            "source_type": "csv",
            "row_number": 3,
            "timestamp": "",
            "close": None,
        }
    )
    dataset = _write_dataset(tmp_path, payload)
    quality_gate = _write_quality_gate(tmp_path, "pass")

    report = build_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=quality_gate,
        output_dir=tmp_path / "out",
    )

    assert report.status == "warn"
    assert report.input_record_count == 3
    assert report.replayed_event_count == 2
    assert any(issue.code == "skipped_unplayable_records" for issue in report.issues)


def test_event_preserves_float_ohlcv_values(tmp_path):
    dataset = _write_dataset(tmp_path)
    quality_gate = _write_quality_gate(tmp_path, "pass")

    report = build_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=quality_gate,
        output_dir=tmp_path / "out",
    )

    event = report.events[1]
    assert event.open == 105.0
    assert event.high == 112.0
    assert event.low == 101.0
    assert event.close == 108.0
    assert event.volume == 1200.0
    assert event.safety_mode == "paper_simulation_only"


def test_quality_gate_fail_blocks_event_generation(tmp_path):
    dataset = _write_dataset(tmp_path)
    quality_gate = _write_quality_gate(tmp_path, "fail")

    report = build_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=quality_gate,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.replayed_event_count == 0
    assert any(issue.code == "quality_gate_failed" for issue in report.issues)


def test_quality_gate_warn_allows_events_with_warning_status(tmp_path):
    dataset = _write_dataset(tmp_path)
    quality_gate = _write_quality_gate(tmp_path, "warn")

    report = build_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=quality_gate,
        output_dir=tmp_path / "out",
    )

    assert report.status == "warn"
    assert report.replayed_event_count == 2
    assert any(issue.code == "quality_gate_warn" for issue in report.issues)


def test_missing_quality_gate_is_info_only(tmp_path):
    dataset = _write_dataset(tmp_path)

    report = build_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=tmp_path / "missing_quality_gate.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.replayed_event_count == 2
    assert any(issue.code == "quality_gate_missing" for issue in report.issues)


def test_write_replay_dry_run_report_creates_outputs(tmp_path):
    dataset = _write_dataset(tmp_path)
    quality_gate = _write_quality_gate(tmp_path, "pass")
    report = build_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=quality_gate,
        output_dir=tmp_path / "out",
    )

    outputs = write_replay_dry_run_report(report, tmp_path / "out")

    assert outputs["dry_run_report_json"].exists()
    assert outputs["dry_run_events_jsonl"].exists()
    assert outputs["dry_run_report_txt"].exists()
    assert outputs["manifest_json"].exists()
    assert "not a profitability claim" in outputs["dry_run_report_txt"].read_text(
        encoding="utf-8"
    )


def test_build_and_write_replay_dry_run_report_writes_event_jsonl(tmp_path):
    dataset = _write_dataset(tmp_path)
    quality_gate = _write_quality_gate(tmp_path, "pass")

    report, outputs = build_and_write_replay_dry_run_report(
        dataset_path=dataset,
        quality_gate_path=quality_gate,
        output_dir=tmp_path / "out",
    )

    lines = outputs["dry_run_events_jsonl"].read_text(encoding="utf-8").strip().splitlines()
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.replayed_event_count == 2
    assert len(lines) == 2
    assert manifest["replayed_event_count"] == 2


def test_documentation_mentions_replay_dry_run_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_REPLAY_DRY_RUN.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_replay_dry_run.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
