"""
Paper Estimated Cost Model Tests

Fake/local paper cost estimates only. No real orders. No broker code.
Not live market data. Not a real charges claim.
"""

from pathlib import Path

import pytest

from src.paper_trading.paper_estimated_cost_model import (
    PaperEstimatedExitCosts,
    estimate_paper_exit_costs,
    paper_estimated_exit_costs_to_dict,
)


def test_estimated_exit_costs_accepts_valid_values():
    costs = PaperEstimatedExitCosts(
        quantity=130,
        estimated_exit_charges=40.0,
        estimated_slippage=13.0,
    )

    assert costs.quantity == 130
    assert costs.estimated_exit_charges == 40.0
    assert costs.estimated_slippage == 13.0
    assert costs.total_estimated_costs == 53.0


def test_estimate_paper_exit_costs_uses_default_demo_model():
    costs = estimate_paper_exit_costs(quantity=130)

    assert costs == PaperEstimatedExitCosts(
        quantity=130,
        estimated_exit_charges=40.0,
        estimated_slippage=13.0,
    )
    assert costs.total_estimated_costs == 53.0


def test_estimate_paper_exit_costs_accepts_custom_inputs():
    costs = estimate_paper_exit_costs(
        quantity=65,
        fixed_exit_charges=20.0,
        slippage_per_quantity=0.25,
    )

    assert costs.estimated_exit_charges == 20.0
    assert costs.estimated_slippage == 16.25
    assert costs.total_estimated_costs == 36.25


def test_paper_estimated_exit_costs_to_dict():
    costs = estimate_paper_exit_costs(quantity=130)

    payload = paper_estimated_exit_costs_to_dict(costs)

    assert payload == {
        "quantity": 130,
        "estimated_exit_charges": 40.0,
        "estimated_slippage": 13.0,
        "total_estimated_costs": 53.0,
    }


def test_estimated_exit_costs_rejects_zero_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        PaperEstimatedExitCosts(
            quantity=0,
            estimated_exit_charges=40.0,
            estimated_slippage=13.0,
        )


def test_estimated_exit_costs_rejects_negative_charges():
    with pytest.raises(
        ValueError,
        match="estimated_exit_charges must be greater than or equal to 0",
    ):
        PaperEstimatedExitCosts(
            quantity=130,
            estimated_exit_charges=-1.0,
            estimated_slippage=13.0,
        )


def test_estimated_exit_costs_rejects_negative_slippage():
    with pytest.raises(
        ValueError,
        match="estimated_slippage must be greater than or equal to 0",
    ):
        PaperEstimatedExitCosts(
            quantity=130,
            estimated_exit_charges=40.0,
            estimated_slippage=-1.0,
        )


def test_estimate_paper_exit_costs_rejects_zero_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        estimate_paper_exit_costs(quantity=0)


def test_estimate_paper_exit_costs_rejects_negative_fixed_charges():
    with pytest.raises(
        ValueError,
        match="fixed_exit_charges must be greater than or equal to 0",
    ):
        estimate_paper_exit_costs(quantity=130, fixed_exit_charges=-1.0)


def test_estimate_paper_exit_costs_rejects_negative_slippage_per_quantity():
    with pytest.raises(
        ValueError,
        match="slippage_per_quantity must be greater than or equal to 0",
    ):
        estimate_paper_exit_costs(quantity=130, slippage_per_quantity=-0.01)


def test_cost_model_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_estimated_cost_model.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
