"""Tests for Live-Readiness Scaffold v0.2 release notes."""

from pathlib import Path


RELEASE_NOTES = Path("docs/LIVE_READINESS_SCAFFOLD_V0_2_RELEASE_NOTES.md")


def test_live_readiness_scaffold_release_notes_document_safety_boundary():
    text = RELEASE_NOTES.read_text(encoding="utf-8")

    assert "This release is not live trading." in text
    assert "It does not enable real money." in text
    assert "It does not enable broker execution." in text
    assert "It does not enable broker submission." in text
    assert "It does not enable live market data." in text
    assert "It does not enable real orders." in text
    assert "It does not claim profitability." in text


def test_live_readiness_scaffold_release_notes_document_release_tag():
    text = RELEASE_NOTES.read_text(encoding="utf-8")

    assert "v0.2-live-readiness-scaffold" in text


def test_live_readiness_scaffold_release_notes_document_included_modules():
    text = RELEASE_NOTES.read_text(encoding="utf-8")

    assert "Paper evidence aggregate runner." in text
    assert "Live-readiness gate scaffold." in text
    assert "Disabled live safety lock scaffold." in text
    assert "Full live-readiness preflight." in text
    assert "Deny-only live execution firewall." in text
    assert "Firewall integration into the live-readiness preflight." in text


def test_live_readiness_scaffold_release_notes_document_operator_commands():
    text = RELEASE_NOTES.read_text(encoding="utf-8")

    assert ".\\hqe_quick_check.bat" in text
    assert ".\\hqe_live_readiness_preflight.bat" in text
    assert ".\\hqe_live_execution_firewall_check.bat" in text
    assert ".\\hqe_live_safety_lock_check.bat" in text


def test_live_readiness_scaffold_release_notes_do_not_claim_profitability():
    text = RELEASE_NOTES.read_text(encoding="utf-8")

    assert "This release does not prove profitability." in text
    assert "Profitability must be proven separately" in text
    assert "safe local live-readiness scaffolding is working" in text
