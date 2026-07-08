"""
Option Premium Trade Level Config

Configuration for broker-agnostic option premium SL/target planning.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OptionPremiumTradeLevelConfig:
    """
    Defines fixed-percent stop-loss and target rules for option premiums.

    entry_slippage_percent is applied against the buyer before SL/target
    levels are planned. Defaults keep legacy behavior unchanged.
    """

    stop_loss_percent: float
    target_percent: float
    entry_slippage_percent: float = 0.0

    def __post_init__(self):
        """
        Validate configured percentages.
        """
        if not 0 < self.stop_loss_percent < 1:
            raise ValueError("stop_loss_percent must be greater than 0 and less than 1")

        if self.target_percent <= 0:
            raise ValueError("target_percent must be greater than 0")

        if self.entry_slippage_percent < 0:
            raise ValueError("entry_slippage_percent cannot be negative")
