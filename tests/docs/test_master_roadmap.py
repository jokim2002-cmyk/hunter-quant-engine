"""Tests for the master roadmap current status override."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_master_roadmap_has_current_status_override_before_historical_notes():
    text = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8")

    current_index = text.index("Current Status Override - July 2026")
    historical_index = text.index("648 tests passing")

    assert current_index < historical_index
    assert "1396 tests passing after friendly replay journal summary viewer." in text
    assert "Paper trading demo/report workflow completed." in text
    assert "Paper journal persistence skeleton completed." in text
    assert "Replay journal persistence bridge completed." in text
    assert "Replay journal demo shortcut completed." in text
    assert "Replay journal folder shortcut completed." in text
    assert "Replay journal summary shortcut completed." in text
    assert "Replay journal all-in-one shortcut completed." in text
    assert "Replay journal guide completed." in text
    assert "Replay journal cleanup helper completed." in text
    assert "Replay journal index completed." in text
    assert "Replay journal index shortcut completed." in text
    assert "Replay journal runs viewer completed." in text
    assert "All-in-one replay journal shortcut uses pretty runs viewer completed." in text
    assert "Friendly replay journal summary viewer completed." in text
    assert "Paper MVP v0.1 scope freeze completed." in text
    assert "Strategy-to-paper bridge completed." in text
    assert "docs/DEFERRED_POLISH_BACKLOG.md" in text
    assert "docs/PAPER_MVP_RELEASE_CHECKLIST.md" in text
    assert "docs/PAPER_MVP_V0_1_SCOPE.md" in text
    assert "Replay journal all-in-one shortcut prints index completed." in text
    assert "Paper P&L is simulation only." in text
    assert "Real-money execution remains the final phase only." in text
    assert "hqe_paper_demo_report.bat" in text
    assert "hqe_paper_report_text.bat" in text
    assert "hqe_paper_replay_journal.bat" in text
    assert "hqe_paper_replay_journal_folder.bat" in text
    assert "hqe_paper_replay_journal_summary.bat" in text
    assert "hqe_paper_replay_journal_index.bat" in text
    assert "hqe_paper_replay_journal_runs.bat" in text
    assert "hqe_paper_replay_journal_all.bat" in text
    assert "docs/PAPER_TRADING_REPLAY_JOURNAL.md" in text
    assert "reports/paper_trading/report.txt" in text
    assert "Older roadmap sections below are retained as historical planning notes" in text

    # Historical roadmap anchors are intentionally retained for old docs guards.
    assert "648 tests passing" in text
    assert "Next Planned Phase: Paper Trading Design and Fake Execution Journal" in text
    assert "Completed Checkpoint" in text
