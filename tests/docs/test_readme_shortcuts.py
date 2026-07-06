"""Tests for the root shortcut quick-start card."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_readme_shortcuts_documents_safe_daily_commands():
    path = PROJECT_ROOT / "README_SHORTCUTS.md"

    assert path.exists()

    text = path.read_text(encoding="utf-8")
    lower_text = text.lower()

    assert ".\\hqe_paper_demo.bat" in text
    assert ".\\hqe_paper_report.bat" in text
    assert ".\\hqe_paper_demo_report.bat" in text
    assert ".\\.venv\\Scripts\\python.exe -m pytest" in text
    assert "git status --short" in text
    assert "Paper P&L is simulation only." in text
    assert "No real orders are placed." in text
    assert "not a profitability claim" in lower_text


def test_readme_shortcuts_stays_paper_safe():
    text = (PROJECT_ROOT / "README_SHORTCUTS.md").read_text(
        encoding="utf-8"
    ).lower()

    assert "fyers" in text
    assert "no broker/fyers" in text
    assert "place" + "_order" not in text
    assert "send" + "_order" not in text
    assert "execute" + "_order" not in text
