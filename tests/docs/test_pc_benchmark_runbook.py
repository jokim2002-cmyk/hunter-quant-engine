"""
Tests for project documentation.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_pc_benchmark_runbook_exists_and_documents_safe_workflow():
    runbook_path = PROJECT_ROOT / "docs" / "PC_BENCHMARK_RUNBOOK.md"

    assert runbook_path.exists()

    text = runbook_path.read_text(encoding="utf-8")

    assert "PC Benchmark Runbook" in text
    assert "Do not run full real-data strategy mode benchmarks or experiment execution on the laptop." in text
    assert "hqe_benchmark_modes.bat" in text
    assert "hqe_run_experiments.bat" in text
    assert "scripts\\benchmark_strategy_modes.py" in text
    assert "scripts\\run_strategy_experiments.py" in text
    assert "--execute" in text
    assert "fyers_nifty_5m_mode_benchmark_report.txt" in text
    assert "fyers_nifty_5m_mode_benchmark_summary.csv" in text
    assert "strategy_experiment_report.txt" in text
    assert "strategy_experiment_summary.csv" in text
    assert "data/processed/experiments/" in text
    assert "best/worst experiment rankings" in text
    assert "No fake profit claims." in text
