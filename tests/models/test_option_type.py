"""
Option Type Tests
"""

from src.models.option_type import OptionType


def test_option_type_values_are_ce_and_pe():
    assert OptionType.CE.value == "CE"
    assert OptionType.PE.value == "PE"


def test_option_type_identifies_call_and_put():
    assert OptionType.CE.is_call is True
    assert OptionType.CE.is_put is False

    assert OptionType.PE.is_call is False
    assert OptionType.PE.is_put is True
