"""Tests for the paper replay journal all-in-one shortcut."""

from pathlib import Path


def test_paper_replay_journal_all_shortcut_runs_demo_summary_and_folder():
    text = Path("hqe_paper_replay_journal_all.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "call hqe_paper_replay_journal.bat" in text
    assert "call hqe_paper_replay_journal_summary.bat" in text
    assert "call hqe_paper_replay_journal_runs.bat" in text
    assert "call hqe_paper_replay_journal_index.bat" not in text
    assert "call hqe_paper_replay_journal_folder.bat" in text
    assert "lists runs" in text
    assert "paper replay journal workflow complete" in text
    assert "paper pnl is simulation only" in text


def test_paper_replay_journal_all_shortcut_is_safe_local_only():
    text = Path("hqe_paper_replay_journal_all.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
    assert "runs fake paper replay" in text

    assert "import " + "fy" + "ers" not in text
    assert "from " + "fy" + "ers" not in text
    assert "place" + "_order" not in text
    assert "send" + "_order" not in text
    assert "execute" + "_order" not in text
