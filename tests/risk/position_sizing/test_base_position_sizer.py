"""
Base Position Sizer Tests
"""

import pytest

from src.risk.position_sizing.base_position_sizer import BasePositionSizer
from src.risk.risk_profile import RiskProfile


class DummyPositionSizer(BasePositionSizer):
    def calculate(
        self,
        risk_profile: RiskProfile,
        entry_price: float,
        stop_loss: float,
    ) -> float:
        return 1.0


def test_base_position_sizer_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BasePositionSizer()


def test_dummy_position_sizer_implements_base_position_sizer_contract():
    sizer = DummyPositionSizer()

    assert isinstance(sizer, BasePositionSizer)
    assert sizer.calculate(None, 100.0, 95.0) == 1.0
