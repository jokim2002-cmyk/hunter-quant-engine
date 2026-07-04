"""
Backtest Pipeline Tests
"""

from datetime import datetime

from src.backtesting.backtest_pipeline import BacktestPipeline
from src.historical_data.providers.in_memory_historical_data_provider import (
    InMemoryHistoricalDataProvider,
)
from src.models.candle import Candle
from src.models.order_block import OrderBlock
from src.models.order_block_type import OrderBlockType
from src.risk.risk_manager import RiskManager
from src.risk.risk_profile import RiskProfile
from src.strategy.context_factories.default_strategy_context_factory import (
    DefaultStrategyContextFactory,
)
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.simple_candle_trade_candidate_planner import (
    SimpleCandleTradeCandidatePlanner,
)
from src.trade_planning.smc_trade_candidate_planner import (
    SMCTradeCandidatePlanner,
)
from src.trade_planning.trade_candidate import TradeCandidate
from tests.builders.risk.risk_profile_builder import RiskProfileBuilder
from tests.builders.strategy.strategy_context_builder import StrategyContextBuilder


def _candle(
    candle_time: datetime,
    open_price: float = 100.0,
    high: float = 105.0,
    low: float = 95.0,
    close: float = 100.0,
) -> Candle:
    return Candle(
        datetime=candle_time,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
    )


def _long_signal(created_at: datetime) -> TradeSignal:
    return TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.MEDIUM,
        confidence=0.75,
        rationale=("Test long signal.",),
        created_at=created_at,
    )


def _neutral_signal(created_at: datetime) -> TradeSignal:
    return TradeSignal(
        signal_type=SignalType.NEUTRAL,
        strength=SignalStrength.WEAK,
        confidence=0.0,
        rationale=("No setup.",),
        created_at=created_at,
    )


class RecordingNeutralStrategy:
    def __init__(self):
        self.contexts = []

    def generate(self, context):
        self.contexts.append(context)
        return (_neutral_signal(context.analysis_time),)


class FirstCandleLongStrategy:
    def generate(self, context):
        if len(context.candles) == 1:
            return (_long_signal(context.analysis_time),)

        return (_neutral_signal(context.analysis_time),)


class RepeatingLongStrategy:
    def generate(self, context):
        return (_long_signal(context.analysis_time),)


class FixedTradeCandidatePlanner:
    def __init__(
        self,
        entry_price: float,
        stop_loss: float,
    ):
        self._entry_price = entry_price
        self._stop_loss = stop_loss

    def plan(
        self,
        signal,
        context,
    ):
        if signal.signal_type == SignalType.NEUTRAL:
            return ()

        return (
            TradeCandidate(
                signal=signal,
                entry_price=self._entry_price,
                stop_loss=self._stop_loss,
            ),
        )


class RecordingDeduplicator:
    def __init__(self):
        self.received_trade_plans = ()

    def deduplicate(
        self,
        trade_plans,
    ):
        self.received_trade_plans = trade_plans

        return trade_plans[:1]


class RecordingStrategyContextFactory:
    def __init__(self):
        self.calls = []
        self._delegate = DefaultStrategyContextFactory()

    def create(
        self,
        symbol,
        timeframe,
        analysis_time,
        candles,
    ):
        self.calls.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "analysis_time": analysis_time,
                "candles": candles,
            }
        )

        return self._delegate.create(
            symbol=symbol,
            timeframe=timeframe,
            analysis_time=analysis_time,
            candles=candles,
        )


class FixedOrderBlockStrategyContextFactory:
    def __init__(
        self,
        order_block: OrderBlock,
    ):
        self._order_block = order_block

    def create(
        self,
        symbol,
        timeframe,
        analysis_time,
        candles,
    ):
        return (
            StrategyContextBuilder()
            .analysis_time(analysis_time)
            .with_candles(*candles)
            .with_order_blocks(self._order_block)
            .build()
        )


def _risk_profile() -> RiskProfile:
    return (
        RiskProfileBuilder()
        .with_account_balance(10000.0)
        .with_risk_per_trade(0.01)
        .with_reward_to_risk(2.0)
        .build()
    )


def test_backtest_pipeline_returns_empty_result_when_no_candles_exist():
    pipeline = BacktestPipeline(
        historical_data_provider=InMemoryHistoricalDataProvider(()),
        strategy=RecordingNeutralStrategy(),
        trade_candidate_planner=SimpleCandleTradeCandidatePlanner(),
        risk_manager=RiskManager(),
        risk_profile=RiskProfileBuilder().build(),
        symbol="TEST",
        timeframe="1H",
    )

    result = pipeline.run()

    assert result.trades == ()
    assert result.performance_summary.total_trades == 0


