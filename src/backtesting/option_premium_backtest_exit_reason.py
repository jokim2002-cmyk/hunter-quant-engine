"""
Option Premium Backtest Exit Reason

Defines deterministic exit reasons for option premium backtests.
"""

from enum import Enum


class OptionPremiumBacktestExitReason(Enum):
    """
    Represents why an option premium backtest exited.
    """

    TARGET_HIT = "target_hit"
    STOP_LOSS_HIT = "stop_loss_hit"
    END_OF_DATA = "end_of_data"
