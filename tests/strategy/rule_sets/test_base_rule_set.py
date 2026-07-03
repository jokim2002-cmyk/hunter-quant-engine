"""
Base Rule Set Tests
"""

import pytest

from src.strategy.rule_sets.base_rule_set import BaseRuleSet
from src.strategy.strategy_context import StrategyContext


class DummyRuleSet(BaseRuleSet[object]):
    def evaluate(
        self,
        context: StrategyContext,
    ) -> object:
        return object()


def test_base_rule_set_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseRuleSet()


def test_dummy_rule_set_implements_base_rule_set_contract():
    rule_set = DummyRuleSet()

    assert isinstance(rule_set, BaseRuleSet)
    assert rule_set.evaluate(None) is not None
