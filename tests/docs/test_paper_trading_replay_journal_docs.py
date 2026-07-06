"""Tests for the paper trading replay journal guide."""

from pathlib import Path


DOC_PATH = Path("docs/PAPER_TRADING_REPLAY_JOURNAL.md")


def test_replay_journal_docs_exist_and_cover_main_shortcuts():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "Paper Trading Replay Journal" in text
    assert ".\\hqe_paper_replay_journal_all.bat" in text
    assert ".\\hqe_paper_replay_journal.bat" in text
    assert ".\\hqe_paper_replay_journal_summary.bat" in text
    assert ".\\hqe_paper_replay_journal_folder.bat" in text


def test_replay_journal_docs_cover_generated_local_files():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "reports/paper_trading/journal/demo-replay-journal/" in text
    assert "metadata.json" in text
    assert "summary.json" in text
    assert "orders.json" in text
    assert "open_positions.json" in text
    assert "exit_records.json" in text
    assert "manifest.json" in text
    assert "index.json" in text
    assert "The index file tracks available replay journal runs." in text
    assert "local/generated outputs and must stay ignored by Git" in text


def test_replay_journal_docs_cover_python_entry_points():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "src.paper_trading.paper_trading_replay_journal_demo_cli" in text
    assert "paper_trading_replay_loop.py" in text
    assert "paper_trading_journal_store.py" in text
    assert "paper_trading_replay_journal.py" in text
    assert "paper_trading_replay_journal_demo_cli.py" in text


def test_replay_journal_docs_keep_safety_language():
    text = DOC_PATH.read_text(encoding="utf-8").lower()

    assert "does not connect to a broker" in text
    assert "does not use live market data" in text
    assert "does not place real orders" in text
    assert "not a profitability claim" in text
    assert "paper p&l is simulation only" in text
    assert "estimated costs must be included in net p&l only" in text
    assert "gross p&l must exclude costs" in text
    assert "real-money execution remains the final phase only" in text
