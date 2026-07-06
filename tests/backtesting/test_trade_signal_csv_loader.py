"""
Trade Signal CSV Loader Tests
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.backtesting.option_buy_backtest_scenario_builder import (
    OptionBuyBacktestScenarioBuilder,
)
from src.backtesting.trade_signal_csv_loader import TradeSignalCsvLoader
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType


def _write_csv(tmp_path, content):
    csv_path = tmp_path / "signals.csv"
    csv_path.write_text(content, encoding="utf-8")
    return csv_path


def test_loader_reads_one_signal(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,LONG,STRONG,0.9,breakout
""",
    )

    signals = loader.load_signals(csv_path)

    assert len(signals) == 1
    assert signals[0].signal_type is SignalType.LONG
    assert signals[0].strength is SignalStrength.STRONG
    assert signals[0].confidence == 0.9
    assert signals[0].rationale == ("breakout",)


def test_loader_reads_multiple_signals(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,long,strong,0.9,breakout
2026-07-06T09:20:00,short,weak,0.4,retest
""",
    )

    signals = loader.load_signals(csv_path)

    assert len(signals) == 2
    assert [signal.signal_type for signal in signals] == [SignalType.LONG, SignalType.SHORT]


def test_loader_returns_signals_sorted_by_timestamp(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:20:00,short,weak,0.4,retest
2026-07-06T09:15:00,long,strong,0.9,breakout
""",
    )

    signals = loader.load_signals(csv_path)

    assert [signal.created_at for signal in signals] == [
        datetime(2026, 7, 6, 9, 15),
        datetime(2026, 7, 6, 9, 20),
    ]


def test_loader_parses_long_signal(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,LONG,STRONG,0.9,breakout
""",
    )

    signals = loader.load_signals(csv_path)

    assert signals[0].signal_type is SignalType.LONG


def test_loader_parses_short_signal(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,short,STRONG,0.9,breakout
""",
    )

    signals = loader.load_signals(csv_path)

    assert signals[0].signal_type is SignalType.SHORT


def test_loader_parses_neutral_signal(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,neutral,STRONG,0.9,breakout
""",
    )

    signals = loader.load_signals(csv_path)

    assert signals[0].signal_type is SignalType.NEUTRAL


def test_loader_parses_signal_strength_values(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,long,medium,0.9,breakout
""",
    )

    signals = loader.load_signals(csv_path)

    assert signals[0].strength is SignalStrength.MEDIUM


def test_loader_parses_rationale_when_present(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,long,strong,0.9,breakout
""",
    )

    signals = loader.load_signals(csv_path)

    assert signals[0].rationale == ("breakout",)


def test_loader_handles_blank_rationale(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,long,strong,0.9,
""",
    )

    signals = loader.load_signals(csv_path)

    assert signals[0].rationale == ()


def test_loader_rejects_missing_required_columns(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,confidence,rationale
2026-07-06T09:15:00,long,0.9,breakout
""",
    )

    with pytest.raises(ValueError, match="missing required trade signal CSV columns: signal_strength"):
        loader.load_signals(csv_path)


def test_loader_rejects_empty_csv_data_rows(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
""",
    )

    with pytest.raises(ValueError, match="trade signal CSV contains no rows"):
        loader.load_signals(csv_path)


def test_loader_rejects_invalid_timestamp(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
not-a-date,long,strong,0.9,breakout
""",
    )

    with pytest.raises(ValueError, match="invalid trade signal timestamp at row 2: not-a-date"):
        loader.load_signals(csv_path)


def test_loader_rejects_invalid_signal_type_enum(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,foo,strong,0.9,breakout
""",
    )

    with pytest.raises(ValueError, match="invalid trade signal value at row 2: signal_type"):
        loader.load_signals(csv_path)


def test_loader_rejects_invalid_signal_strength_enum(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,long,foo,0.9,breakout
""",
    )

    with pytest.raises(ValueError, match="invalid trade signal value at row 2: signal_strength"):
        loader.load_signals(csv_path)


def test_loader_rejects_invalid_confidence(tmp_path):
    loader = TradeSignalCsvLoader()
    csv_path = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,long,strong,not-a-number,breakout
""",
    )

    with pytest.raises(ValueError, match="invalid trade signal value at row 2: confidence"):
        loader.load_signals(csv_path)


def test_loaded_signals_can_be_paired_with_snapshots(tmp_path):
    loader = TradeSignalCsvLoader()
    builder = OptionBuyBacktestScenarioBuilder()
    signal_csv = _write_csv(
        tmp_path,
        """timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,long,strong,0.9,breakout
""",
    )
    signals = loader.load_signals(signal_csv)

    scenarios = builder.build_scenarios(signals, [object()])

    assert len(scenarios) == 1


def test_loader_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = Path(__file__).resolve().parents[1] / ".." / "src" / "backtesting" / "trade_signal_csv_loader.py"
    content = source.read_text(encoding="utf-8").lower()

    assert "fyers" not in content
