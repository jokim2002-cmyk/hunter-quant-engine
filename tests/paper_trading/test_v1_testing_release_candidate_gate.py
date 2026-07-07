import json
from pathlib import Path

from src.paper_trading.v1_testing_release_candidate_gate import (
    build_and_write_release_candidate_gate_report,
    build_release_candidate_gate_report,
    safety_notice,
)


def _section(title, content="paper evidence"):
    return {
        "section_index": 1,
        "title": title,
        "content": content,
    }


def _notes(tmp_path, status="pass", ready=True, final_outputs=True, issues=None, sections=None):
    final_report = tmp_path / "backtest_report.txt"
    final_metrics = tmp_path / "backtest_metrics.json"
    final_ledger = tmp_path / "backtest_trade_ledger.json"

    if final_outputs:
        final_report.write_text("paper report\nnot a profitability claim\n", encoding="utf-8")
        final_metrics.write_text("{}", encoding="utf-8")
        final_ledger.write_text("{}", encoding="utf-8")

    if sections is None:
        sections = [
            _section(
                "Release summary",
                "HQE v1.0 Testing Edition paper/simulation release.",
            ),
            _section(
                "Backtest evidence outputs",
                "Final backtest report, final metrics, final trade ledger.",
            ),
            _section(
                "Trading safety contract",
                "LONG = CE BUY paper plan only. SHORT = PE BUY paper plan only. NEUTRAL = no trade. No option selling. No broker orders. No real money.",
            ),
            _section(
                "Release limitations",
                "This release is not a profitability claim.",
            ),
            _section(
                "Next release step",
                "Use this for final v1.0 Testing Edition tag close.",
            ),
        ]

    return {
        "release_version": "v1.0-testing-edition",
        "status": status,
        "ready_for_future_v1_release_candidate_gate": ready,
        "section_count": len(sections),
        "final_backtest_report_path": str(final_report),
        "final_metrics_path": str(final_metrics),
        "final_trade_ledger_path": str(final_ledger),
        "safety_notice": "paper/simulation v1.0 testing edition release notes only",
        "issues": [] if issues is None else issues,
        "sections": sections,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_release_candidate_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation v1.0 testing edition release candidate gate" in notice
    assert "release notes evidence" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_release_notes_fails(tmp_path):
    report = build_release_candidate_gate_report(
        release_notes_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_final_v1_testing_release_close is False
    assert any(issue.code == "release_notes_missing" for issue in report.issues)


def test_valid_release_notes_create_candidate_gate(tmp_path):
    notes = _write_json(tmp_path / "notes.json", _notes(tmp_path))

    report = build_release_candidate_gate_report(
        release_notes_path=notes,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_final_v1_testing_release_close is True
    assert report.release_version == "v1.0-testing-edition"
    assert report.release_notes_status == "pass"
    assert report.release_notes_ready is True
    assert report.section_count == 5
    assert report.final_backtest_report_path.endswith("backtest_report.txt")


def test_warning_release_notes_fail_by_default(tmp_path):
    notes = _write_json(
        tmp_path / "notes.json",
        _notes(tmp_path, status="warn", ready=True),
    )

    report = build_release_candidate_gate_report(
        release_notes_path=notes,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "release_notes_warn" for issue in report.issues)


def test_warning_release_notes_can_remain_warning_when_allowed(tmp_path):
    notes = _write_json(
        tmp_path / "notes.json",
        _notes(tmp_path, status="warn", ready=True),
    )

    report = build_release_candidate_gate_report(
        release_notes_path=notes,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_final_v1_testing_release_close is True


def test_not_ready_release_notes_fail(tmp_path):
    notes = _write_json(
        tmp_path / "notes.json",
        _notes(tmp_path, status="pass", ready=False),
    )

    report = build_release_candidate_gate_report(
        release_notes_path=notes,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "release_notes_not_ready" for issue in report.issues)


def test_missing_required_sections_fail(tmp_path):
    notes = _write_json(
        tmp_path / "notes.json",
        _notes(
            tmp_path,
            sections=[
                _section("Release summary"),
                _section("Trading safety contract", "LONG = CE BUY paper plan only. SHORT = PE BUY paper plan only. NEUTRAL = no trade. No option selling. No broker orders. No real money. not a profitability claim."),
            ],
        ),
    )

    report = build_release_candidate_gate_report(
        release_notes_path=notes,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_release_note_sections" for issue in report.issues)
    assert any(issue.code == "required_release_note_sections_missing" for issue in report.issues)


def test_missing_required_safety_phrases_fail(tmp_path):
    bad_sections = [
        _section("Release summary"),
        _section("Backtest evidence outputs"),
        _section("Trading safety contract", "incomplete safety"),
        _section("Release limitations", "incomplete"),
        _section("Next release step"),
    ]
    notes = _write_json(
        tmp_path / "notes.json",
        _notes(tmp_path, sections=bad_sections),
    )

    report = build_release_candidate_gate_report(
        release_notes_path=notes,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_release_note_phrases_missing" for issue in report.issues)


def test_final_outputs_missing_on_disk_fail_by_default(tmp_path):
    notes = _write_json(
        tmp_path / "notes.json",
        _notes(tmp_path, final_outputs=False),
    )

    report = build_release_candidate_gate_report(
        release_notes_path=notes,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "release_note_final_outputs_missing_on_disk" for issue in report.issues)


def test_final_output_existence_check_can_be_skipped(tmp_path):
    notes = _write_json(
        tmp_path / "notes.json",
        _notes(tmp_path, final_outputs=False),
    )

    report = build_release_candidate_gate_report(
        release_notes_path=notes,
        output_dir=tmp_path / "out",
        require_final_outputs_exist=False,
    )

    assert report.status == "pass"
    assert report.ready_for_final_v1_testing_release_close is True


def test_build_and_write_outputs_and_docs_reference_release_candidate_gate(tmp_path):
    notes = _write_json(tmp_path / "notes.json", _notes(tmp_path))

    report, outputs = build_and_write_release_candidate_gate_report(
        release_notes_path=notes,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["v1_testing_release_candidate_gate_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/V1_TESTING_RELEASE_CANDIDATE_GATE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["v1_testing_release_candidate_gate_json"].exists()
    assert "not a profitability claim" in text_report.lower()
    assert manifest["ready_for_final_v1_testing_release_close"] is True
    assert "hqe_v1_testing_release_candidate_gate.bat" in combined_docs
    assert "paper-only v1.0 testing release candidate gate" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
