"""
Base Trade Plan Deduplicator Tests
"""

import pytest

from src.backtesting.base_trade_plan_deduplicator import (
    BaseTradePlanDeduplicator,
)


def test_base_trade_plan_deduplicator_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseTradePlanDeduplicator()


def test_base_trade_plan_deduplicator_requires_deduplicate_implementation():
    class IncompleteDeduplicator(BaseTradePlanDeduplicator):
        pass

    with pytest.raises(TypeError):
        IncompleteDeduplicator()
