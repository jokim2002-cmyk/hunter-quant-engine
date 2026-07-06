"""Tests that all-in-one replay journal shortcut uses pretty runs viewer."""

from pathlib import Path


def test_all_in_one_replay_journal_shortcut_uses_pretty_runs_viewer():
    text = Path("hqe_paper_replay_journal_all.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "call hqe_paper_replay_journal.bat" in text
    assert "call hqe_paper_replay_journal_summary.bat" in text
    assert "call hqe_paper_replay_journal_runs.bat" in text
    assert "call hqe_paper_replay_journal_folder.bat" in text
    assert "call hqe_paper_replay_journal_index.bat" not in text
    assert "lists runs" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
