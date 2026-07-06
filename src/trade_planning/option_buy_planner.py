"""
Option Buy Planner

Broker-agnostic pipeline for the first HQE NIFTY option-buy module.
"""

from src.models.option_chain_snapshot import OptionChainSnapshot
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.dynamic_option_strike_selector import (
    DynamicOptionStrikeSelector,
)
from src.trade_planning.fixed_percent_option_premium_trade_level_planner import (
    FixedPercentOptionPremiumTradeLevelPlanner,
)
from src.trade_planning.option_buy_trade_plan_build_result import (
    OptionBuyTradePlanBuildResult,
)
from src.trade_planning.option_buy_trade_plan_builder import OptionBuyTradePlanBuilder
from src.trade_planning.option_premium_trade_level_config import (
    OptionPremiumTradeLevelConfig,
)


class OptionBuyPlanner:
    """
    Orchestrates strike selection, premium levels, and option-buy plan building.
    """

    def __init__(
        self,
        strike_selector: DynamicOptionStrikeSelector | None = None,
        premium_level_planner: FixedPercentOptionPremiumTradeLevelPlanner | None = None,
        trade_plan_builder: OptionBuyTradePlanBuilder | None = None,
    ):
        """
        Initialize planner dependencies with safe defaults.
        """
        self.strike_selector = strike_selector or DynamicOptionStrikeSelector()
        self.premium_level_planner = premium_level_planner or (
            FixedPercentOptionPremiumTradeLevelPlanner(
                config=OptionPremiumTradeLevelConfig(
                    stop_loss_percent=0.30,
                    target_percent=0.60,
                )
            )
        )
        self.trade_plan_builder = trade_plan_builder or OptionBuyTradePlanBuilder(lots=1)

    def plan(
        self,
        signal: TradeSignal,
        snapshot: OptionChainSnapshot,
    ) -> OptionBuyTradePlanBuildResult:
        """
        Return an approved option-buy plan or clear rejection result.
        """
        selection_result = self.strike_selector.select(
            signal=signal,
            snapshot=snapshot,
        )

        if not selection_result.has_selection:
            return self.trade_plan_builder.build(
                selection_result=selection_result,
                premium_levels=None,
                underlying_price=snapshot.underlying_price,
            )

        selected_entry = selection_result.selected_entry
        try:
            premium_levels = self.premium_level_planner.plan(selected_entry)
        except ValueError as error:
            return OptionBuyTradePlanBuildResult(
                plan=None,
                rejection_reasons=(f"premium level planning failed: {error}",),
            )

        return self.trade_plan_builder.build(
            selection_result=selection_result,
            premium_levels=premium_levels,
            underlying_price=snapshot.underlying_price,
        )
