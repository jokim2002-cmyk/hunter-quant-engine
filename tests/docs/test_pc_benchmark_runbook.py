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
    assert "Do not run full real-data strategy mode benchmarks on the laptop." in text
    assert "hqe_benchmark_modes.bat" in text
    assert "scripts\\benchmark_strategy_modes.py" in text
    assert "fyers_nifty_5m_mode_benchmark_report.txt" in text
    assert "fyers_nifty_5m_mode_benchmark_summary.csv" in text
    assert "No fake profit claims." in text
