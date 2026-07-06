"""
Option Buy Backtest Runner Tests
"""

from datetime import date, datetime

import pytest

from src.backtesting.option_buy_backtest_runner import OptionBuyBacktestRunner
from src.backtesting.option_buy_backtest_summary import OptionBuyBacktestSummary
from src.backtesting.option_premium_backtest_exit_reason import (
    OptionPremiumBacktestExitReason,
)
from src.backtesting.option_premium_backtest_result import OptionPremiumBacktestResult
from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_build_result import (
    OptionBuyTradePlanBuildResult,
)
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


def _signal(signal_type=SignalType.LONG):
    return TradeSignal(
        signal_type=signal_type,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("test signal",),
        created_at=datetime(2026, 7, 6, 10, 15),
    )


def _contract():
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol="NIFTY26JUL24200CE",
    )


def _entry():
    return OptionChainEntry(
        contract=_contract(),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10000,
        open_interest=50000,
    )


def _snapshot():
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.0,
        timestamp=datetime(2026, 7, 6, 10, 15),
        entries=(_entry(),),
    )


def _plan(entry_premium=100.0, charges=10.0):
    return OptionBuyTradePlan(
        signal=_signal(),
        entry=_entry(),
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=entry_premium,
        stop_loss_premium=70.0,
        target_premium=160.0,
        lots=1,
        estimated_charges=charges,
        status=OptionBuyTradePlanStatus.APPROVED,
        rejection_reasons=(),
    )


def _result(exit_premium=160.0, charges=10.0):
    return OptionPremiumBacktestResult(
        plan=_plan(charges=charges),
        exit_reason=OptionPremiumBacktestExitReason.TARGET_HIT,
        exit_premium=exit_premium,
        bars_held=1,
        estimated_charges=charges,
    )


def _premium_candles():
    return (
        OptionPremiumCandle(
            timestamp=datetime(2026, 7, 6, 10, 15),
            open=100.0,
            high=160.0,
            low=95.0,
            close=150.0,
        ),
    )


class _ApprovedPlanner:
    def __init__(self, plan=None):
        self._trade_plan = plan or _plan()

    def plan(self, signal, snapshot):
        return OptionBuyTradePlanBuildResult(plan=self._trade_plan)


class _RejectedPlanner:
    def plan(self, signal, snapshot):
        return OptionBuyTradePlanBuildResult(
            plan=None,
            rejection_reasons=("planner rejected setup",),
        )


class _FixedPremiumBacktester:
    def __init__(self, result=None):
        self.result = result or _result()

    def backtest(self, plan, premium_candles):
        return self.result


class _FailingPremiumBacktester:
    def backtest(self, plan, premium_candles):
        raise ValueError("premium backtest failed")


def test_summary_normalizes_tuple_fields():
    result = _result()

    summary = OptionBuyBacktestSummary(
        planned_signals=1,
        rejected_plans=0,
        results=[result],
        rejection_reasons=["reason"],
    )

    assert summary.results == (result,)
    assert summary.rejection_reasons == ("reason",)


@pytest.mark.parametrize(
    "field_name",
    ("planned_signals", "rejected_plans", "failed_backtests"),
)
def test_summary_validates_non_negative_counts(field_name):
    values = {
        "planned_signals": 0,
        "rejected_plans": 0,
        "failed_backtests": 0,
    }
    values[field_name] = -1

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be greater than or equal to 0",
    ):
        OptionBuyBacktestSummary(**values)


def test_summary_calculates_completed_trades():
    assert OptionBuyBacktestSummary(1, 0, results=(_result(),)).completed_trades == 1


def test_summary_calculates_winning_trades():
    summary = OptionBuyBacktestSummary(1, 0, results=(_result(exit_premium=160.0),))

    assert summary.winning_trades == 1


def test_summary_calculates_losing_trades():
    summary = OptionBuyBacktestSummary(1, 0, results=(_result(exit_premium=70.0),))

    assert summary.losing_trades == 1


def test_summary_calculates_breakeven_trades():
    summary = OptionBuyBacktestSummary(
        1,
        0,
        results=(_result(exit_premium=100.0, charges=0.0),),
    )

    assert summary.breakeven_trades == 1


def test_summary_calculates_win_rate():
    summary = OptionBuyBacktestSummary(
        planned_signals=2,
        rejected_plans=0,
        results=(_result(exit_premium=160.0), _result(exit_premium=70.0)),
    )

    assert summary.win_rate == 0.5
    assert OptionBuyBacktestSummary(0, 0).win_rate == 0.0


