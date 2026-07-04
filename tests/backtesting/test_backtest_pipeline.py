"""
Backtest Pipeline Tests
"""

from datetime import datetime

from src.backtesting.backtest_pipeline import BacktestPipeline
from src.historical_data.providers.in_memory_historical_data_provider import (
    InMemoryHistoricalDataProvider,
)
from src.models.candle import Candle
from src.risk.risk_manager import RiskManager
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.simple_candle_trade_candidate_planner import (
    SimpleCandleTradeCandidatePlanner,
)
from tests.builders.risk.risk_profile_builder import RiskProfileBuilder


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


def test_backtest_pipeline_leaves_detection_events_empty_in_v1():
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
        risk_profile=RiskProfileBuilder()
        .with_account_balance(10000.0)
        .with_risk_per_trade(0.01)
        .with_reward_to_risk(2.0)
        .build(),
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
