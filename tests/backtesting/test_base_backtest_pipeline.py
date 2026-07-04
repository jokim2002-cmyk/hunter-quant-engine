"""
Base Backtest Pipeline Tests
"""

import pytest

from src.backtesting.base_backtest_pipeline import BaseBacktestPipeline


def test_base_backtest_pipeline_cannot_be_instantiated():
    """
    Should not allow direct instantiation of the abstract pipeline contract.
    """
    with pytest.raises(TypeError):
        BaseBacktestPipeline()
