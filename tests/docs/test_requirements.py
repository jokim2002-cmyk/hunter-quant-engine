"""
Tests for project requirements.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_requirements_include_core_runtime_and_test_dependencies():
    requirements_path = PROJECT_ROOT / "requirements.txt"

    assert requirements_path.exists()

    requirements = set(
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )

    assert "pandas" in requirements
    assert "numpy" in requirements
    assert "matplotlib" in requirements
    assert "python-dotenv" in requirements
    assert "pydantic" in requirements
    assert "pytest" in requirements
    assert "fyers-apiv3" in requirements
