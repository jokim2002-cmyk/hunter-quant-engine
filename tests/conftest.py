from datetime import datetime

import pytest

from src.models.candle import Candle


@pytest.fixture
def bullish_candle():
    return Candle(
        datetime=datetime(2026, 1, 1, 9, 15),
        open=100.0,
        high=110.0,
        low=95.0,
        close=108.0,
        volume=1000.0,
    )


@pytest.fixture
def bearish_candle():
    return Candle(
        datetime=datetime(2026, 1, 1, 9, 15),
        open=108.0,
        high=110.0,
        low=95.0,
        close=100.0,
        volume=1000.0,
    )


@pytest.fixture
def doji_candle():
    return Candle(
        datetime=datetime(2026, 1, 1, 9, 15),
        open=100.0,
        high=110.0,
        low=95.0,
        close=100.0,
        volume=1000.0,
    )