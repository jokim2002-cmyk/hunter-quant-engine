"""
Institutional Setup Model Tests
"""

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from src.models.institutional_setup import InstitutionalSetup
from src.strategy.signal_type import SignalType


def test_institutional_setup_is_immutable():
    setup = InstitutionalSetup(
        direction=SignalType.LONG,
        confidence=75.0,
        rationale=("Bullish confluence detected.",),
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    with pytest.raises(FrozenInstanceError):
        setup.confidence = 80.0


def test_is_long_returns_true_for_long_setup():
    setup = InstitutionalSetup(
        direction=SignalType.LONG,
        confidence=75.0,
        rationale=("Bullish setup.",),
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setup.is_long() is True
    assert setup.is_short() is False


def test_is_short_returns_true_for_short_setup():
    setup = InstitutionalSetup(
        direction=SignalType.SHORT,
        confidence=75.0,
        rationale=("Bearish setup.",),
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setup.is_short() is True
    assert setup.is_long() is False


def test_has_market_structure_returns_false_without_bos_or_choch():
    setup = InstitutionalSetup(
        direction=SignalType.LONG,
        confidence=75.0,
        rationale=("No structure.",),
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setup.has_market_structure() is False


def test_has_liquidity_sweep_returns_false_without_sweep():
    setup = InstitutionalSetup(
        direction=SignalType.LONG,
        confidence=75.0,
        rationale=("No sweep.",),
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setup.has_liquidity_sweep() is False


def test_has_entry_zone_returns_false_without_fvg_or_order_block():
    setup = InstitutionalSetup(
        direction=SignalType.LONG,
        confidence=75.0,
        rationale=("No entry zone.",),
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setup.has_entry_zone() is False


def test_neutral_setup_is_not_actionable():
    setup = InstitutionalSetup(
        direction=SignalType.NEUTRAL,
        confidence=0.0,
        rationale=("No setup.",),
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setup.is_actionable() is False


def test_setup_without_required_confluence_is_not_actionable():
    setup = InstitutionalSetup(
        direction=SignalType.LONG,
        confidence=75.0,
        rationale=("Incomplete confluence.",),
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    assert setup.is_actionable() is False
