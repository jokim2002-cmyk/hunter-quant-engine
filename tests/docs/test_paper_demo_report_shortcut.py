"""Tests for the combined paper demo and report shortcut."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_hqe_paper_demo_report_bat_runs_demo_then_report_shortcut():
    shortcut = PROJECT_ROOT / "hqe_paper_demo_report.bat"

    assert shortcut.exists()

    text = shortcut.read_text(encoding="utf-8").lower()

    assert "call \".\\hqe_paper_demo.bat\"" in text
    assert "call \".\\hqe_paper_report.bat\"" in text
    assert "if errorlevel 1 exit /b %errorlevel%" in text
    assert "fyers" not in text
    assert "place" + "_order" not in text
    assert "send" + "_order" not in text
    assert "execute" + "_order" not in text