def test_summary_calculates_total_gross_pnl():
    summary = OptionBuyBacktestSummary(
        planned_signals=2,
        rejected_plans=0,
        results=(_result(exit_premium=160.0), _result(exit_premium=70.0)),
    )

    assert summary.total_gross_pnl == 1950.0


def test_summary_calculates_total_net_pnl():
    summary = OptionBuyBacktestSummary(
        planned_signals=2,
        rejected_plans=0,
        results=(_result(exit_premium=160.0), _result(exit_premium=70.0)),
    )

    assert summary.total_net_pnl == 1930.0


def test_summary_calculates_total_estimated_charges():
    summary = OptionBuyBacktestSummary(
        planned_signals=2,
        rejected_plans=0,
        results=(_result(charges=10.0), _result(charges=20.0)),
    )

    assert summary.total_estimated_charges == 30.0


def test_runner_rejects_empty_signals():
    with pytest.raises(ValueError, match="signals are required"):
        OptionBuyBacktestRunner().run((), (_snapshot(),), lambda plan: _premium_candles())


def test_runner_rejects_empty_snapshots():
    with pytest.raises(ValueError, match="snapshots are required"):
        OptionBuyBacktestRunner().run((_signal(),), (), lambda plan: _premium_candles())


def test_runner_rejects_length_mismatch():
    with pytest.raises(
        ValueError,
        match="signals and snapshots must have the same length",
    ):
        OptionBuyBacktestRunner().run(
            (_signal(), _signal()),
            (_snapshot(),),
            lambda plan: _premium_candles(),
        )


def test_runner_completes_one_approved_trade():
    summary = OptionBuyBacktestRunner(
        planner=_ApprovedPlanner(),
        premium_backtester=_FixedPremiumBacktester(_result()),
    ).run((_signal(),), (_snapshot(),), lambda plan: _premium_candles())

    assert summary.planned_signals == 1
    assert summary.completed_trades == 1
    assert summary.rejected_plans == 0
    assert summary.failed_backtests == 0


def test_runner_handles_rejected_planner_result():
    summary = OptionBuyBacktestRunner(planner=_RejectedPlanner()).run(
        (_signal(),),
        (_snapshot(),),
        lambda plan: _premium_candles(),
    )

    assert summary.completed_trades == 0
    assert summary.rejected_plans == 1
    assert summary.rejection_reasons == ("planner rejected setup",)


def test_runner_handles_premium_candle_provider_failure():
    def _failing_provider(plan):
        raise ValueError("premium candles unavailable")

    summary = OptionBuyBacktestRunner(planner=_ApprovedPlanner()).run(
        (_signal(),),
        (_snapshot(),),
        _failing_provider,
    )

    assert summary.failed_backtests == 1
    assert summary.rejection_reasons == (
        "option premium backtest failed: premium candles unavailable",
    )


def test_runner_handles_premium_backtester_failure():
    summary = OptionBuyBacktestRunner(
        planner=_ApprovedPlanner(),
        premium_backtester=_FailingPremiumBacktester(),
    ).run((_signal(),), (_snapshot(),), lambda plan: _premium_candles())

    assert summary.failed_backtests == 1
    assert summary.rejection_reasons == (
        "option premium backtest failed: premium backtest failed",
    )


def test_runner_processes_multiple_signals_snapshots():
    summary = OptionBuyBacktestRunner(
        planner=_ApprovedPlanner(),
        premium_backtester=_FixedPremiumBacktester(_result()),
    ).run(
        (_signal(), _signal(SignalType.SHORT)),
        (_snapshot(), _snapshot()),
        lambda plan: _premium_candles(),
    )

    assert summary.planned_signals == 2
    assert summary.completed_trades == 2


def test_runner_uses_injected_planner():
    summary = OptionBuyBacktestRunner(planner=_RejectedPlanner()).run(
        (_signal(),),
        (_snapshot(),),
        lambda plan: _premium_candles(),
    )

    assert summary.rejected_plans == 1


def test_runner_uses_injected_premium_backtester():
    result = _result(exit_premium=170.0)
    summary = OptionBuyBacktestRunner(
        planner=_ApprovedPlanner(),
        premium_backtester=_FixedPremiumBacktester(result),
    ).run((_signal(),), (_snapshot(),), lambda plan: _premium_candles())

    assert summary.results == (result,)
