"""
Option Premium Candle CSV Loader Tests
"""

from datetime import date, datetime
from pathlib import Path

import pytest

import src.backtesting.option_premium_candle_csv_loader as loader_module
from src.backtesting.in_memory_option_premium_candle_provider import (
    InMemoryOptionPremiumCandleProvider,
)
from src.backtesting.option_premium_candle_csv_loader import (
    OptionPremiumCandleCsvLoader,
)
from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


def _write_csv(tmp_path, content):
    csv_path = tmp_path / "option_premium_candles.csv"
    csv_path.write_text(content.strip() + "\n", encoding="utf-8")
    return csv_path


def _signal():
    return TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("test signal",),
        created_at=datetime(2026, 7, 6, 10, 15),
    )


def _contract(symbol="NIFTY26JUL24200CE"):
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol=symbol,
    )


def _entry(symbol="NIFTY26JUL24200CE"):
    return OptionChainEntry(
        contract=_contract(symbol=symbol),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10000,
        open_interest=50000,
    )


def _approved_plan(symbol="NIFTY26JUL24200CE"):
    return OptionBuyTradePlan(
        signal=_signal(),
        entry=_entry(symbol=symbol),
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=100.0,
        stop_loss_premium=70.0,
        target_premium=160.0,
        lots=1,
        estimated_charges=10.0,
        status=OptionBuyTradePlanStatus.APPROVED,
        rejection_reasons=(),
    )


def test_loader_reads_valid_csv_and_groups_candles_by_symbol(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close,volume
NIFTY26JUL24200CE,2026-07-06T09:15:00,100,110,95,105,1000
NIFTY26JUL24200PE,2026-07-06T09:15:00,90,100,85,95,500
""",
    )

    grouped = OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)

    assert set(grouped) == {"NIFTY26JUL24200CE", "NIFTY26JUL24200PE"}
    assert grouped["NIFTY26JUL24200CE"][0].close == 105.0
    assert grouped["NIFTY26JUL24200PE"][0].volume == 500


def test_loader_sorts_candles_by_timestamp_ascending(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close,volume
NIFTY26JUL24200CE,2026-07-06T09:20:00,105,110,100,108,1000
NIFTY26JUL24200CE,2026-07-06T09:15:00,100,105,95,102,900
""",
    )

    candles = OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)[
        "NIFTY26JUL24200CE"
    ]

    assert candles[0].timestamp == datetime(2026, 7, 6, 9, 15)
    assert candles[1].timestamp == datetime(2026, 7, 6, 9, 20)


def test_loader_supports_timestamp_with_t_separator(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close
NIFTY26JUL24200CE,2026-07-06T09:15:00,100,110,95,105
""",
    )

    candle = OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)[
        "NIFTY26JUL24200CE"
    ][0]

    assert candle.timestamp == datetime(2026, 7, 6, 9, 15)


def test_loader_supports_timestamp_with_space_separator(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close
NIFTY26JUL24200CE,2026-07-06 09:15:00,100,110,95,105
""",
    )

    candle = OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)[
        "NIFTY26JUL24200CE"
    ][0]

    assert candle.timestamp == datetime(2026, 7, 6, 9, 15)


def test_loader_defaults_missing_volume_column_to_zero(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close
NIFTY26JUL24200CE,2026-07-06T09:15:00,100,110,95,105
""",
    )

    candle = OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)[
        "NIFTY26JUL24200CE"
    ][0]

    assert candle.volume == 0


def test_loader_defaults_blank_volume_to_zero(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close,volume
NIFTY26JUL24200CE,2026-07-06T09:15:00,100,110,95,105,
""",
    )

    candle = OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)[
        "NIFTY26JUL24200CE"
    ][0]

    assert candle.volume == 0


def test_loader_ignores_extra_columns(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close,volume,extra
NIFTY26JUL24200CE,2026-07-06T09:15:00,100,110,95,105,1000,ignored
""",
    )

    grouped = OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)

    assert grouped["NIFTY26JUL24200CE"][0].close == 105.0


def test_loader_rejects_missing_required_columns(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low
NIFTY26JUL24200CE,2026-07-06T09:15:00,100,110,95
""",
    )

    with pytest.raises(
        ValueError,
        match="missing required option premium candle CSV columns: close",
    ):
        OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)


def test_loader_rejects_empty_csv_data_rows(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close
""",
    )

    with pytest.raises(ValueError, match="option premium candle CSV contains no rows"):
        OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)


def test_loader_rejects_blank_symbol(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close
 ,2026-07-06T09:15:00,100,110,95,105
""",
    )

    with pytest.raises(ValueError, match="option premium candle symbol is required"):
        OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)


def test_loader_rejects_invalid_timestamp(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close
NIFTY26JUL24200CE,not-a-time,100,110,95,105
""",
    )

    with pytest.raises(ValueError, match="invalid timestamp at row 2: not-a-time"):
        OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)


def test_loader_rejects_invalid_numeric_price(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close
NIFTY26JUL24200CE,2026-07-06T09:15:00,bad,110,95,105
""",
    )

    with pytest.raises(
        ValueError,
        match="invalid option premium candle value at row 2: open",
    ):
        OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)


def test_loader_rejects_invalid_volume(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close,volume
NIFTY26JUL24200CE,2026-07-06T09:15:00,100,110,95,105,bad
""",
    )

    with pytest.raises(
        ValueError,
        match="invalid option premium candle value at row 2: volume",
    ):
        OptionPremiumCandleCsvLoader().load_grouped_candles(csv_path)


def test_load_provider_returns_in_memory_option_premium_candle_provider(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close
NIFTY26JUL24200CE,2026-07-06T09:15:00,100,110,95,105
""",
    )

    provider = OptionPremiumCandleCsvLoader().load_provider(csv_path)

    assert isinstance(provider, InMemoryOptionPremiumCandleProvider)


def test_loaded_provider_returns_candles_for_an_approved_plan_symbol(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
symbol,timestamp,open,high,low,close
NIFTY26JUL24200CE,2026-07-06T09:15:00,100,110,95,105
""",
    )

    provider = OptionPremiumCandleCsvLoader().load_provider(csv_path)

    assert provider(_approved_plan())[0].close == 105.0


def test_loader_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = Path(loader_module.__file__).read_text(encoding="utf-8").lower()

    assert "fyers" not in source
