from src.models.equal_level_type import EqualLevelType


def test_equal_level_type_high():
    level_type = EqualLevelType.HIGH

    assert level_type.is_high() is True
    assert level_type.is_low() is False


def test_equal_level_type_low():
    level_type = EqualLevelType.LOW

    assert level_type.is_low() is True
    assert level_type.is_high() is False


def test_equal_level_type_values():
    assert EqualLevelType.HIGH.value == "high"
    assert EqualLevelType.LOW.value == "low"