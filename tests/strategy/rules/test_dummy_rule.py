"""
Tests for DummyRule.
"""

from src.strategy.rules.base_rule import BaseRule
from src.strategy.rules.dummy_rule import DummyRule


def test_dummy_rule_is_base_rule():
    rule = DummyRule()

    assert isinstance(rule, BaseRule)


def test_dummy_rule_returns_empty_tuple():
    rule = DummyRule()

    assert rule.evaluate(None) == ()
