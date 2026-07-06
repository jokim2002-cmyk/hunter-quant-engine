"""Tests for the paper replay journal folder shortcut."""

from pathlib import Path


def test_paper_replay_journal_folder_shortcut_exists_and_opens_demo_folder():
    text = Path("hqe_paper_replay_journal_folder.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "reports\\paper_trading\\journal\\demo-replay-journal" in text
    assert "hqe_paper_replay_journal.bat" in text
    assert 'start "" "%journal_dir%"' in text
    assert "mkdir" in text


def test_paper_replay_journal_folder_shortcut_is_safe_local_only():
    text = Path("hqe_paper_replay_journal_folder.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
    assert "local/generated fake paper replay journal folder" in text

    assert "import " + "fy" + "ers" not in text
    assert "from " + "fy" + "ers" not in text
    assert "place" + "_order" not in text
    assert "send" + "_order" not in text
    assert "execute" + "_order" not in text
