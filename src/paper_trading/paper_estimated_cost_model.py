"""
Paper Estimated Cost Model

Safe local helper for fake/paper exit cost estimates only.
No real orders. No broker code. No external SDK. Not live market data.
Not a real charges claim.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaperEstimatedExitCosts:
    """
    Estimated paper-only exit costs.

    These values are local simulation inputs only. They are not real broker
    charges and are not a profitability claim.
    """

    quantity: int
    estimated_exit_charges: float
    estimated_slippage: float

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")
        if self.estimated_exit_charges < 0:
            raise ValueError("estimated_exit_charges must be greater than or equal to 0")
        if self.estimated_slippage < 0:
            raise ValueError("estimated_slippage must be greater than or equal to 0")

    @property
    def total_estimated_costs(self) -> float:
        """
        Return estimated paper-only costs.
        """
        return self.estimated_exit_charges + self.estimated_slippage


def estimate_paper_exit_costs(
    quantity: int,
    fixed_exit_charges: float = 40.0,
    slippage_per_quantity: float = 0.10,
) -> PaperEstimatedExitCosts:
    """
    Estimate local paper exit costs from simple deterministic inputs.

    Defaults are intentionally simple demo assumptions:
    - fixed_exit_charges: fixed estimated exit charges
    - slippage_per_quantity: estimated slippage per option quantity

    These are not real broker charges.
    """
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")
    if fixed_exit_charges < 0:
        raise ValueError("fixed_exit_charges must be greater than or equal to 0")
    if slippage_per_quantity < 0:
        raise ValueError("slippage_per_quantity must be greater than or equal to 0")

    estimated_slippage = round(quantity * slippage_per_quantity, 2)

    return PaperEstimatedExitCosts(
        quantity=quantity,
        estimated_exit_charges=fixed_exit_charges,
        estimated_slippage=estimated_slippage,
    )


def paper_estimated_exit_costs_to_dict(
    costs: PaperEstimatedExitCosts,
) -> dict[str, float | int]:
    """
    Convert estimated paper exit costs to a serializable dictionary.
    """
    return {
        "quantity": costs.quantity,
        "estimated_exit_charges": costs.estimated_exit_charges,
        "estimated_slippage": costs.estimated_slippage,
        "total_estimated_costs": costs.total_estimated_costs,
    }
