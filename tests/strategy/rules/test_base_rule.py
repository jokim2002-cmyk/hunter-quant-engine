"""
Base Rule Tests
"""

import pytest

from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class DummyRule(BaseRule):
    def evaluate(self, context: StrategyContext) -> bool:
        return True


def test_base_rule_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseRule()


def test_dummy_rule_implements_base_rule_contract():
    rule = DummyRule()

    assert isinstance(rule, BaseRule)
