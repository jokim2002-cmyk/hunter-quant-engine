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


def test_paper_trading_design_doc_documents_implemented_skeleton():
    text = (PROJECT_ROOT / "docs" / "PAPER_TRADING_DESIGN.md").read_text(encoding="utf-8")

    assert "Implemented Skeleton" in text
    assert "PaperOrderRequest" in text
    assert "PaperOrderRecord" in text
    assert "Fake/local records only" in text
    assert "No real orders are placed" in text
    assert "No broker or FYERS" in text
    assert "Not a profitability claim" in text
    assert "src/paper_trading/paper_order_journal.py" in text
    assert "tests/paper_trading/test_paper_order_journal.py" in text


def test_paper_trading_design_doc_documents_position_state_skeleton():
    text = (PROJECT_ROOT / "docs" / "PAPER_TRADING_DESIGN.md").read_text(encoding="utf-8")

    assert "Paper Position State Skeleton" in text
    assert "PaperPosition" in text
    assert "PaperPositionState" in text
    assert "Local fake paper position tracking only" in text
    assert "PaperOrderRecord" in text
    assert "No broker or FYERS" in text
    assert "No real orders" in text
    assert "Not a profitability claim" in text
    assert "src/paper_trading/paper_position_state.py" in text
    assert "tests/paper_trading/test_paper_position_state.py" in text


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


def test_paper_trading_design_docs_cover_session_skeleton():
    text = Path("docs/PAPER_TRADING_DESIGN.md").read_text(encoding="utf-8")

    assert "Paper trading session skeleton" in text
    assert "PaperTradingSession" in text
    assert "PaperOrderJournal" in text
    assert "PaperPositionState" in text
    assert "src/paper_trading/paper_trading_session.py" in text
    assert "tests/paper_trading/test_paper_trading_session.py" in text
    assert "fake/local coordinator" in text
    assert "does not use FYERS" in text
    assert "does not use live market data" in text
    assert "does not place real orders" in text
    assert "not a profitability claim" in text


def test_paper_trading_design_doc_documents_option_buy_plan_adapter():
    text = (PROJECT_ROOT / "docs" / "PAPER_TRADING_DESIGN.md").read_text(encoding="utf-8")

    assert "Option-buy Plan to Paper Order Adapter" in text
    assert "OptionBuyTradePlan" in text
    assert "PaperOrderRequest" in text
    assert "PaperTradingSession" in text
    assert "fake/local only" in text
    assert "No broker/FYERS" in text
    assert "No real orders" in text
    assert "Not a profitability claim" in text
    assert "src/paper_trading/option_buy_plan_to_paper_order.py" in text
    assert "tests/paper_trading/test_option_buy_plan_to_paper_order.py" in text


def test_paper_trading_design_docs_cover_demo_script():
    from pathlib import Path

    text = Path("docs/PAPER_TRADING_DESIGN.md").read_text(encoding="utf-8")

    assert "Paper Trading Demo Script" in text
    assert "examples/run_paper_trading_demo.py" in text
    assert "synthetic OptionBuyTradePlan" in text
    assert "PaperOrderRequest" in text
    assert "PaperTradingSession" in text
    assert "PaperOrderRecord" in text
    assert "PaperPosition" in text
    assert "fake/local workflow" in text
    assert "does not use FYERS" in text
    assert "does not use live/real market data" in text
    assert "does not place real orders" in text
    assert "not a profitability claim" in text
    assert "tests/examples/test_run_paper_trading_demo.py" in text
