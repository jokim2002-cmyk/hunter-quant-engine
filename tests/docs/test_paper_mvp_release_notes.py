"""Tests for Paper MVP v0.1 release notes."""

from pathlib import Path


RELEASE_NOTES = Path("docs/PAPER_MVP_V0_1_RELEASE_NOTES.md")


def test_paper_mvp_release_notes_document_safety_boundary():
    text = RELEASE_NOTES.read_text(encoding="utf-8")

    assert "Paper MVP v0.1 is paper/simulation only." in text
    assert "It does not place broker orders." in text
    assert "It does not use live market data." in text
    assert "It does not use real money." in text
    assert "It does not claim profitability." in text


def test_paper_mvp_release_notes_document_completed_modules():
    text = RELEASE_NOTES.read_text(encoding="utf-8")

    assert "Strategy-to-paper bridge." in text
    assert "Paper backtest evidence runner." in text
    assert "Paper MVP operator demo workflow." in text
    assert "Paper MVP release gate." in text


def test_paper_mvp_release_notes_document_operator_commands():
    text = RELEASE_NOTES.read_text(encoding="utf-8")

    assert ".\\hqe_quick_check.bat" in text
    assert ".\\hqe_paper_mvp_operator_demo.bat" in text
    assert ".\\hqe_paper_replay_journal_all.bat" in text
    assert ".\\hqe_paper_mvp_release_check.bat" in text


def test_paper_mvp_release_notes_document_release_tag_and_next_phase():
    text = RELEASE_NOTES.read_text(encoding="utf-8")

    assert "v0.1-paper-mvp" in text
    assert "Live trading remains deferred" in text
    assert "This release does not prove profitability." in text


def test_roadmap_links_paper_mvp_release_notes():
    text = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert "docs/PAPER_MVP_V0_1_RELEASE_NOTES.md" in text
    assert "Paper MVP v0.1 release close completed." in text
