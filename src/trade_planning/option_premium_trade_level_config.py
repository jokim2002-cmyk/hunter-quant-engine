"""
Option Premium Trade Level Config

Configuration for broker-agnostic option premium SL/target planning.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OptionPremiumTradeLevelConfig:
    """
    Defines fixed-percent stop-loss and target rules for option premiums.
    """

    stop_loss_percent: float
    target_percent: float

    def __post_init__(self):
        """
        Validate configured percentages.
        """
        if not 0 < self.stop_loss_percent < 1:
            raise ValueError("stop_loss_percent must be greater than 0 and less than 1")

        if self.target_percent <= 0:
            raise ValueError("target_percent must be greater than 0")
