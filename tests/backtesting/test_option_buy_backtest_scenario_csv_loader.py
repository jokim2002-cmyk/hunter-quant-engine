"""
Option Buy Backtest Scenario CSV Loader Tests
"""

from datetime import datetime
from pathlib import Path

import pytest

import src.backtesting.option_buy_backtest_scenario_csv_loader as loader_module
from src.backtesting.option_buy_backtest_runner import OptionBuyBacktestRunner
from src.backtesting.option_buy_backtest_scenario import OptionBuyBacktestScenario
from src.backtesting.option_buy_backtest_scenario_csv_loader import (
    OptionBuyBacktestScenarioCsvLoader,
)
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType
from src.strategy.signal_type import SignalType


CSV_HEADER = (
    "snapshot_id,timestamp,signal_type,signal_strength,confidence,"
    "underlying_symbol,underlying_price,expiry_date,strike_price,option_type,"
    "lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,"
    "open_interest,rationale,delta,theta,vega,gamma,implied_volatility"
)


def _write_csv(tmp_path, content):
    csv_path = tmp_path / "option_buy_scenarios.csv"
    csv_path.write_text(content.strip() + "\n", encoding="utf-8")
    return csv_path


def _valid_row(
    snapshot_id="s1",
    timestamp="2026-07-06T09:15:00",
    signal_type="long",
    signal_strength="strong",
    confidence="0.9",
    underlying_symbol="NIFTY",
    underlying_price="24210",
    expiry_date="2026-07-09",
    strike_price="24200",
    option_type="CE",
    lot_size="65",
    option_symbol="NIFTY26JUL24200CE",
    last_traded_price="100",
    bid_price="99",
    ask_price="101",
    volume="10000",
    open_interest="50000",
    rationale="test setup",
    delta="",
    theta="",
    vega="",
    gamma="",
    implied_volatility="",
):
    return (
        f"{snapshot_id},{timestamp},{signal_type},{signal_strength},{confidence},"
        f"{underlying_symbol},{underlying_price},{expiry_date},{strike_price},"
        f"{option_type},{lot_size},{option_symbol},{last_traded_price},{bid_price},"
        f"{ask_price},{volume},{open_interest},{rationale},{delta},{theta},{vega},"
        f"{gamma},{implied_volatility}"
    )


def _valid_csv(*rows):
    return "\n".join((CSV_HEADER, *rows))


def _premium_provider(plan):
    return (
        OptionPremiumCandle(
            timestamp=datetime(2026, 7, 6, 9, 20),
            open=100.0,
            high=170.0,
            low=95.0,
            close=165.0,
        ),
    )


def test_scenario_model_stores_signal_and_snapshot(tmp_path):
    scenario = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(tmp_path, _valid_csv(_valid_row()))
    )[0]

    model = OptionBuyBacktestScenario(
        signal=scenario.signal,
        snapshot=scenario.snapshot,
    )

    assert model.signal == scenario.signal
    assert model.snapshot == scenario.snapshot


def test_loader_reads_one_valid_scenario(tmp_path):
    scenarios = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(tmp_path, _valid_csv(_valid_row()))
    )

    assert len(scenarios) == 1
    assert scenarios[0].snapshot.underlying_symbol == "NIFTY"
    assert len(scenarios[0].snapshot.entries) == 1


def test_loader_groups_multiple_option_entries_into_one_snapshot(tmp_path):
    scenarios = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(
            tmp_path,
            _valid_csv(
                _valid_row(option_symbol="NIFTY26JUL24200CE"),
                _valid_row(
                    strike_price="24200",
                    option_type="PE",
                    option_symbol="NIFTY26JUL24200PE",
                ),
            ),
        )
    )

    assert len(scenarios) == 1
    assert tuple(entry.contract.symbol for entry in scenarios[0].snapshot.entries) == (
        "NIFTY26JUL24200CE",
        "NIFTY26JUL24200PE",
    )


def test_loader_returns_scenarios_sorted_by_timestamp(tmp_path):
    scenarios = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(
            tmp_path,
            _valid_csv(
                _valid_row(snapshot_id="s2", timestamp="2026-07-06T09:20:00"),
                _valid_row(snapshot_id="s1", timestamp="2026-07-06T09:15:00"),
            ),
        )
    )

    assert tuple(scenario.snapshot.timestamp.minute for scenario in scenarios) == (15, 20)


def test_loader_parses_long_signal_and_ce_option(tmp_path):
    scenario = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(tmp_path, _valid_csv(_valid_row(signal_type="LONG", option_type="ce")))
    )[0]

    assert scenario.signal.signal_type == SignalType.LONG
    assert scenario.snapshot.entries[0].option_type == OptionType.CE


def test_loader_parses_short_signal_and_pe_option(tmp_path):
    scenario = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(
            tmp_path,
            _valid_csv(
                _valid_row(
                    signal_type="short",
                    option_type="PE",
                    option_symbol="NIFTY26JUL24200PE",
                )
            ),
        )
    )[0]

    assert scenario.signal.signal_type == SignalType.SHORT
    assert scenario.snapshot.entries[0].option_type == OptionType.PE


def test_loader_supports_blank_bid_price_and_ask_price_as_none(tmp_path):
    entry = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(tmp_path, _valid_csv(_valid_row(bid_price="", ask_price="")))
    )[0].snapshot.entries[0]

    assert entry.bid_price is None
    assert entry.ask_price is None


