"""
Option Buy Backtest Scenario Builder Tests
"""

from datetime import date, datetime

import pytest

from src.backtesting.option_buy_backtest_runner import OptionBuyBacktestRunner
from src.backtesting.option_buy_backtest_scenario import OptionBuyBacktestScenario
from src.backtesting.option_buy_backtest_scenario_builder import (
    OptionBuyBacktestScenarioBuilder,
)
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal


def _signal(signal_type):
    return TradeSignal(
        signal_type=signal_type,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("test",),
        created_at=datetime(2026, 7, 6, 9, 15),
    )


def _snapshot(timestamp):
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.0,
        timestamp=timestamp,
        entries=(
            OptionChainEntry(
                contract=OptionContract(
                    underlying_symbol="NIFTY",
                    expiry_date=date(2026, 7, 9),
                    strike_price=24200.0,
                    option_type=OptionType.CE,
                    lot_size=65,
                    symbol="ABC",
                ),
                last_traded_price=100.0,
                bid_price=99.0,
                ask_price=101.0,
                volume=1000,
                open_interest=5000,
            ),
        ),
    )


def test_builder_rejects_empty_signals():
    builder = OptionBuyBacktestScenarioBuilder()

    with pytest.raises(ValueError, match="signals are required"):
        builder.build_scenarios([], [])


def test_builder_rejects_empty_snapshots():
    builder = OptionBuyBacktestScenarioBuilder()

    with pytest.raises(ValueError, match="snapshots are required"):
        builder.build_scenarios([_signal(SignalType.LONG)], [])


def test_builder_rejects_length_mismatch():
    builder = OptionBuyBacktestScenarioBuilder()

    with pytest.raises(ValueError, match="signals and snapshots must have the same length"):
        builder.build_scenarios([_signal(SignalType.LONG)], [_snapshot(datetime(2026, 7, 6, 9, 15)), _snapshot(datetime(2026, 7, 6, 9, 20))])


def test_builder_creates_one_scenario():
    builder = OptionBuyBacktestScenarioBuilder()

    scenarios = builder.build_scenarios([_signal(SignalType.LONG)], [_snapshot(datetime(2026, 7, 6, 9, 15))])

    assert len(scenarios) == 1
    assert isinstance(scenarios[0], OptionBuyBacktestScenario)
    assert scenarios[0].signal.signal_type is SignalType.LONG


def test_builder_creates_multiple_scenarios():
    builder = OptionBuyBacktestScenarioBuilder()
    signals = [_signal(SignalType.LONG), _signal(SignalType.SHORT)]
    snapshots = [_snapshot(datetime(2026, 7, 6, 9, 15)), _snapshot(datetime(2026, 7, 6, 9, 20))]

    scenarios = builder.build_scenarios(signals, snapshots)

    assert len(scenarios) == 2
    assert [scenario.signal.signal_type for scenario in scenarios] == [SignalType.LONG, SignalType.SHORT]


def test_builder_preserves_order():
    builder = OptionBuyBacktestScenarioBuilder()
    signals = [_signal(SignalType.NEUTRAL), _signal(SignalType.LONG)]
    snapshots = [_snapshot(datetime(2026, 7, 6, 9, 15)), _snapshot(datetime(2026, 7, 6, 9, 20))]

    scenarios = builder.build_scenarios(signals, snapshots)

    assert [scenario.signal.signal_type for scenario in scenarios] == [SignalType.NEUTRAL, SignalType.LONG]
    assert [scenario.snapshot.timestamp for scenario in scenarios] == [
        datetime(2026, 7, 6, 9, 15),
        datetime(2026, 7, 6, 9, 20),
    ]


def test_builder_keeps_long_signal():
    builder = OptionBuyBacktestScenarioBuilder()

    scenarios = builder.build_scenarios([_signal(SignalType.LONG)], [_snapshot(datetime(2026, 7, 6, 9, 15))])

    assert scenarios[0].signal.signal_type is SignalType.LONG


def test_builder_keeps_short_signal():
    builder = OptionBuyBacktestScenarioBuilder()

    scenarios = builder.build_scenarios([_signal(SignalType.SHORT)], [_snapshot(datetime(2026, 7, 6, 9, 15))])

    assert scenarios[0].signal.signal_type is SignalType.SHORT


def test_builder_keeps_neutral_signal():
    builder = OptionBuyBacktestScenarioBuilder()

    scenarios = builder.build_scenarios([_signal(SignalType.NEUTRAL)], [_snapshot(datetime(2026, 7, 6, 9, 15))])

    assert scenarios[0].signal.signal_type is SignalType.NEUTRAL


def test_split_scenarios_rejects_empty_scenarios():
    builder = OptionBuyBacktestScenarioBuilder()

    with pytest.raises(ValueError, match="option buy backtest scenarios are required"):
        builder.split_scenarios([])


def test_split_scenarios_returns_signals_and_snapshots():
    builder = OptionBuyBacktestScenarioBuilder()
    scenarios = [
        OptionBuyBacktestScenario(
            signal=_signal(SignalType.LONG),
            snapshot=_snapshot(datetime(2026, 7, 6, 9, 15)),
        ),
        OptionBuyBacktestScenario(
            signal=_signal(SignalType.SHORT),
            snapshot=_snapshot(datetime(2026, 7, 6, 9, 20)),
        ),
    ]

    signals, snapshots = builder.split_scenarios(scenarios)

    assert tuple(signal.signal_type for signal in signals) == (SignalType.LONG, SignalType.SHORT)
    assert tuple(snapshot.timestamp for snapshot in snapshots) == (
        datetime(2026, 7, 6, 9, 15),
        datetime(2026, 7, 6, 9, 20),
    )


def test_built_scenarios_can_flow_into_runner_with_fake_dependencies():
    builder = OptionBuyBacktestScenarioBuilder()
    scenarios = builder.build_scenarios(
        [_signal(SignalType.LONG)],
        [_snapshot(datetime(2026, 7, 6, 9, 15))],
    )

    class FakePlanner:
        def plan(self, signal, snapshot):
            class BuildResult:
                has_plan = True
                plan = object()
                rejection_reasons = ()
            return BuildResult()

    class FakePremiumBacktester:
        def backtest(self, plan, premium_candles):
            return "ok"

    runner = OptionBuyBacktestRunner(planner=FakePlanner(), premium_backtester=FakePremiumBacktester())
    signals, snapshots = builder.split_scenarios(scenarios)

    summary = runner.run(signals, snapshots, lambda plan: ())

    assert summary.planned_signals == 1
    assert summary.results == ("ok",)


def test_builder_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = __import__("pathlib").Path(__file__).resolve().parents[1] / ".." / "src" / "backtesting" / "option_buy_backtest_scenario_builder.py"
    content = source.read_text(encoding="utf-8").lower()

    assert "fyers" not in content
