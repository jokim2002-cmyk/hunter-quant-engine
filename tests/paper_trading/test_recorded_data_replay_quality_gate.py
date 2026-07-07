import json
from pathlib import Path

from src.paper_trading.recorded_data_replay_quality_gate import (
    audit_dataset_payload,
    build_and_write_quality_gate_report,
    build_quality_gate_report,
    safety_notice,
    write_quality_gate_report,
)


def _valid_payload():
    return {
        "sources": [
            {
                "path": "sample.csv",
                "status": "parsed",
                "discovered_records": 1,
                "normalized_records": 1,
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
            }
        ],
    }


def test_safety_notice_preserves_paper_only_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "brokers" in notice
    assert "real orders" in notice
    assert "prove profitability" in notice


def test_audit_dataset_payload_passes_valid_dataset(tmp_path):
    report = audit_dataset_payload(
        _valid_payload(),
        dataset_path=tmp_path / "dataset.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.source_count == 1
    assert report.record_count == 1
    assert report.issues == []


def test_build_quality_gate_report_fails_when_dataset_missing(tmp_path):
    report = build_quality_gate_report(
        dataset_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.issues[0].code == "dataset_missing"


def test_build_quality_gate_report_fails_invalid_json(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text("{not-json", encoding="utf-8")

    report = build_quality_gate_report(dataset_path=dataset, output_dir=tmp_path / "out")

    assert report.status == "fail"
    assert report.issues[0].code == "dataset_invalid_json"


def test_build_quality_gate_report_fails_invalid_shape(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    report = build_quality_gate_report(dataset_path=dataset, output_dir=tmp_path / "out")

    assert report.status == "fail"
    assert report.issues[0].code == "dataset_invalid_shape"


def test_audit_dataset_payload_fails_when_no_records(tmp_path):
    report = audit_dataset_payload(
        {"sources": [], "records": []},
        dataset_path=tmp_path / "dataset.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "no_replay_records" for issue in report.issues)


def test_missing_close_is_fail(tmp_path):
    payload = _valid_payload()
    payload["records"][0]["close"] = None

    report = audit_dataset_payload(
        payload,
        dataset_path=tmp_path / "dataset.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "missing_close" for issue in report.issues)


def test_missing_volume_is_info_not_failure(tmp_path):
    payload = _valid_payload()
    payload["records"][0]["volume"] = None

    report = audit_dataset_payload(
        payload,
        dataset_path=tmp_path / "dataset.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert any(issue.code == "missing_volume" for issue in report.issues)


def test_invalid_ohlc_relationship_fails(tmp_path):
    payload = _valid_payload()
    payload["records"][0]["high"] = 90

    report = audit_dataset_payload(
        payload,
        dataset_path=tmp_path / "dataset.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "invalid_ohlc" for issue in report.issues)


def test_negative_volume_fails(tmp_path):
    payload = _valid_payload()
    payload["records"][0]["volume"] = -1

    report = audit_dataset_payload(
        payload,
        dataset_path=tmp_path / "dataset.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "negative_volume" for issue in report.issues)


def test_duplicate_rows_warn(tmp_path):
    payload = _valid_payload()
    payload["records"].append(dict(payload["records"][0]))

    report = audit_dataset_payload(
        payload,
        dataset_path=tmp_path / "dataset.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "warn"
    assert any(issue.code == "duplicate_replay_rows" for issue in report.issues)


def test_out_of_order_timestamps_warn(tmp_path):
    payload = _valid_payload()
    payload["records"].append(
        {
            **payload["records"][0],
            "row_number": 2,
            "timestamp": "2026-01-01T09:14:00+05:30",
        }
    )

    report = audit_dataset_payload(
        payload,
        dataset_path=tmp_path / "dataset.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "warn"
    assert any(issue.code == "out_of_order_timestamps" for issue in report.issues)


def test_source_errors_fail_and_skipped_rows_warn(tmp_path):
    payload = _valid_payload()
    payload["sources"] = [
        {"path": "bad.csv", "status": "error", "skipped_records": 0},
        {"path": "partial.csv", "status": "parsed", "skipped_records": 2},
        {"path": "data.parquet", "status": "skipped", "skipped_records": 0},
    ]

    report = audit_dataset_payload(
        payload,
        dataset_path=tmp_path / "dataset.json",
        output_dir=tmp_path / "out",
    )

    codes = {issue.code for issue in report.issues}
    assert report.status == "fail"
    assert "source_parse_errors" in codes
    assert "skipped_source_rows" in codes
    assert "skipped_sources" in codes


def test_build_and_write_quality_gate_report_creates_outputs(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(_valid_payload()), encoding="utf-8")

    report, outputs = build_and_write_quality_gate_report(
        dataset_path=dataset,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert outputs["quality_gate_json"].exists()
    assert outputs["quality_gate_txt"].exists()
    assert outputs["manifest_json"].exists()

    text_report = outputs["quality_gate_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))
    assert "not a profitability claim" in text_report
    assert manifest["status"] == "pass"


def test_documentation_mentions_replay_quality_gate_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_REPLAY_QUALITY_GATE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_replay_quality_gate.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
