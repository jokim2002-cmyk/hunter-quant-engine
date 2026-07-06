"""Tests for the HQE paper operator guide."""

from pathlib import Path


GUIDE = Path("docs/PAPER_OPERATOR_GUIDE.md")


def test_paper_operator_guide_documents_safety_boundary():
    text = GUIDE.read_text(encoding="utf-8")

    assert "paper/simulation only" in text
    assert "It does not place broker orders." in text
    assert "It does not use live market data." in text
    assert "It does not use real money." in text
    assert "It does not claim profitability." in text


def test_paper_operator_guide_documents_operator_commands():
    text = GUIDE.read_text(encoding="utf-8")

    assert ".\\hqe_quick_check.bat" in text
    assert ".\\hqe_paper_mvp_operator_demo.bat" in text
    assert ".\\hqe_paper_replay_journal_all.bat" in text


def test_paper_operator_guide_documents_operator_demo_outputs():
    text = GUIDE.read_text(encoding="utf-8")

    assert "reports\\paper_trading\\operator_demo" in text
    assert "strategy-to-paper report text" in text
    assert "paper backtest evidence JSON" in text
    assert "evidence manifest JSON" in text


def test_paper_operator_guide_documents_evidence_gates():
    text = GUIDE.read_text(encoding="utf-8")

    assert "closed trades are below the configured minimum" in text
    assert "open positions remain above the configured maximum" in text
    assert "Passing evidence gates is not a profitability claim." in text
    assert "Live trading remains disabled by default." in text


def test_paper_operator_guide_documents_release_gate():
    text = GUIDE.read_text(encoding="utf-8")

    assert ".\\hqe_paper_mvp_release_check.bat" in text
    assert "This checks Paper MVP release readiness." in text
    assert "It does not create a git tag." in text
