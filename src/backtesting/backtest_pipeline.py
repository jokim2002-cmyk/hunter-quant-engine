"""
Backtest Pipeline

Walk-forward pipeline for generating trade plans and running backtests.
"""

from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.backtest_result import BacktestResult
from src.backtesting.base_backtest_pipeline import BaseBacktestPipeline
from src.historical_data.providers.base_historical_data_provider import (
    BaseHistoricalDataProvider,
)
from src.historical_data.providers.in_memory_historical_data_provider import (
    InMemoryHistoricalDataProvider,
)
from src.models.candle import Candle
from src.risk.base_risk_manager import BaseRiskManager
from src.risk.risk_profile import RiskProfile
from src.risk.trade_plan import TradePlan
from src.strategy.base_strategy import BaseStrategy
from src.strategy.strategy_context import StrategyContext
from src.trade_planning.base_trade_candidate_planner import (
    BaseTradeCandidatePlanner,
)


class BacktestPipeline(BaseBacktestPipeline):
    """
    Walk-forward backtest pipeline.

    The pipeline loads historical candles, builds walk-forward StrategyContext
    snapshots, generates strategy signals, converts them into trade candidates,
    creates risk-approved trade plans, and delegates execution to BacktestEngine.
    """

    def __init__(
        self,
        historical_data_provider: BaseHistoricalDataProvider,
        strategy: BaseStrategy,
        trade_candidate_planner: BaseTradeCandidatePlanner,
        risk_manager: BaseRiskManager,
        risk_profile: RiskProfile,
        symbol: str,
        timeframe: str,
    ):
        self._historical_data_provider = historical_data_provider
        self._strategy = strategy
        self._trade_candidate_planner = trade_candidate_planner
        self._risk_manager = risk_manager
        self._risk_profile = risk_profile
        self._symbol = symbol
        self._timeframe = timeframe

    def run(self) -> BacktestResult:
        candles = self._historical_data_provider.load()
        trade_plans = self._create_trade_plans(candles)

        return BacktestEngine(
            trade_plans=trade_plans,
            historical_data_provider=InMemoryHistoricalDataProvider(candles),
        ).run()

    def _create_trade_plans(
        self,
        candles: tuple[Candle, ...],
    ) -> tuple[TradePlan, ...]:
        trade_plans: list[TradePlan] = []

        for index, candle in enumerate(candles):
            context = self._build_context(
                candles=candles[: index + 1],
                analysis_candle=candle,
            )

            signals = self._strategy.generate(context)

            for signal in signals:
                candidates = self._trade_candidate_planner.plan(
                    signal=signal,
                    context=context,
                )

                for candidate in candidates:
                    plans = self._risk_manager.plan(
                        signal=candidate.signal,
                        risk_profile=self._risk_profile,
                        entry_price=candidate.entry_price,
                        stop_loss=candidate.stop_loss,
                    )

                    trade_plans.extend(plans)

        return tuple(trade_plans)

    def _build_context(
        self,
        candles: tuple[Candle, ...],
        analysis_candle: Candle,
    ) -> StrategyContext:
        return StrategyContext(
            symbol=self._symbol,
            timeframe=self._timeframe,
            analysis_time=analysis_candle.datetime,
            candles=candles,
            market_structure_points=(),
            bos_events=(),
            choch_events=(),
            liquidity_points=(),
            equal_high_points=(),
            equal_low_points=(),
            liquidity_clusters=(),
            liquidity_sweeps=(),
            fair_value_gaps=(),
            order_blocks=(),
        )
