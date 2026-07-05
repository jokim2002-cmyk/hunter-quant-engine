"""
Option Action Tests
"""

from src.models.option_action import OptionAction


def test_option_action_allows_buy_only_for_first_module():
    assert tuple(OptionAction) == (OptionAction.BUY,)
    assert OptionAction.BUY.value == "BUY"
