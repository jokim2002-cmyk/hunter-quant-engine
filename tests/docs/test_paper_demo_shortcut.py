"""Tests for the paper demo Windows shortcut."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_hqe_paper_demo_bat_runs_safe_paper_cli_module():
    shortcut = PROJECT_ROOT / "hqe_paper_demo.bat"

    assert shortcut.exists()

    text = shortcut.read_text(encoding="utf-8").lower()

    assert ".\\.venv\\scripts\\python.exe -m src.paper_trading.paper_trading_demo_cli" in text
    assert "fyers" not in text
    assert "place" + "_order" not in text
    assert "send" + "_order" not in text
    assert "execute" + "_order" not in text
