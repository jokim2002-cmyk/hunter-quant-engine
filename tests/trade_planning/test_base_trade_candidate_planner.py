"""
Base Trade Candidate Planner Tests
"""

import pytest

from src.trade_planning.base_trade_candidate_planner import (
    BaseTradeCandidatePlanner,
)


def test_base_trade_candidate_planner_cannot_be_instantiated():
    """
    Should not allow direct instantiation of the abstract planner contract.
    """
    with pytest.raises(TypeError):
        BaseTradeCandidatePlanner()
