from src.models.fair_value_gap_type import FairValueGapType


def test_bullish_value():
    assert FairValueGapType.BULLISH.value == "bullish"


def test_bearish_value():
    assert FairValueGapType.BEARISH.value == "bearish"


def test_enum_has_two_members():
    assert len(FairValueGapType) == 2


def test_enum_member_names():
    assert FairValueGapType.BULLISH.name == "BULLISH"
    assert FairValueGapType.BEARISH.name == "BEARISH"