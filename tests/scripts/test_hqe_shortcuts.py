"""
Tests for HQE workflow shortcut batch files.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_hqe_benchmark_modes_shortcut_exists_and_runs_mode_benchmark():
    shortcut_path = PROJECT_ROOT / "hqe_benchmark_modes.bat"

    assert shortcut_path.exists()

    text = shortcut_path.read_text(encoding="utf-8")

    assert "HQE STRATEGY MODE BENCHMARK" in text
    assert "PC only" in text
    assert "scripts\\benchmark_strategy_modes.py" in text
    assert "--input \"data\\raw\\fyers_nifty_5min.csv\"" in text
    assert "fyers_nifty_5m_mode_benchmark_report.txt" in text
    assert "fyers_nifty_5m_mode_benchmark_summary.csv" in text
