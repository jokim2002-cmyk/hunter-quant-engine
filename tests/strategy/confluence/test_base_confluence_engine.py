"""
Base Confluence Engine Tests
"""

from datetime import datetime

import pytest

from src.strategy.confluence.base_confluence_engine import BaseConfluenceEngine
from src.strategy.signal_type import SignalType


def test_base_confluence_engine_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseConfluenceEngine()


def test_concrete_confluence_engine_can_implement_contract():
    class ConcreteConfluenceEngine(BaseConfluenceEngine[object, object]):
        def generate(
            self,
            result: object,
            direction: SignalType,
            created_at: datetime,
        ) -> tuple[object, ...]:
            return (result,)

    result = object()
    created_at = datetime(2026, 1, 1, 9, 0)

    generated = ConcreteConfluenceEngine().generate(
        result=result,
        direction=SignalType.LONG,
        created_at=created_at,
    )

    assert generated == (result,)
