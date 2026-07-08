"""
Option Buy Trade Plan Builder

Builds approved broker-agnostic NIFTY option-buy trade plans.
"""

from dataclasses import dataclass

from src.costs.transaction_cost_calculator import TransactionCostCalculator
from src.models.option_action import OptionAction
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_build_result import (
    OptionBuyTradePlanBuildResult,
)
from src.trade_planning.option_buy_trade_plan_status import (
    OptionBuyTradePlanStatus,
)
from src.trade_planning.option_premium_trade_levels import OptionPremiumTradeLevels
from src.trade_planning.option_strike_selection_result import (
    OptionStrikeSelectionResult,
)


@dataclass(frozen=True)
class _EstimatedTargetExitTrade:
    """
    Trade-like object used only for planned target-exit charge estimation.
    """

    entry_price: float
    exit_price: float
    position_size: int
    pnl: float


class OptionBuyTradePlanBuilder:
    """
    Builds approved option-buy trade plans from selected strikes and premium levels.
    """

    def __init__(
        self,
        lots: int,
        cost_calculator: TransactionCostCalculator | None = None,
        min_estimated_net_reward: float = 0.0,
    ):
        """
        Initialize builder.
        """
        if lots <= 0:
            raise ValueError("lots must be greater than 0")

        if min_estimated_net_reward < 0:
            raise ValueError("min_estimated_net_reward cannot be negative")

        self.lots = lots
        self.cost_calculator = cost_calculator or TransactionCostCalculator()
        self.min_estimated_net_reward = min_estimated_net_reward

    def build(
        self,
        selection_result: OptionStrikeSelectionResult,
        premium_levels: OptionPremiumTradeLevels | None,
        underlying_price: float,
    ) -> OptionBuyTradePlanBuildResult:
        """
        Build an approved option-buy trade plan, or return clear rejection reasons.
        """
        if not selection_result.has_selection:
            rejection_reasons = selection_result.rejection_reasons
            if not rejection_reasons:
                rejection_reasons = (selection_result.selected_reason,)

            return OptionBuyTradePlanBuildResult(
                plan=None,
                rejection_reasons=rejection_reasons,
            )

        selected_entry = selection_result.selected_entry
        if selected_entry is None:
            return OptionBuyTradePlanBuildResult(
                plan=None,
                rejection_reasons=("selected option entry is required",),
            )

        if premium_levels is None:
            return OptionBuyTradePlanBuildResult(
                plan=None,
                rejection_reasons=(
                    "premium levels are required to build option-buy trade plan",
                ),
            )

        if premium_levels.entry != selected_entry:
            return OptionBuyTradePlanBuildResult(
                plan=None,
                rejection_reasons=(
                    "premium levels entry must match selected option entry",
                ),
            )

        quantity = selected_entry.contract.quantity_for_lots(self.lots)
        estimated_trade = _EstimatedTargetExitTrade(
            entry_price=premium_levels.entry_premium,
            exit_price=premium_levels.target_premium,
            position_size=quantity,
            pnl=premium_levels.reward_per_unit * quantity,
        )
        cost_breakdown = self.cost_calculator.calculate(estimated_trade)
        estimated_net_reward = premium_levels.reward_per_unit * quantity
        estimated_net_reward -= cost_breakdown.total_charges

        if estimated_net_reward < self.min_estimated_net_reward:
            return OptionBuyTradePlanBuildResult(
                plan=None,
                rejection_reasons=(
                    "estimated net reward below minimum "
                    f"{self.min_estimated_net_reward}",
                ),
            )

        plan = OptionBuyTradePlan(
            signal=selection_result.signal,
            entry=selected_entry,
            action=OptionAction.BUY,
            underlying_price=underlying_price,
            entry_premium=premium_levels.entry_premium,
            stop_loss_premium=premium_levels.stop_loss_premium,
            target_premium=premium_levels.target_premium,
            lots=self.lots,
            estimated_charges=cost_breakdown.total_charges,
            status=OptionBuyTradePlanStatus.APPROVED,
            rejection_reasons=(),
        )

        return OptionBuyTradePlanBuildResult(plan=plan)
