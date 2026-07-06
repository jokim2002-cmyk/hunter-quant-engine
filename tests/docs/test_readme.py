"""
Tests for README documentation.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_readme_documents_current_hqe_workflow():
    readme_path = PROJECT_ROOT / "README.md"

    assert readme_path.exists()

    text = readme_path.read_text(encoding="utf-8")

    assert "Hunter Quant Engine (HQE)" in text
    assert "1337 tests passing" in text
    assert "Strict/Balanced/Relaxed strategy modes" in text
    assert "Strategy mode benchmark runner" in text
    assert "Strategy experiment dry-run planner" in text
    assert "Do not run full real-data strategy mode benchmarks or experiment execution on the laptop." in text
    assert "hqe_benchmark_modes.bat" in text
    assert "hqe_run_experiments.bat" in text
    assert "No fake profit claims." in text
    assert "docs/PC_BENCHMARK_RUNBOOK.md" in text
    assert "Run the safe local paper trading demo CLI:" in text
    assert ".\\.venv\\Scripts\\python.exe -m src.paper_trading.paper_trading_demo_cli" in text
    assert "Run the safe local paper trading demo example wrapper:" in text
    assert ".\\.venv\\Scripts\\python.exe examples\\run_paper_trading_demo.py" in text
    assert "Run the safe local paper trading demo shortcut:" in text
    assert ".\\hqe_paper_demo.bat" in text
    assert "Open the latest generated paper trading report:" in text
    assert ".\\hqe_paper_report.bat" in text


def test_readme_no_longer_contains_old_architecture_typos():
    text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "vDetection" not in text
    assert "Mmutable" not in text
    assert "Backtesting Engine will consume" not in text
