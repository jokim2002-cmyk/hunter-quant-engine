from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_nifty_option_buy_assumptions_document_locks_first_module_direction():
    doc_path = PROJECT_ROOT / "docs" / "NIFTY_OPTION_BUY_ASSUMPTIONS.md"

    assert doc_path.exists()

    text = doc_path.read_text(encoding="utf-8")

    assert "dynamic NIFTY option-buy planning engine" in text
    assert "Bullish NIFTY signal -> Call / CE buy planning." in text
    assert "Bearish NIFTY signal -> Put / PE buy planning." in text
    assert "No option selling is allowed in the first module." in text
    assert "HQE must not be a fixed ATM option buyer." in text
    assert "1 lot = 65 quantity." in text
    assert "NIFTY spot/index data alone is not enough" in text
    assert "Current SMC mode benchmarks are underlying signal research only." in text

