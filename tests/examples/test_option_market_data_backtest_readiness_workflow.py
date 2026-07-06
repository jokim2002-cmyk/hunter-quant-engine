"""Backtest-readiness smoke test for the safe offline demo workflow.

Proves that synthetic/demo CSV files produced by the recording workflow
can be loaded through the existing option-buy backtest loaders and
used with the existing backtest scenario builder.

Synthetic/demo data only. No broker code. No orders placed.
Not live market data. Not a profitability claim.
"""

from datetime import datetime
from pathlib import Path

from examples.record_in_memory_option_market_data import (
    DEMO_SYMBOL,
    run_demo as run_recording_demo,
)
from examples.validate_option_market_data_csv import run_demo as run_validation_demo
from src.backtesting.option_buy_backtest_scenario_builder import (
    OptionBuyBacktestScenarioBuilder,
)
from src.backtesting.option_chain_snapshot_csv_loader import OptionChainSnapshotCsvLoader
from src.backtesting.option_premium_candle_csv_loader import OptionPremiumCandleCsvLoader
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal


def test_demo_csvs_load_through_backtest_loaders_and_scenario_builder(tmp_path):
    # Step 1 — record synthetic CSV files
    assert run_recording_demo(tmp_path) == 0
    snapshot_csv = tmp_path / "demo_snapshots.csv"
    premium_csv = tmp_path / "demo_premiums.csv"
    assert snapshot_csv.exists()
    assert premium_csv.exists()

    # Step 2 — validate
    assert run_validation_demo(snapshot_csv, premium_csv) == 0

    # Step 3 — load snapshot CSV through existing backtest loader
    snapshots = OptionChainSnapshotCsvLoader().load_snapshots(snapshot_csv)
    assert len(snapshots) >= 1
    assert snapshots[0].underlying_symbol == "NIFTY"
    assert any(entry.contract.symbol == DEMO_SYMBOL for entry in snapshots[0].entries)

    # Step 4 — load premium CSV through existing backtest loader
    provider = OptionPremiumCandleCsvLoader().load_provider(premium_csv)
    candles = provider.get_candles_for_symbol(DEMO_SYMBOL)
    assert len(candles) >= 1
    assert candles[0].close == 120.0

    # Step 5 — prove loaded snapshot is compatible with scenario builder
    signal = TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("demo",),
        created_at=datetime(2026, 7, 6, 9, 15),
    )
    scenarios = OptionBuyBacktestScenarioBuilder().build_scenarios(
        [signal], list(snapshots[:1])
    )
    assert len(scenarios) == 1
    assert scenarios[0].signal.signal_type is SignalType.LONG
    assert scenarios[0].snapshot is snapshots[0]


def test_no_broker_code_in_new_workflow_test_and_example_scripts():
    """Guard: recording demo scripts and this test file contain no broker SDK references."""
    forbidden = "fy" + "ers"
    scripts = [
        Path("examples/record_in_memory_option_market_data.py"),
        Path("examples/validate_option_market_data_csv.py"),
        Path("examples/replay_csv_option_market_data.py"),
        Path("tests/examples/test_option_market_data_backtest_readiness_workflow.py"),
    ]
    for script in scripts:
        assert forbidden not in script.read_text(encoding="utf-8").lower(), script
