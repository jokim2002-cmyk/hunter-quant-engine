"""
Tests for BacktestEngine.
"""

from datetime import datetime

from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.trade_result import TradeResult
from src.models.candle import Candle
from src.risk.trade_plan import TradePlan
from src.strategy.signal_type import SignalType


def _candle(
    candle_time: datetime,
    high: float,
    low: float,
) -> Candle:
    return Candle(
        datetime=candle_time,
        open=100.0,
        high=high,
        low=low,
        close=100.0,
        volume=1000.0,
    )


def _long_trade_plan(created_at: datetime) -> TradePlan:
    return TradePlan(
        signal_type=SignalType.LONG,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size=10.0,
        risk_amount=50.0,
        reward_amount=100.0,
        created_at=created_at,
    )


def _short_trade_plan(created_at: datetime) -> TradePlan:
    return TradePlan(
        signal_type=SignalType.SHORT,
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
        position_size=10.0,
        risk_amount=50.0,
        reward_amount=100.0,
        created_at=created_at,
    )


def test_backtest_engine_returns_empty_result_when_no_trade_plans_exist():
    result = BacktestEngine(
        trade_plans=(),
        candles=(),
    ).run()

    assert result.trades == ()
    assert result.performance_summary.total_trades == 0
    assert result.performance_summary.total_pnl == 0.0


def test_backtest_engine_returns_empty_result_when_trade_never_closes():
    trade_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 0),
    )
    candles = (
        _candle(datetime(2026, 1, 1, 10, 0), high=108.0, low=96.0),
        _candle(datetime(2026, 1, 1, 11, 0), high=109.0, low=97.0),
    )

    result = BacktestEngine(
        trade_plans=(trade_plan,),
        candles=candles,
    ).run()

    assert result.trades == ()
    assert result.performance_summary.total_trades == 0


def test_backtest_engine_records_closed_long_trade():
    trade_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 0),
    )
    closing_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=110.0,
        low=96.0,
    )

    result = BacktestEngine(
        trade_plans=(trade_plan,),
        candles=(closing_candle,),
    ).run()

    assert len(result.trades) == 1
    assert result.trades[0].signal_type is SignalType.LONG
    assert result.trades[0].exit_price == 110.0
    assert result.trades[0].pnl == 100.0
    assert result.performance_summary.total_trades == 1
    assert result.performance_summary.winning_trades == 1
    assert result.performance_summary.total_pnl == 100.0


def test_backtest_engine_records_closed_short_trade():
    trade_plan = _short_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 0),
    )
    closing_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=104.0,
        low=90.0,
    )

    result = BacktestEngine(
        trade_plans=(trade_plan,),
        candles=(closing_candle,),
    ).run()

    assert len(result.trades) == 1
    assert result.trades[0].signal_type is SignalType.SHORT
    assert result.trades[0].exit_price == 90.0
    assert result.trades[0].pnl == 100.0
    assert result.performance_summary.total_trades == 1
    assert result.performance_summary.winning_trades == 1


def test_backtest_engine_ignores_candles_before_trade_plan_creation_time():
    trade_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 10, 0),
    )
    old_candle_that_would_have_hit_take_profit = _candle(
        datetime(2026, 1, 1, 9, 0),
        high=120.0,
        low=96.0,
    )
    future_candle_that_hits_stop_loss = _candle(
        datetime(2026, 1, 1, 11, 0),
        high=108.0,
        low=95.0,
    )

    result = BacktestEngine(
        trade_plans=(trade_plan,),
        candles=(
            old_candle_that_would_have_hit_take_profit,
            future_candle_that_hits_stop_loss,
        ),
    ).run()

    assert len(result.trades) == 1
    assert result.trades[0].exit_price == 95.0
    assert result.trades[0].pnl == -50.0
    assert result.performance_summary.losing_trades == 1


def test_backtest_engine_collects_multiple_closed_trade_results():
    long_trade_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 0),
    )
    short_trade_plan = _short_trade_plan(
        created_at=datetime(2026, 1, 1, 10, 30),
    )
    long_closing_candle = _candle(
        datetime(2026, 1, 1, 10, 0),
        high=110.0,
        low=96.0,
    )
    short_closing_candle = _candle(
        datetime(2026, 1, 1, 11, 0),
        high=104.0,
        low=90.0,
    )

    result = BacktestEngine(
        trade_plans=(long_trade_plan, short_trade_plan),
        candles=(
            long_closing_candle,
            short_closing_candle,
        ),
    ).run()

    assert len(result.trades) == 2
    assert result.performance_summary.total_trades == 2
    assert result.performance_summary.total_pnl == 200.0
    assert result.performance_summary.win_rate == 1.0


class RecordingTradeExecutionSimulator:
    def __init__(self):
        self.received_candles = None

    def simulate(self, trade_plan, candles):
        self.received_candles = candles
        return None


def test_backtest_engine_passes_only_future_candles_to_simulator():
    simulator = RecordingTradeExecutionSimulator()
    trade_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 10, 0),
    )
    old_candle = _candle(datetime(2026, 1, 1, 9, 0), high=120.0, low=90.0)
    future_candle = _candle(datetime(2026, 1, 1, 11, 0), high=108.0, low=96.0)

    BacktestEngine(
        trade_plans=(trade_plan,),
        candles=(old_candle, future_candle),
        trade_execution_simulator=simulator,
    ).run()

    assert simulator.received_candles == (future_candle,)


class StaticWinningTradeExecutionSimulator:
    def simulate(self, trade_plan, candles):
        return TradeResult(
            signal_type=trade_plan.signal_type,
            entry_price=trade_plan.entry_price,
            exit_price=trade_plan.take_profit,
            stop_loss=trade_plan.stop_loss,
            take_profit=trade_plan.take_profit,
            position_size=trade_plan.position_size,
            pnl=100.0,
            risk_multiple=2.0,
            opened_at=trade_plan.created_at,
            closed_at=datetime(2026, 1, 1, 11, 0),
        )


def test_backtest_engine_accepts_custom_trade_execution_simulator():
    trade_plan = _long_trade_plan(
        created_at=datetime(2026, 1, 1, 9, 0),
    )

    result = BacktestEngine(
        trade_plans=(trade_plan,),
        candles=(),
        trade_execution_simulator=StaticWinningTradeExecutionSimulator(),
    ).run()

    assert len(result.trades) == 1
    assert result.performance_summary.total_pnl == 100.0

