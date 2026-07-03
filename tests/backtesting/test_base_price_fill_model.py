"""
Base Price Fill Model Tests
"""

import pytest

from src.backtesting.base_price_fill_model import BasePriceFillModel
from src.backtesting.price_fill_result import PriceFillResult


class DummyPriceFillModel(BasePriceFillModel):
    def evaluate(
        self,
        trade_plan,
        candle,
    ) -> PriceFillResult:
        return PriceFillResult(
            filled=False,
            fill_price=None,
            reason=None,
        )


def test_base_price_fill_model_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BasePriceFillModel()


def test_dummy_price_fill_model_implements_contract():
    model = DummyPriceFillModel()

    assert isinstance(model, BasePriceFillModel)

    result = model.evaluate(None, None)

    assert result == PriceFillResult(
        filled=False,
        fill_price=None,
        reason=None,
    )
