"""Tests for the paper report quick-open shortcut."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_hqe_paper_report_bat_opens_generated_report_only():
    shortcut = PROJECT_ROOT / "hqe_paper_report.bat"

    assert shortcut.exists()

    text = shortcut.read_text(encoding="utf-8").lower()

    assert "reports\\paper_trading\\report.txt" in text
    assert "hqe_paper_demo.bat" in text
    assert "start" in text
    assert "fyers" not in text
    assert "place" + "_order" not in text
    assert "send" + "_order" not in text
    assert "execute" + "_order" not in text
