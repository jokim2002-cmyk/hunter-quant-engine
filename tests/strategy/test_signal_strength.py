from src.strategy.signal_strength import SignalStrength


def test_signal_strength_values():
    assert SignalStrength.WEAK.value == "weak"
    assert SignalStrength.MEDIUM.value == "medium"
    assert SignalStrength.STRONG.value == "strong"


def test_signal_strength_members():
    assert len(SignalStrength) == 3
