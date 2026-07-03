from src.models.liquidity_sweep_type import LiquiditySweepType


def test_high_value():
    assert LiquiditySweepType.HIGH.value == "high"


def test_low_value():
    assert LiquiditySweepType.LOW.value == "low"


def test_enum_has_two_members():
    assert len(LiquiditySweepType) == 2


def test_enum_member_names():
    assert LiquiditySweepType.HIGH.name == "HIGH"
    assert LiquiditySweepType.LOW.name == "LOW"