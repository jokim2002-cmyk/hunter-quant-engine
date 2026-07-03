"""
OHLC Trade Execution Simulator

Simulates historical trade execution using OHLC candles.
"""

from src.backtesting.base_price_fill_model import BasePriceFillModel
from src.backtesting.base_trade_execution_simulator import (
    BaseTradeExecutionSimulator,
)
from src.backtesting.ohlc_price_fill_model import OHLCPriceFillModel
from src.backtesting.trade_result import TradeResult
from src.models.candle import Candle
from src.risk.trade_plan import TradePlan
from src.strategy.signal_type import SignalType


class OHLCTradeExecutionSimulator(BaseTradeExecutionSimulator):
    """
    Simulates trade execution over OHLC candles.

    The simulator manages trade lifecycle and delegates fill decisions
    to a price fill model.
    """

    def __init__(self, price_fill_model: BasePriceFillModel | None = None):
        self._price_fill_model = price_fill_model or OHLCPriceFillModel()

    def simulate(
        self,
        trade_plan: TradePlan,
        candles: tuple[Candle, ...],
    ) -> TradeResult | None:
        for candle in candles:
            fill_result = self._price_fill_model.evaluate(
                trade_plan=trade_plan,
                candle=candle,
            )

            if fill_result.filled:
                if fill_result.fill_price is None:
                    raise ValueError(
                        "Filled price result must include fill_price."
                    )

                return self._create_trade_result(
                    trade_plan=trade_plan,
                    exit_price=fill_result.fill_price,
                    closed_at=candle.datetime,
                )

        return None

    def _create_trade_result(
        self,
        trade_plan: TradePlan,
        exit_price: float,
        closed_at,
    ) -> TradeResult:
        pnl = self._calculate_pnl(
            trade_plan=trade_plan,
            exit_price=exit_price,
        )

        return TradeResult(
            signal_type=trade_plan.signal_type,
            entry_price=trade_plan.entry_price,
            exit_price=exit_price,
            stop_loss=trade_plan.stop_loss,
            take_profit=trade_plan.take_profit,
            position_size=trade_plan.position_size,
            pnl=pnl,
            risk_multiple=pnl / trade_plan.risk_amount,
            opened_at=trade_plan.created_at,
            closed_at=closed_at,
        )

    def _calculate_pnl(
        self,
        trade_plan: TradePlan,
        exit_price: float,
    ) -> float:
        if trade_plan.signal_type == SignalType.LONG:
            return (
                exit_price - trade_plan.entry_price
            ) * trade_plan.position_size

        if trade_plan.signal_type == SignalType.SHORT:
            return (
                trade_plan.entry_price - exit_price
            ) * trade_plan.position_size

        raise ValueError("Unsupported trade signal type.")
