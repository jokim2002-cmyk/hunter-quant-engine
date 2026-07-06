"""
Option Buy Trade Plan Build Result

Represents the outcome of attempting to build an option-buy trade plan.
"""

from dataclasses import dataclass

from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan


@dataclass(frozen=True)
class OptionBuyTradePlanBuildResult:
    """
    Immutable result for option-buy trade plan building.
    """

    plan: OptionBuyTradePlan | None
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self):
        """
        Validate and normalize build result fields.
        """
        object.__setattr__(self, "rejection_reasons", tuple(self.rejection_reasons))

        if self.plan is None and not self.rejection_reasons:
            raise ValueError("rejection_reasons are required when plan is missing")

        if self.plan is not None and self.rejection_reasons:
            raise ValueError("rejection_reasons must be empty when plan exists")

    @property
    def has_plan(self) -> bool:
        """
        Return True when a trade plan was built.
        """
        return self.plan is not None
