"""
Fixed Percent Option Premium Trade Level Planner

Plans option premium stop-loss and target levels using fixed percentages.
"""

from src.models.option_chain_entry import OptionChainEntry
from src.trade_planning.option_premium_trade_level_config import (
    OptionPremiumTradeLevelConfig,
)
from src.trade_planning.option_premium_trade_levels import OptionPremiumTradeLevels


class FixedPercentOptionPremiumTradeLevelPlanner:
    """
    Builds option premium levels from ask price or last traded price.

    Buyer-side entry slippage can be configured through
    OptionPremiumTradeLevelConfig. Defaults keep legacy behavior unchanged.
    """

    def __init__(
        self,
        config: OptionPremiumTradeLevelConfig,
    ):
        """
        Initialize planner with fixed-percent premium rules.
        """
        self.config = config

    def plan(
        self,
        entry: OptionChainEntry,
    ) -> OptionPremiumTradeLevels:
        """
        Return premium trade levels for an option chain entry.
        """
        base_entry_premium, premium_source = self._entry_premium(entry)
        entry_premium = self._apply_entry_slippage(base_entry_premium)

        if self.config.entry_slippage_percent > 0:
            premium_source = (
                f"{premium_source}+entry_slippage_"
                f"{self.config.entry_slippage_percent}"
            )

        return OptionPremiumTradeLevels(
            entry=entry,
            entry_premium=entry_premium,
            stop_loss_premium=entry_premium * (1 - self.config.stop_loss_percent),
            target_premium=entry_premium * (1 + self.config.target_percent),
            premium_source=premium_source,
        )

    def _entry_premium(
        self,
        entry: OptionChainEntry,
    ) -> tuple[float, str]:
        """
        Use ask price first, then last traded price.
        """
        if entry.ask_price is not None:
            return entry.ask_price, "ask_price"

        return entry.last_traded_price, "last_traded_price"

    def _apply_entry_slippage(
        self,
        entry_premium: float,
    ) -> float:
        """
        Apply buyer-adverse entry slippage to the planned premium.
        """
        return entry_premium * (1 + self.config.entry_slippage_percent)
