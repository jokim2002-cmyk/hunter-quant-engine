"""Docs tests for the broker-agnostic option market data recorder."""

from pathlib import Path


def test_option_market_data_recording_docs_exist():
    doc_path = Path("docs/OPTION_MARKET_DATA_RECORDING.md")

    assert doc_path.exists()


def test_option_market_data_recording_docs_cover_core_guidance():
    contents = Path("docs/OPTION_MARKET_DATA_RECORDING.md").read_text(encoding="utf-8")

    assert "broker-agnostic" in contents.lower()
    assert "does not place orders" in contents.lower()
    assert "not a profitability claim" in contents.lower()
    assert "option chain snapshots" in contents.lower()
    assert "option premium candles" in contents.lower()
    assert "CsvOptionMarketDataRecorder" in contents
    assert "offline option-buy backtest cli" in contents.lower()


def test_option_market_data_recording_docs_cover_polling_recorder():
    contents = Path("docs/OPTION_MARKET_DATA_RECORDING.md").read_text(encoding="utf-8")

    assert "OptionMarketDataSource" in contents
    assert "OptionMarketDataPoller" in contents
    assert "OptionMarketDataPollingRecorder" in contents
    assert "CsvOptionMarketDataRecorder" in contents
    assert "poll-and-record workflow" in contents.lower()
    assert "does not place orders" in contents.lower()
    assert "not a profitability claim" in contents.lower()
    assert "data/recorded/" in contents


def test_gitignore_ignores_recording_data_directories():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "data/recorded/" in gitignore
    assert "data/live_recording/" in gitignore
    assert "data/paper_trading/" in gitignore