def test_backtest_pipeline_builds_walk_forward_contexts():
    strategy = RecordingNeutralStrategy()
    first_candle = _candle(datetime(2026, 1, 1, 9, 0))
    second_candle = _candle(datetime(2026, 1, 1, 10, 0))

    pipeline = BacktestPipeline(
        historical_data_provider=InMemoryHistoricalDataProvider(
            (first_candle, second_candle)
        ),
        strategy=strategy,
        trade_candidate_planner=SimpleCandleTradeCandidatePlanner(),
        risk_manager=RiskManager(),
        risk_profile=RiskProfileBuilder().build(),
        symbol="EURUSD",
        timeframe="1H",
    )

    pipeline.run()

    assert len(strategy.contexts) == 2
    assert strategy.contexts[0].candles == (first_candle,)
    assert strategy.contexts[1].candles == (first_candle, second_candle)


def test_backtest_pipeline_delegates_context_creation_to_factory():
    factory = RecordingStrategyContextFactory()
    strategy = RecordingNeutralStrategy()
    first_candle = _candle(datetime(2026, 1, 1, 9, 0))
    second_candle = _candle(datetime(2026, 1, 1, 10, 0))

    pipeline = BacktestPipeline(
        historical_data_provider=InMemoryHistoricalDataProvider(
            (first_candle, second_candle)
        ),
        strategy=strategy,
        trade_candidate_planner=SimpleCandleTradeCandidatePlanner(),
        risk_manager=RiskManager(),
        risk_profile=RiskProfileBuilder().build(),
        symbol="EURUSD",
        timeframe="1H",
        strategy_context_factory=factory,
    )

    pipeline.run()

    assert len(factory.calls) == 2
    assert factory.calls[0]["symbol"] == "EURUSD"
    assert factory.calls[0]["timeframe"] == "1H"
    assert factory.calls[0]["analysis_time"] == first_candle.datetime
    assert factory.calls[0]["candles"] == (first_candle,)
    assert factory.calls[1]["analysis_time"] == second_candle.datetime
    assert factory.calls[1]["candles"] == (first_candle, second_candle)


def test_backtest_pipeline_sets_context_metadata():
    strategy = RecordingNeutralStrategy()
    candle = _candle(datetime(2026, 1, 1, 9, 0))

    pipeline = BacktestPipeline(
        historical_data_provider=InMemoryHistoricalDataProvider((candle,)),
        strategy=strategy,
        trade_candidate_planner=SimpleCandleTradeCandidatePlanner(),
        risk_manager=RiskManager(),
        risk_profile=RiskProfileBuilder().build(),
        symbol="BTCUSD",
        timeframe="4H",
    )

    pipeline.run()

    context = strategy.contexts[0]

    assert context.symbol == "BTCUSD"
    assert context.timeframe == "4H"
    assert context.analysis_time == candle.datetime


def test_backtest_pipeline_leaves_detection_events_empty_when_no_detections_exist():
    strategy = RecordingNeutralStrategy()
    candle = _candle(datetime(2026, 1, 1, 9, 0))

    pipeline = BacktestPipeline(
        historical_data_provider=InMemoryHistoricalDataProvider((candle,)),
        strategy=strategy,
        trade_candidate_planner=SimpleCandleTradeCandidatePlanner(),
        risk_manager=RiskManager(),
        risk_profile=RiskProfileBuilder().build(),
        symbol="TEST",
        timeframe="1H",
    )

    pipeline.run()

    context = strategy.contexts[0]

    assert context.market_structure_points == ()
    assert context.bos_events == ()
    assert context.choch_events == ()
    assert context.liquidity_points == ()
    assert context.equal_high_points == ()
    assert context.equal_low_points == ()
    assert context.liquidity_clusters == ()
    assert context.liquidity_sweeps == ()
    assert context.fair_value_gaps == ()
    assert context.order_blocks == ()


def test_backtest_pipeline_generates_trade_plan_and_backtest_result():
    signal_candle = _candle(
        candle_time=datetime(2026, 1, 1, 9, 0),
        high=104.0,
        low=95.0,
        close=100.0,
    )
    closing_candle = _candle(
        candle_time=datetime(2026, 1, 1, 10, 0),
        high=110.0,
        low=96.0,
        close=108.0,
    )

    pipeline = BacktestPipeline(
        historical_data_provider=InMemoryHistoricalDataProvider(
            (signal_candle, closing_candle)
        ),
        strategy=FirstCandleLongStrategy(),
        trade_candidate_planner=SimpleCandleTradeCandidatePlanner(),
        risk_manager=RiskManager(),
        risk_profile=_risk_profile(),
        symbol="TEST",
        timeframe="1H",
    )

    result = pipeline.run()

    assert len(result.trades) == 1
    assert result.trades[0].entry_price == 100.0
    assert result.trades[0].stop_loss == 95.0
    assert result.trades[0].take_profit == 110.0
    assert result.trades[0].exit_price == 110.0
    assert result.trades[0].pnl == 200.0
    assert result.performance_summary.total_trades == 1
    assert result.performance_summary.total_pnl == 200.0


