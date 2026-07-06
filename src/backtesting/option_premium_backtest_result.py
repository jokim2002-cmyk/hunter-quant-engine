"""
Option Premium Backtest Result

Result model for one approved option-buy plan backtested on premium candles.
"""

from dataclasses import dataclass

from src.backtesting.option_premium_backtest_exit_reason import (
    OptionPremiumBacktestExitReason,
)
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan


@dataclass(frozen=True)
class OptionPremiumBacktestResult:
    """
    Represents the result of one option premium backtest.
    """

    plan: OptionBuyTradePlan
    exit_reason: OptionPremiumBacktestExitReason
    exit_premium: float
    bars_held: int
    estimated_charges: float

    def __post_init__(self):
        """
        Validate backtest result fields.
        """
        if self.exit_premium <= 0:
            raise ValueError("exit_premium must be greater than 0")

        if self.bars_held < 1:
            raise ValueError("bars_held must be greater than or equal to 1")

        if self.estimated_charges < 0:
            raise ValueError("estimated_charges must be greater than or equal to 0")

    @property
    def quantity(self) -> int:
        """
        Return planned option quantity.
        """
        return self.plan.quantity

    @property
    def gross_pnl(self) -> float:
        """
        Return gross option premium PnL before charges.
        """
        return (self.exit_premium - self.plan.entry_premium) * self.quantity

    @property
    def net_pnl(self) -> float:
        """
        Return PnL after estimated charges.
        """
        return self.gross_pnl - self.estimated_charges

    @property
    def is_win(self) -> bool:
        """
        Return True when net PnL is positive.
        """
        return self.net_pnl > 0

    @property
    def is_loss(self) -> bool:
        """
        Return True when net PnL is negative.
        """
        return self.net_pnl < 0

    @property
    def return_percent(self) -> float:
        """
        Return premium return before charges as a decimal.
        """
        return (self.exit_premium - self.plan.entry_premium) / self.plan.entry_premium
