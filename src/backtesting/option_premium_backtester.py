"""
Option Premium Backtester

Conservative single-plan option premium backtest core.
"""

from collections.abc import Sequence

from src.backtesting.option_premium_backtest_exit_reason import (
    OptionPremiumBacktestExitReason,
)
from src.backtesting.option_premium_backtest_result import OptionPremiumBacktestResult
from src.models.option_premium_candle import OptionPremiumCandle
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


class OptionPremiumBacktester:
    """
    Backtests one approved option-buy trade plan against premium OHLC candles.
    """

    def backtest(
        self,
        plan: OptionBuyTradePlan,
        premium_candles: Sequence[OptionPremiumCandle],
    ) -> OptionPremiumBacktestResult:
        """
        Simulate one approved option-buy plan on option premium candles.
        """
        if plan.status is not OptionBuyTradePlanStatus.APPROVED:
            raise ValueError("only approved option-buy trade plans can be backtested")

        if not premium_candles:
            raise ValueError("premium candles are required")

        for index, candle in enumerate(premium_candles, start=1):
            if candle.low <= plan.stop_loss_premium:
                return OptionPremiumBacktestResult(
                    plan=plan,
                    exit_reason=OptionPremiumBacktestExitReason.STOP_LOSS_HIT,
                    exit_premium=plan.stop_loss_premium,
                    bars_held=index,
                    estimated_charges=plan.estimated_charges,
                )

            if candle.high >= plan.target_premium:
                return OptionPremiumBacktestResult(
                    plan=plan,
                    exit_reason=OptionPremiumBacktestExitReason.TARGET_HIT,
                    exit_premium=plan.target_premium,
                    bars_held=index,
                    estimated_charges=plan.estimated_charges,
                )

        return OptionPremiumBacktestResult(
            plan=plan,
            exit_reason=OptionPremiumBacktestExitReason.END_OF_DATA,
            exit_premium=premium_candles[-1].close,
            bars_held=len(premium_candles),
            estimated_charges=plan.estimated_charges,
        )
