import json
from pathlib import Path

from src.paper_trading.recorded_data_replay_acceptance import (
    build_acceptance_report,
    build_and_write_acceptance_report,
    safety_notice,
    write_acceptance_report,
)


def _valid_summary(status="pass", replayed_events=2, dry_run_status="pass"):
    return {
        "status": status,
        "stage_results": [
            {
                "stage": "recorded_data_replay_dataset",
                "status": "pass",
                "summary": {
                    "source_count": 1,
                    "normalized_record_count": 2,
                },
            },
            {
                "stage": "recorded_data_replay_quality_gate",
                "status": "pass",
                "summary": {
                    "record_count": 2,
                    "issue_count": 0,
                },
            },
            {
                "stage": "recorded_data_replay_dry_run",
                "status": dry_run_status,
                "summary": {
                    "input_record_count": 2,
                    "replayed_event_count": replayed_events,
                    "issue_count": 0,
                },
            },
        ],
    }


def _write_summary(tmp_path, payload):
    summary = tmp_path / "evidence_summary.json"
    summary.write_text(json.dumps(payload), encoding="utf-8")
    return summary


def test_safety_notice_preserves_acceptance_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "real orders" in notice
    assert "prove profitability" in notice


def test_missing_evidence_summary_fails(tmp_path):
    report = build_acceptance_report(
        evidence_summary_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "evidence_summary_missing" for issue in report.issues)


def test_invalid_json_fails(tmp_path):
    summary = tmp_path / "evidence_summary.json"
    summary.write_text("{bad-json", encoding="utf-8")

    report = build_acceptance_report(
        evidence_summary_path=summary,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "evidence_summary_invalid_json" for issue in report.issues)


def test_invalid_shape_fails(tmp_path):
    summary = _write_summary(tmp_path, ["not", "object"])

    report = build_acceptance_report(
        evidence_summary_path=summary,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "evidence_summary_invalid_shape" for issue in report.issues)


def test_valid_summary_is_accepted(tmp_path):
    summary = _write_summary(tmp_path, _valid_summary())

    report = build_acceptance_report(
        evidence_summary_path=summary,
        output_dir=tmp_path / "out",
        min_events=1,
    )

    assert report.status == "pass"
    assert report.accepted is True
    assert report.stage_count == 3
    assert report.replayed_event_count == 2


def test_min_events_rule_can_fail_acceptance(tmp_path):
    summary = _write_summary(tmp_path, _valid_summary(replayed_events=2))

    report = build_acceptance_report(
        evidence_summary_path=summary,
        output_dir=tmp_path / "out",
        min_events=3,
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "insufficient_replayed_events" for issue in report.issues)


def test_bundle_fail_status_fails_acceptance(tmp_path):
    summary = _write_summary(tmp_path, _valid_summary(status="fail"))

    report = build_acceptance_report(
        evidence_summary_path=summary,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "bundle_failed" for issue in report.issues)


def test_stage_fail_status_fails_acceptance(tmp_path):
    payload = _valid_summary()
    payload["stage_results"][1]["status"] = "fail"
    summary = _write_summary(tmp_path, payload)

    report = build_acceptance_report(
        evidence_summary_path=summary,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_data_replay_quality_gate_failed"
        for issue in report.issues
    )


def test_warning_stage_not_allowed_by_default(tmp_path):
    summary = _write_summary(
        tmp_path,
        _valid_summary(status="warn", dry_run_status="warn"),
    )

    report = build_acceptance_report(
        evidence_summary_path=summary,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "bundle_warn" for issue in report.issues)


def test_warning_stage_can_be_accepted_when_allowed(tmp_path):
    summary = _write_summary(
        tmp_path,
        _valid_summary(status="warn", dry_run_status="warn"),
    )

    report = build_acceptance_report(
        evidence_summary_path=summary,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.accepted is True
    assert any(issue.code == "bundle_warn" for issue in report.issues)


def test_write_acceptance_report_creates_outputs(tmp_path):
    summary = _write_summary(tmp_path, _valid_summary())
    report = build_acceptance_report(
        evidence_summary_path=summary,
        output_dir=tmp_path / "out",
    )

    outputs = write_acceptance_report(report, tmp_path / "out")

    assert outputs["acceptance_gate_json"].exists()
    assert outputs["acceptance_gate_txt"].exists()
    assert outputs["manifest_json"].exists()
    assert "not a profitability claim" in outputs["acceptance_gate_txt"].read_text(
        encoding="utf-8"
    )


def test_build_and_write_acceptance_report_manifest(tmp_path):
    summary = _write_summary(tmp_path, _valid_summary())

    report, outputs = build_and_write_acceptance_report(
        evidence_summary_path=summary,
        output_dir=tmp_path / "out",
    )

    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))
    assert report.accepted is True
    assert manifest["accepted"] is True
    assert manifest["replayed_event_count"] == 2


def test_documentation_mentions_replay_acceptance_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_REPLAY_ACCEPTANCE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_replay_acceptance.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
