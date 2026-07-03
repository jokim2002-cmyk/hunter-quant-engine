"""
Base Rule Tests
"""

import pytest

from src.strategy.rules.base_rule import BaseRule
from src.strategy.strategy_context import StrategyContext


class DummyRule(BaseRule[object]):
    def evaluate(
        self,
        context: StrategyContext,
    ) -> tuple[object, ...]:
        return ()


def test_base_rule_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseRule()


def test_dummy_rule_implements_base_rule_contract():
    rule = DummyRule()

    assert isinstance(rule, BaseRule)

    assert rule.evaluate(None) == ()