def test_loader_parses_bid_price_and_ask_price_when_present(tmp_path):
    entry = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(tmp_path, _valid_csv(_valid_row(bid_price="98.5", ask_price="101.5")))
    )[0].snapshot.entries[0]

    assert entry.bid_price == 98.5
    assert entry.ask_price == 101.5


def test_loader_parses_optional_rationale(tmp_path):
    scenario = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(tmp_path, _valid_csv(_valid_row(rationale="breakout setup")))
    )[0]

    assert scenario.signal.rationale == ("breakout setup",)


def test_loader_creates_greeks_when_greek_values_are_present(tmp_path):
    entry = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(
            tmp_path,
            _valid_csv(
                _valid_row(
                    delta="0.45",
                    theta="-8.0",
                    vega="12.0",
                    gamma="0.04",
                    implied_volatility="0.18",
                )
            ),
        )
    )[0].snapshot.entries[0]

    assert entry.greeks.delta == 0.45
    assert entry.greeks.theta == -8.0
    assert entry.greeks.vega == 12.0
    assert entry.greeks.gamma == 0.04
    assert entry.greeks.implied_volatility == 0.18


def test_loader_uses_greeks_none_when_greek_columns_are_blank(tmp_path):
    entry = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(tmp_path, _valid_csv(_valid_row()))
    )[0].snapshot.entries[0]

    assert entry.greeks is None


def test_loader_uses_greeks_none_when_greek_columns_are_missing(tmp_path):
    content = "\n".join(
        (
            CSV_HEADER.replace(",delta,theta,vega,gamma,implied_volatility", ""),
            _valid_row().rsplit(",,,,,", 1)[0],
        )
    )

    entry = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(tmp_path, content)
    )[0].snapshot.entries[0]

    assert entry.greeks is None


def test_loader_rejects_missing_required_columns(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        """
snapshot_id,timestamp,signal_type
s1,2026-07-06T09:15:00,long
""",
    )

    with pytest.raises(
        ValueError,
        match="missing required option buy backtest scenario CSV columns:",
    ):
        OptionBuyBacktestScenarioCsvLoader().load_scenarios(csv_path)


def test_loader_rejects_empty_csv_data_rows(tmp_path):
    csv_path = _write_csv(tmp_path, CSV_HEADER)

    with pytest.raises(
        ValueError,
        match="option buy backtest scenario CSV contains no rows",
    ):
        OptionBuyBacktestScenarioCsvLoader().load_scenarios(csv_path)


def test_loader_rejects_blank_snapshot_id(tmp_path):
    with pytest.raises(ValueError, match="scenario snapshot_id is required"):
        OptionBuyBacktestScenarioCsvLoader().load_scenarios(
            _write_csv(tmp_path, _valid_csv(_valid_row(snapshot_id=" ")))
        )


def test_loader_rejects_invalid_timestamp(tmp_path):
    with pytest.raises(
        ValueError,
        match="invalid scenario timestamp at row 2: not-a-time",
    ):
        OptionBuyBacktestScenarioCsvLoader().load_scenarios(
            _write_csv(tmp_path, _valid_csv(_valid_row(timestamp="not-a-time")))
        )


def test_loader_rejects_invalid_expiry_date(tmp_path):
    with pytest.raises(
        ValueError,
        match="invalid option expiry_date at row 2: bad-date",
    ):
        OptionBuyBacktestScenarioCsvLoader().load_scenarios(
            _write_csv(tmp_path, _valid_csv(_valid_row(expiry_date="bad-date")))
        )


def test_loader_rejects_invalid_numeric_value(tmp_path):
    with pytest.raises(
        ValueError,
        match="invalid option buy backtest scenario value at row 2: confidence",
    ):
        OptionBuyBacktestScenarioCsvLoader().load_scenarios(
            _write_csv(tmp_path, _valid_csv(_valid_row(confidence="bad")))
        )


def test_loader_rejects_invalid_enum_value(tmp_path):
    with pytest.raises(
        ValueError,
        match="invalid option buy backtest scenario value at row 2: signal_type",
    ):
        OptionBuyBacktestScenarioCsvLoader().load_scenarios(
            _write_csv(tmp_path, _valid_csv(_valid_row(signal_type="sideways")))
        )


def test_loader_rejects_inconsistent_metadata_inside_same_snapshot_id(tmp_path):
    with pytest.raises(
        ValueError,
        match="inconsistent scenario snapshot metadata for snapshot_id: s1",
    ):
        OptionBuyBacktestScenarioCsvLoader().load_scenarios(
            _write_csv(
                tmp_path,
                _valid_csv(
                    _valid_row(snapshot_id="s1", underlying_price="24210"),
                    _valid_row(
                        snapshot_id="s1",
                        underlying_price="24211",
                        option_symbol="NIFTY26JUL24300CE",
                        strike_price="24300",
                    ),
                ),
            )
        )


def test_loaded_scenarios_can_feed_option_buy_backtest_runner(tmp_path):
    scenario = OptionBuyBacktestScenarioCsvLoader().load_scenarios(
        _write_csv(tmp_path, _valid_csv(_valid_row(ask_price="100")))
    )[0]

    summary = OptionBuyBacktestRunner().run(
        signals=(scenario.signal,),
        snapshots=(scenario.snapshot,),
        premium_candle_provider=_premium_provider,
    )

    assert summary.planned_signals == 1
    assert summary.completed_trades == 1


def test_loader_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = Path(loader_module.__file__).read_text(encoding="utf-8").lower()

    assert "fyers" not in source
