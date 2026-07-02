def test_candle_body_size(bullish_candle):
    assert bullish_candle.body_size == 8.0


def test_candle_range_size(bullish_candle):
    assert bullish_candle.range_size == 15.0


def test_candle_is_bullish(bullish_candle):
    assert bullish_candle.is_bullish is True
    assert bullish_candle.is_bearish is False


def test_candle_is_bearish(bearish_candle):
    assert bearish_candle.is_bearish is True
    assert bearish_candle.is_bullish is False


def test_doji_candle_is_neither_bullish_nor_bearish(doji_candle):
    assert doji_candle.is_bullish is False
    assert doji_candle.is_bearish is False