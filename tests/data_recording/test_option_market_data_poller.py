from datetime import datetime
from pathlib import Path

import pytest

from src.data_recording.option_market_data_poll_result import (
    OptionMarketDataPollResult,
)
from src.data_recording.option_market_data_poller import OptionMarketDataPoller
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType


class FakeOptionMarketDataSource:
    def __init__(self, snapshot=None, candles_by_symbol=None):
        self.snapshot = snapshot
        self.candles_by_symbol = candles_by_symbol or {}
        self.snapshot_calls = 0
        self.premium_calls = []

    def get_option_chain_snapshot(self):
        self.snapshot_calls += 1
        return self.snapshot

    def get_option_premium_candles(self, symbols):
        self.premium_calls.append(tuple(symbols))
        return self.candles_by_symbol


def _candle(timestamp, close=100.0):
    return OptionPremiumCandle(
        timestamp=timestamp,
        open=close,
        high=close + 10,
        low=close - 10,
        close=close,
        volume=1,
    )


def _snapshot():
    contract = OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=datetime(2026, 7, 9).date(),
        strike_price=24200,
        option_type=OptionType.CE,
        lot_size=65,
        symbol="NIFTY26JUL24200CE",
    )
    entry = OptionChainEntry(
        contract=contract,
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=100.0,
        volume=1,
        open_interest=1,
    )
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.0,
        timestamp=datetime(2026, 7, 6, 9, 15),
        entries=(entry,),
    )


def test_default_empty_result():
    result = OptionMarketDataPollResult()

    assert result.snapshot is None
    assert result.premium_candles_by_symbol == {}
    assert result.has_snapshot is False
    assert result.premium_symbols_count == 0
    assert result.premium_candles_count == 0
    assert result.has_premium_candles is False
    assert result.has_data is False


def test_tuple_normalization():
    result = OptionMarketDataPollResult(
        premium_candles_by_symbol={"NIFTY26JUL24200CE": [_candle(datetime(2026, 7, 6, 9, 20))]}
    )

    assert isinstance(result.premium_candles_by_symbol["NIFTY26JUL24200CE"], tuple)


def test_blank_symbol_reject():
    with pytest.raises(ValueError, match="option premium candle symbol is required"):
        OptionMarketDataPollResult(
            premium_candles_by_symbol={"": (_candle(datetime(2026, 7, 6, 9, 20)),)}
        )


def test_empty_candle_sequence_reject():
    with pytest.raises(
        ValueError,
        match="option premium candles are required for symbol: NIFTY26JUL24200CE",
    ):
        OptionMarketDataPollResult(
            premium_candles_by_symbol={"NIFTY26JUL24200CE": ()}
        )


def test_all_properties():
    result = OptionMarketDataPollResult(
        snapshot=_snapshot(),
        premium_candles_by_symbol={
            "NIFTY26JUL24200CE": (
                _candle(datetime(2026, 7, 6, 9, 20)),
                _candle(datetime(2026, 7, 6, 9, 25)),
            )
        },
    )

    assert result.has_snapshot is True
    assert result.premium_symbols_count == 1
    assert result.premium_candles_count == 2
    assert result.has_premium_candles is True
    assert result.has_data is True


def test_poll_snapshot():
    data_source = FakeOptionMarketDataSource(snapshot=_snapshot())
    poller = OptionMarketDataPoller(data_source)

    result = poller.poll_snapshot()

    assert result.snapshot == data_source.snapshot
    assert data_source.snapshot_calls == 1


def test_poll_premium_candles_reject_empty_symbols():
    poller = OptionMarketDataPoller(FakeOptionMarketDataSource())

    with pytest.raises(ValueError, match="option premium candle symbols are required"):
        poller.poll_premium_candles(())


def test_poll_premium_candles_returns_candles():
    candles = (_candle(datetime(2026, 7, 6, 9, 20)),)
    data_source = FakeOptionMarketDataSource(
        candles_by_symbol={"NIFTY26JUL24200CE": candles}
    )
    poller = OptionMarketDataPoller(data_source)

    result = poller.poll_premium_candles(["NIFTY26JUL24200CE"])

    assert result.premium_candles_by_symbol["NIFTY26JUL24200CE"] == candles
    assert data_source.premium_calls == [("NIFTY26JUL24200CE",)]


def test_poll_combines_snapshot_and_candles():
    data_source = FakeOptionMarketDataSource(
        snapshot=_snapshot(),
        candles_by_symbol={"NIFTY26JUL24200CE": (_candle(datetime(2026, 7, 6, 9, 20)),)},
    )
    poller = OptionMarketDataPoller(data_source)

    result = poller.poll(premium_symbols=["NIFTY26JUL24200CE"])

    assert result.has_snapshot is True
    assert result.has_premium_candles is True
    assert data_source.snapshot_calls == 1
    assert data_source.premium_calls == [("NIFTY26JUL24200CE",)]


def test_poll_can_return_empty_result():
    poller = OptionMarketDataPoller(FakeOptionMarketDataSource())

    result = poller.poll(include_snapshot=False)

    assert result.has_data is False
    assert result.snapshot is None
    assert result.premium_candles_by_symbol == {}


def test_no_fyers_specific_imports():
    import src.data_recording.option_market_data_poller as module

    source = Path(module.__file__).read_text(encoding="utf-8").lower()

    assert "fyers" not in source
