"""
Backtest Engine

Concrete backtest engine for simulating prepared trade plans.
"""

from src.backtesting.backtest_result import BacktestResult
from src.backtesting.base_backtest_engine import BaseBacktestEngine
from src.backtesting.base_trade_execution_simulator import (
    BaseTradeExecutionSimulator,
)
from src.backtesting.ohlc_trade_execution_simulator import (
    OHLCTradeExecutionSimulator,
)
from src.backtesting.performance_summary_calculator import (
    PerformanceSummaryCalculator,
)
from src.backtesting.trade_result import TradeResult
from src.models.candle import Candle
from src.risk.trade_plan import TradePlan


class BacktestEngine(BaseBacktestEngine):
    """
    Concrete backtest engine for prepared trade plans.

    This engine does not generate trade plans.
    It only simulates already-created risk-approved TradePlan objects.
    """

    def __init__(
        self,
        trade_plans: tuple[TradePlan, ...],
        candles: tuple[Candle, ...],
        trade_execution_simulator: BaseTradeExecutionSimulator | None = None,
        performance_summary_calculator: PerformanceSummaryCalculator | None = None,
    ):
        self._trade_plans = trade_plans
        self._candles = candles
        self._trade_execution_simulator = (
            trade_execution_simulator or OHLCTradeExecutionSimulator()
        )
        self._performance_summary_calculator = (
            performance_summary_calculator or PerformanceSummaryCalculator()
        )

    def run(self) -> BacktestResult:
        trade_results: list[TradeResult] = []

        for trade_plan in self._trade_plans:
            future_candles = self._get_future_candles(trade_plan)

            trade_result = self._trade_execution_simulator.simulate(
                trade_plan=trade_plan,
                candles=future_candles,
            )

            if trade_result is not None:
                trade_results.append(trade_result)

        return BacktestResult.from_trades(
            trades=tuple(trade_results),
            calculator=self._performance_summary_calculator,
        )

    def _get_future_candles(
        self,
        trade_plan: TradePlan,
    ) -> tuple[Candle, ...]:
        return tuple(
            candle
            for candle in self._candles
            if candle.datetime > trade_plan.created_at
        )
