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
        entry_premium, premium_source = self._entry_premium(entry)

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