def test_backtest_pipeline_can_use_smc_trade_candidate_planner_via_di():
    signal_candle = _candle(
        candle_time=datetime(2026, 1, 1, 9, 0),
        high=104.0,
        low=95.0,
        close=100.0,
    )
    closing_candle = _candle(
        candle_time=datetime(2026, 1, 1, 10, 0),
        high=109.0,
        low=97.0,
        close=108.0,
    )
    order_block = OrderBlock(
        candle_index=0,
        high=104.0,
        low=96.0,
        open=103.0,
        close=97.0,
        order_block_type=OrderBlockType.BULLISH,
        created_at=signal_candle.datetime,
    )

    pipeline = BacktestPipeline(
        historical_data_provider=InMemoryHistoricalDataProvider(
            (signal_candle, closing_candle)
        ),
        strategy=FirstCandleLongStrategy(),
        trade_candidate_planner=SMCTradeCandidatePlanner(),
        risk_manager=RiskManager(),
        risk_profile=_risk_profile(),
        symbol="TEST",
        timeframe="1H",
        strategy_context_factory=FixedOrderBlockStrategyContextFactory(
            order_block=order_block,
        ),
    )

    result = pipeline.run()

    assert len(result.trades) == 1
    assert result.trades[0].entry_price == 100.0
    assert result.trades[0].stop_loss == 96.0
    assert result.trades[0].take_profit == 108.0
    assert result.trades[0].exit_price == 108.0
    assert result.trades[0].pnl == 200.0
    assert result.performance_summary.total_trades == 1
    assert result.performance_summary.total_pnl == 200.0


def test_backtest_pipeline_deduplicates_repeated_trade_plans_by_default():
    first_candle = _candle(
        candle_time=datetime(2026, 1, 1, 9, 0),
        high=105.0,
        low=95.0,
        close=100.0,
    )
    second_candle = _candle(
        candle_time=datetime(2026, 1, 1, 9, 5),
        high=109.0,
        low=98.0,
        close=108.0,
    )
    third_candle = _candle(
        candle_time=datetime(2026, 1, 1, 9, 10),
        high=109.0,
        low=98.0,
        close=108.0,
    )

    pipeline = BacktestPipeline(
        historical_data_provider=InMemoryHistoricalDataProvider(
            (
                first_candle,
                second_candle,
                third_candle,
            )
        ),
        strategy=RepeatingLongStrategy(),
        trade_candidate_planner=FixedTradeCandidatePlanner(
            entry_price=100.0,
            stop_loss=96.0,
        ),
        risk_manager=RiskManager(),
        risk_profile=_risk_profile(),
        symbol="TEST",
        timeframe="5m",
    )

    result = pipeline.run()

    assert len(result.trades) == 1
    assert result.trades[0].entry_price == 100.0
    assert result.trades[0].stop_loss == 96.0
    assert result.trades[0].take_profit == 108.0
    assert result.trades[0].exit_price == 108.0
    assert result.trades[0].pnl == 200.0


def test_backtest_pipeline_accepts_injected_trade_plan_deduplicator():
    deduplicator = RecordingDeduplicator()
    first_candle = _candle(
        candle_time=datetime(2026, 1, 1, 9, 0),
        high=105.0,
        low=95.0,
        close=100.0,
    )
    second_candle = _candle(
        candle_time=datetime(2026, 1, 1, 9, 5),
        high=109.0,
        low=98.0,
        close=108.0,
    )

    pipeline = BacktestPipeline(
        historical_data_provider=InMemoryHistoricalDataProvider(
            (
                first_candle,
                second_candle,
            )
        ),
        strategy=RepeatingLongStrategy(),
        trade_candidate_planner=FixedTradeCandidatePlanner(
            entry_price=100.0,
            stop_loss=96.0,
        ),
        risk_manager=RiskManager(),
        risk_profile=_risk_profile(),
        symbol="TEST",
        timeframe="5m",
        trade_plan_deduplicator=deduplicator,
    )

    pipeline.run()

    assert len(deduplicator.received_trade_plans) == 2
    assert deduplicator.received_trade_plans[0].created_at == first_candle.datetime
    assert deduplicator.received_trade_plans[1].created_at == second_candle.datetime
