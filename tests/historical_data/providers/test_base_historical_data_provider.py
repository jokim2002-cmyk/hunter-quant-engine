"""
Base Historical Data Provider Tests

Tests the abstract historical data provider contract.
"""

import pytest

from src.historical_data.providers.base_historical_data_provider import (
    BaseHistoricalDataProvider,
)


def test_base_historical_data_provider_cannot_be_instantiated():
    """
    Should not allow direct instantiation of the abstract provider contract.
    """
    with pytest.raises(TypeError):
        BaseHistoricalDataProvider()
