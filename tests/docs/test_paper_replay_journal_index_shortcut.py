"""Tests for the paper replay journal index shortcut."""

from pathlib import Path


def test_paper_replay_journal_index_shortcut_prints_index_json():
    text = Path("hqe_paper_replay_journal_index.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert r"reports\paper_trading\journal\index.json" in text
    assert "hqe_paper_replay_journal.bat" in text
    assert 'type "%index_json%"' in text
    assert "paper pnl is simulation only" in text


def test_paper_replay_journal_index_shortcut_is_safe_local_only():
    text = Path("hqe_paper_replay_journal_index.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
    assert "local/generated fake paper replay journal index" in text

    assert "import " + "fy" + "ers" not in text
    assert "from " + "fy" + "ers" not in text
    assert "place" + "_order" not in text
    assert "send" + "_order" not in text
    assert "execute" + "_order" not in text
