from dataclasses import FrozenInstanceError

import pytest

from src.models.fair_value_gap import FairValueGap
from src.models.fair_value_gap_type import FairValueGapType


def test_create_bullish_fair_value_gap():
    gap = FairValueGap(
        start_index=10,
        end_index=12,
        high=105.50,
        low=104.20,
        direction=FairValueGapType.BULLISH,
        created_at=12,
    )

    assert gap.start_index == 10
    assert gap.end_index == 12
    assert gap.high == 105.50
    assert gap.low == 104.20
    assert gap.direction == FairValueGapType.BULLISH
    assert gap.created_at == 12
    assert gap.filled is False
    assert gap.filled_at is None


def test_create_bearish_fair_value_gap():
    gap = FairValueGap(
        start_index=20,
        end_index=22,
        high=98.75,
        low=97.40,
        direction=FairValueGapType.BEARISH,
        created_at=22,
    )

    assert gap.direction == FairValueGapType.BEARISH


def test_create_filled_fair_value_gap():
    gap = FairValueGap(
        start_index=30,
        end_index=32,
        high=120.00,
        low=118.50,
        direction=FairValueGapType.BULLISH,
        created_at=32,
        filled=True,
        filled_at=45,
    )

    assert gap.filled is True
    assert gap.filled_at == 45


def test_fair_value_gap_is_immutable():
    gap = FairValueGap(
        start_index=1,
        end_index=3,
        high=100.0,
        low=99.0,
        direction=FairValueGapType.BULLISH,
        created_at=3,
    )

    with pytest.raises(FrozenInstanceError):
        gap.high = 101.0