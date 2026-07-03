from src.strategy.signal_type import SignalType


def test_signal_type_values():
    assert SignalType.LONG.value == "long"
    assert SignalType.SHORT.value == "short"
    assert SignalType.NEUTRAL.value == "neutral"


def test_signal_type_members():
    assert len(SignalType) == 3
