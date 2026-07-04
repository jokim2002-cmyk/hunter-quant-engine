"""
Tests for laptop-to-PC handoff documentation.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_laptop_to_pc_handoff_documents_latest_sync_steps():
    handoff_path = PROJECT_ROOT / "docs" / "LAPTOP_TO_PC_HANDOFF.md"

    assert handoff_path.exists()

    text = handoff_path.read_text(encoding="utf-8")

    assert "Laptop to PC Handoff" in text
    assert "0b2eedf Update project requirements" in text
    assert "620 passed" in text
    assert "git pull --ff-only" in text
    assert "hqe_benchmark_modes.bat" in text
    assert "hqe_run_experiments.bat" in text
    assert "Do not run these on laptop" in text
    assert "Do Not Commit Generated Outputs" in text
    assert "No fake profit claims." in text
