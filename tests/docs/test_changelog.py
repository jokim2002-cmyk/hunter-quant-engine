"""
Tests for CHANGELOG documentation.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_changelog_documents_current_project_status():
    changelog_path = PROJECT_ROOT / "CHANGELOG.md"

    assert changelog_path.exists()

    text = changelog_path.read_text(encoding="utf-8")

    assert "Changelog" in text
    assert "No fake profit claims" in text
    assert "Strict, balanced, and relaxed strategy modes." in text
    assert "Strategy mode benchmark runner." in text
    assert "Strategy experiment dry-run runner." in text
    assert "PC-only strategy experiment shortcut." in text
    assert "Full real-data strategy mode benchmark marked as PC-only." in text
    assert "618 tests passing." in text
    assert "first honest baseline" in text
