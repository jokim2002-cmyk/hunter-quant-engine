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
    assert "--input" in text
    assert "data\\raw\\fyers_nifty_5min.csv" in text
    assert "fyers_nifty_5m_mode_benchmark_report.txt" in text
    assert "fyers_nifty_5m_mode_benchmark_summary.csv" in text


def test_hqe_run_experiments_shortcut_exists_and_runs_execute_mode():
    shortcut_path = PROJECT_ROOT / "hqe_run_experiments.bat"

    assert shortcut_path.exists()

    text = shortcut_path.read_text(encoding="utf-8")

    assert "HQE STRATEGY EXPERIMENT RUNNER" in text
    assert "PC only" in text
    assert "scripts\\run_strategy_experiments.py" in text
    assert "--execute" in text
    assert "--input" in text
    assert "data\\raw\\fyers_nifty_5min.csv" in text
    assert "strategy_experiment_report.txt" in text
    assert "strategy_experiment_summary.csv" in text
    assert "data\\processed\\experiments\\" in text
