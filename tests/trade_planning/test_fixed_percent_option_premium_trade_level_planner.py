"""
Fixed Percent Option Premium Trade Level Planner Tests
"""

from datetime import date

import pytest

from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.trade_planning.fixed_percent_option_premium_trade_level_planner import (
    FixedPercentOptionPremiumTradeLevelPlanner,
)
from src.trade_planning.option_premium_trade_level_config import (
    OptionPremiumTradeLevelConfig,
)
from src.trade_planning.option_premium_trade_levels import OptionPremiumTradeLevels


def _contract():
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol="NIFTY26JUL24200CE",
    )


def _entry(ask_price=101.0):
    return OptionChainEntry(
        contract=_contract(),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=ask_price,
        volume=10000,
        open_interest=50000,
    )


def _levels(**overrides):
    values = {
        "entry": _entry(),
        "entry_premium": 100.0,
        "stop_loss_premium": 75.0,
        "target_premium": 150.0,
        "premium_source": "ask_price",
    }
    values.update(overrides)
    return OptionPremiumTradeLevels(**values)


def test_config_stores_valid_percentages():
    config = OptionPremiumTradeLevelConfig(
        stop_loss_percent=0.25,
        target_percent=0.5,
    )

    assert config.stop_loss_percent == 0.25
    assert config.target_percent == 0.5


@pytest.mark.parametrize("stop_loss_percent", (0, -0.1, 1, 1.1))
def test_config_rejects_invalid_stop_loss_percent(stop_loss_percent):
    with pytest.raises(
        ValueError,
        match="stop_loss_percent must be greater than 0 and less than 1",
    ):
        OptionPremiumTradeLevelConfig(
            stop_loss_percent=stop_loss_percent,
            target_percent=0.5,
        )


@pytest.mark.parametrize("target_percent", (0, -0.1))
def test_config_rejects_invalid_target_percent(target_percent):
    with pytest.raises(ValueError, match="target_percent must be greater than 0"):
        OptionPremiumTradeLevelConfig(
            stop_loss_percent=0.25,
            target_percent=target_percent,
        )


def test_levels_stores_fields():
    entry = _entry()

    levels = _levels(entry=entry)

    assert levels.entry == entry
    assert levels.entry_premium == 100.0
    assert levels.stop_loss_premium == 75.0
    assert levels.target_premium == 150.0
    assert levels.premium_source == "ask_price"


def test_levels_validates_entry_premium():
    with pytest.raises(ValueError, match="entry_premium must be greater than 0"):
        _levels(entry_premium=0)


def test_levels_validates_stop_loss_premium():
    with pytest.raises(
        ValueError,
        match="stop_loss_premium must be greater than 0",
    ):
        _levels(stop_loss_premium=0)


def test_levels_validates_stop_loss_below_entry():
    with pytest.raises(
        ValueError,
        match="stop_loss_premium must be below entry_premium",
    ):
        _levels(stop_loss_premium=100.0)


def test_levels_validates_target_above_entry():
    with pytest.raises(
        ValueError,
        match="target_premium must be above entry_premium",
    ):
        _levels(target_premium=100.0)


def test_levels_validates_premium_source():
    with pytest.raises(ValueError, match="premium_source is required"):
        _levels(premium_source="")


def test_levels_calculates_risk_per_unit():
    assert _levels().risk_per_unit == 25.0


def test_levels_calculates_reward_per_unit():
    assert _levels().reward_per_unit == 50.0


def test_levels_calculates_reward_to_risk():
    assert _levels().reward_to_risk == 2.0


def test_planner_uses_ask_price_when_available():
    planner = FixedPercentOptionPremiumTradeLevelPlanner(
        config=OptionPremiumTradeLevelConfig(
            stop_loss_percent=0.25,
            target_percent=0.5,
        )
    )

    levels = planner.plan(_entry(ask_price=101.0))

    assert levels.entry_premium == 101.0
    assert levels.premium_source == "ask_price"


def test_planner_falls_back_to_last_traded_price_when_ask_price_missing():
    planner = FixedPercentOptionPremiumTradeLevelPlanner(
        config=OptionPremiumTradeLevelConfig(
            stop_loss_percent=0.25,
            target_percent=0.5,
        )
    )

    levels = planner.plan(_entry(ask_price=None))

    assert levels.entry_premium == 100.0
    assert levels.premium_source == "last_traded_price"


def test_planner_calculates_stop_loss_premium():
    planner = FixedPercentOptionPremiumTradeLevelPlanner(
        config=OptionPremiumTradeLevelConfig(
            stop_loss_percent=0.25,
            target_percent=0.5,
        )
    )

    levels = planner.plan(_entry(ask_price=100.0))

    assert levels.stop_loss_premium == 75.0


def test_planner_calculates_target_premium():
    planner = FixedPercentOptionPremiumTradeLevelPlanner(
        config=OptionPremiumTradeLevelConfig(
            stop_loss_percent=0.25,
            target_percent=0.5,
        )
    )

    levels = planner.plan(_entry(ask_price=100.0))

    assert levels.target_premium == 150.0
