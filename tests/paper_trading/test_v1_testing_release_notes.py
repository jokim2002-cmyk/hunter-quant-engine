import json
from pathlib import Path

from src.paper_trading.v1_testing_release_notes import (
    build_and_write_v1_testing_release_notes_report,
    build_v1_testing_release_notes_report,
    safety_notice,
)


def _handoff(tmp_path, status="pass", ready=True, final_outputs=True, issues=None, checklist=None):
    final_report = tmp_path / "backtest_report.txt"
    final_metrics = tmp_path / "backtest_metrics.json"
    final_ledger = tmp_path / "backtest_trade_ledger.json"

    if final_outputs:
        final_report.write_text("paper report\nnot a profitability claim\n", encoding="utf-8")
        final_metrics.write_text("{}", encoding="utf-8")
        final_ledger.write_text("{}", encoding="utf-8")

    if checklist is None:
        checklist = [
            {"item_index": 1, "category": "safety", "action": "Confirm LONG = CE BUY", "required": True},
            {"item_index": 2, "category": "safety", "action": "Confirm SHORT = PE BUY", "required": True},
        ]

    return {
        "status": status,
        "ready_for_future_v1_release_notes": ready,
        "final_backtest_report_path": str(final_report),
        "final_metrics_path": str(final_metrics),
        "final_trade_ledger_path": str(final_ledger),
        "safety_notice": "paper/simulation v1.0 testing edition operator handoff only",
        "issues": [] if issues is None else issues,
        "checklist": checklist,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_release_notes_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation v1.0 testing edition release notes" in notice
    assert "recorded replay paper backtest evidence" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_operator_handoff_pack_fails(tmp_path):
    report = build_v1_testing_release_notes_report(
        operator_handoff_pack_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_v1_release_candidate_gate is False
    assert any(issue.code == "operator_handoff_pack_missing" for issue in report.issues)


def test_valid_handoff_creates_release_notes(tmp_path):
    handoff = _write_json(tmp_path / "handoff.json", _handoff(tmp_path))

    report = build_v1_testing_release_notes_report(
        operator_handoff_pack_path=handoff,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_future_v1_release_candidate_gate is True
    assert report.release_version == "v1.0-testing-edition"
    assert report.handoff_status == "pass"
    assert report.handoff_ready is True
    assert report.section_count == 5
    assert any(section.title == "Trading safety contract" for section in report.sections)


def test_warning_handoff_fails_by_default(tmp_path):
    handoff = _write_json(
        tmp_path / "handoff.json",
        _handoff(tmp_path, status="warn", ready=True),
    )

    report = build_v1_testing_release_notes_report(
        operator_handoff_pack_path=handoff,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "operator_handoff_pack_warn" for issue in report.issues)


def test_warning_handoff_can_remain_warning_when_allowed(tmp_path):
    handoff = _write_json(
        tmp_path / "handoff.json",
        _handoff(tmp_path, status="warn", ready=True),
    )

    report = build_v1_testing_release_notes_report(
        operator_handoff_pack_path=handoff,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_v1_release_candidate_gate is True


def test_not_ready_handoff_fails(tmp_path):
    handoff = _write_json(
        tmp_path / "handoff.json",
        _handoff(tmp_path, status="pass", ready=False),
    )

    report = build_v1_testing_release_notes_report(
        operator_handoff_pack_path=handoff,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "operator_handoff_pack_not_ready" for issue in report.issues)


def test_missing_final_output_paths_fail(tmp_path):
    payload = _handoff(tmp_path)
    payload["final_metrics_path"] = ""
    handoff = _write_json(tmp_path / "handoff.json", payload)

    report = build_v1_testing_release_notes_report(
        operator_handoff_pack_path=handoff,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "handoff_final_output_paths_missing" for issue in report.issues)


def test_final_outputs_missing_on_disk_fail_by_default(tmp_path):
    handoff = _write_json(
        tmp_path / "handoff.json",
        _handoff(tmp_path, final_outputs=False),
    )

    report = build_v1_testing_release_notes_report(
        operator_handoff_pack_path=handoff,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "handoff_final_outputs_missing_on_disk" for issue in report.issues)


def test_final_output_existence_check_can_be_skipped(tmp_path):
    handoff = _write_json(
        tmp_path / "handoff.json",
        _handoff(tmp_path, final_outputs=False),
    )

    report = build_v1_testing_release_notes_report(
        operator_handoff_pack_path=handoff,
        output_dir=tmp_path / "out",
        require_final_outputs_exist=False,
    )

    assert report.status == "pass"
    assert report.ready_for_future_v1_release_candidate_gate is True


def test_handoff_fail_issues_fail_release_notes(tmp_path):
    handoff = _write_json(
        tmp_path / "handoff.json",
        _handoff(
            tmp_path,
            issues=[
                {
                    "severity": "fail",
                    "code": "example_fail",
                    "count": 1,
                    "message": "example",
                }
            ],
        ),
    )

    report = build_v1_testing_release_notes_report(
        operator_handoff_pack_path=handoff,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "handoff_contains_fail_issues" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_release_notes(tmp_path):
    handoff = _write_json(tmp_path / "handoff.json", _handoff(tmp_path))

    report, outputs = build_and_write_v1_testing_release_notes_report(
        operator_handoff_pack_path=handoff,
        output_dir=tmp_path / "out",
    )

    md = outputs["v1_testing_release_notes_md"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/V1_TESTING_RELEASE_NOTES_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["v1_testing_release_notes_json"].exists()
    assert outputs["v1_testing_release_notes_txt"].exists()
    assert "not a profitability claim" in md.lower()
    assert manifest["ready_for_future_v1_release_candidate_gate"] is True
    assert "hqe_v1_testing_release_notes.bat" in combined_docs
    assert "paper-only v1.0 testing release notes" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
