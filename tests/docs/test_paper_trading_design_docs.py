from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_paper_trading_design_doc_exists():
    assert (PROJECT_ROOT / "docs" / "PAPER_TRADING_DESIGN.md").exists()


def test_paper_trading_design_doc_content():
    text = (PROJECT_ROOT / "docs" / "PAPER_TRADING_DESIGN.md").read_text(encoding="utf-8")

    assert "Paper Trading Design" in text
    assert "design only" in text
    assert "no broker" in text.lower()
    assert "no FYERS" in text or "No broker or FYERS" in text
    assert "no real orders" in text.lower()
    assert "no profitability claim" in text.lower()
    assert "validated" in text and "replayed" in text
    assert "offline" in text
    assert "option-buy trade plan" in text.lower() or "OptionBuyTradePlan" in text
    assert "PaperOrderJournal" in text
    assert "PaperPositionState" in text
    assert "data/paper_trading/" in text
    assert "max_trades_per_day" in text or "max trades per day" in text
    assert "max_daily_loss" in text or "max daily loss" in text
    assert "max_position_size" in text or "max position size" in text
    assert "cooldown" in text
    assert "kill_switch" in text or "kill switch" in text
    assert "real-money execution remains the last phase" in text.lower()
    assert "no option selling" in text.lower()
    assert "no short ce" in text.lower() or "No short CE" in text


def test_roadmap_documents_paper_trading_design_next_phase():
    text = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8")

    assert "Next Planned Phase: Paper Trading Design and Fake Execution Journal" in text
    assert "Design first" in text
    assert "No paper trading engine is implemented yet" in text
    assert "Offline/replayed data first" in text
    assert "max trades per day" in text
    assert "max daily loss" in text
    assert "max position size" in text
    assert "cooldown" in text
    assert "kill switch" in text
    assert "Broker/live execution remains a future phase" in text
    assert "Real-money execution remains the last phase" in text
    assert "docs/PAPER_TRADING_DESIGN.md" in text
