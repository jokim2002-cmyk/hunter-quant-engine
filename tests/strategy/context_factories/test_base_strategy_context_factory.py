"""
Base Strategy Context Factory Tests
"""

import pytest

from src.strategy.context_factories.base_strategy_context_factory import (
    BaseStrategyContextFactory,
)


def test_base_strategy_context_factory_cannot_be_instantiated():
    """
    Should not allow direct instantiation of the abstract factory contract.
    """
    with pytest.raises(TypeError):
        BaseStrategyContextFactory()
