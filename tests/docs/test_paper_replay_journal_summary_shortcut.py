"""Tests for the paper replay journal summary shortcut."""

from pathlib import Path


def test_paper_replay_journal_summary_shortcut_uses_pretty_summary_cli():
    text = Path("hqe_paper_replay_journal_summary.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "src.paper_trading.paper_trading_replay_journal_summary_cli" in text
    assert r".venv\scripts\python.exe" in text
    assert "type " not in text


def test_paper_replay_journal_summary_shortcut_is_safe_local_only():
    text = Path("hqe_paper_replay_journal_summary.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "local/generated fake paper replay journal summary" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text

    assert "import " + "fy" + "ers" not in text
    assert "from " + "fy" + "ers" not in text
    assert "place" + "_order" not in text
    assert "send" + "_order" not in text
    assert "execute" + "_order" not in text
