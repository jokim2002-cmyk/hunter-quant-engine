"""
Strategy to Paper Bridge Tests

Fake/local paper trading only. No broker. No live market data. No real orders.
"""

from datetime import date, datetime
from pathlib import Path

import pytest

from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.paper_trading_session import PaperTradingSession
from src.paper_trading.strategy_to_paper_bridge import (
    StrategyPaperExitInstruction,
    run_strategy_to_paper_bridge,
)
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


_CREATED_AT = datetime(2026, 7, 6, 9, 15)
_CLOSED_AT = datetime(2026, 7, 6, 9, 30)


def _signal(signal_type: SignalType = SignalType.LONG) -> TradeSignal:
    return TradeSignal(
        signal_type=signal_type,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("strategy bridge test signal",),
        created_at=_CREATED_AT,
    )


def _contract(
    *,
    symbol: str = "NIFTY26JUL24200CE",
    option_type: OptionType = OptionType.CE,
) -> OptionContract:
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=option_type,
        lot_size=65,
        symbol=symbol,
    )


def _entry(
    *,
    symbol: str = "NIFTY26JUL24200CE",
    option_type: OptionType = OptionType.CE,
    premium: float = 100.0,
) -> OptionChainEntry:
    return OptionChainEntry(
        contract=_contract(symbol=symbol, option_type=option_type),
        last_traded_price=premium,
        bid_price=premium - 1.0,
        ask_price=premium + 1.0,
        volume=10000,
        open_interest=50000,
    )


def _plan(
    *,
    symbol: str = "NIFTY26JUL24200CE",
    option_type: OptionType = OptionType.CE,
    status: OptionBuyTradePlanStatus = OptionBuyTradePlanStatus.APPROVED,
    rejection_reasons: tuple[str, ...] = (),
    lots: int = 2,
    premium: float = 100.0,
) -> OptionBuyTradePlan:
    return OptionBuyTradePlan(
        signal=_signal(),
        entry=_entry(symbol=symbol, option_type=option_type, premium=premium),
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=premium,
        stop_loss_premium=premium - 30.0,
        target_premium=premium + 60.0,
        lots=lots,
        estimated_charges=40.0,
        status=status,
        rejection_reasons=rejection_reasons,
    )


def test_strategy_to_paper_bridge_submits_approved_plan_and_writes_report(tmp_path):
    result = run_strategy_to_paper_bridge(
        [_plan()],
        output_dir=tmp_path / "reports" / "strategy_to_paper",
        generated_at=_CREATED_AT,
    )

    assert result.submitted_orders_count == 1
    assert result.skipped_plans_count == 0
    assert result.exit_records_count == 0
    assert result.submitted_orders[0].symbol == "NIFTY26JUL24200CE"
    assert result.submitted_orders[0].quantity == 130
    assert result.summary.total_orders == 1
    assert result.summary.open_positions_count == 1
    assert result.report_paths.summary_json.exists()
    assert result.report_paths.orders_json.exists()
    assert result.report_paths.report_text.exists()


def test_strategy_to_paper_bridge_skips_rejected_plan(tmp_path):
    rejected = _plan(
        symbol="NIFTY26JUL24200PE",
        option_type=OptionType.PE,
        status=OptionBuyTradePlanStatus.REJECTED,
        rejection_reasons=("weak setup",),
    )

    result = run_strategy_to_paper_bridge(
        [rejected],
        output_dir=tmp_path / "reports" / "strategy_to_paper",
    )

    assert result.submitted_orders_count == 0
    assert result.skipped_plans_count == 1
    assert result.skipped_plans[0].index == 1
    assert result.skipped_plans[0].symbol == "NIFTY26JUL24200PE"
    assert result.skipped_plans[0].status == "rejected"
    assert result.skipped_plans[0].reason == "weak setup"
    assert result.summary.total_orders == 0


def test_strategy_to_paper_bridge_closes_position_with_exit_instruction(tmp_path):
    result = run_strategy_to_paper_bridge(
        [_plan()],
        exit_instructions=[
            StrategyPaperExitInstruction(
                symbol="NIFTY26JUL24200CE",
                closed_at=_CLOSED_AT,
                exit_reason=PaperExitReason.TARGET,
                exit_price=135.0,
                estimated_exit_charges=10.0,
                estimated_slippage=5.0,
            )
        ],
        output_dir=tmp_path / "reports" / "strategy_to_paper",
    )

    assert result.submitted_orders_count == 1
    assert result.exit_records_count == 1
    assert result.failed_exit_symbols == ()
    assert result.summary.open_positions_count == 0
    assert result.summary.closed_trades_count == 1

    exit_record = result.exit_records[0]
    assert exit_record.symbol == "NIFTY26JUL24200CE"
    assert exit_record.exit_reason is PaperExitReason.TARGET
    assert exit_record.exit_price == 135.0
    assert exit_record.simulated_points == 35.0
    assert exit_record.simulated_gross_pnl == 4550.0
    assert exit_record.total_estimated_costs == 15.0
    assert exit_record.simulated_net_pnl == 4535.0


def test_strategy_to_paper_bridge_records_failed_exit_symbol_when_position_missing(tmp_path):
    result = run_strategy_to_paper_bridge(
        [],
        exit_instructions=[
            StrategyPaperExitInstruction(
                symbol="NIFTY_UNKNOWN",
                closed_at=_CLOSED_AT,
                exit_price=120.0,
            )
        ],
        output_dir=tmp_path / "reports" / "strategy_to_paper",
    )

    assert result.exit_records_count == 0
    assert result.failed_exit_symbols == ("NIFTY_UNKNOWN",)
    assert result.summary.total_orders == 0


def test_strategy_to_paper_bridge_supports_existing_session(tmp_path):
    session = PaperTradingSession()
    existing = run_strategy_to_paper_bridge(
        [_plan(symbol="NIFTY26JUL24200CE")],
        session=session,
        output_dir=tmp_path / "reports" / "first",
    )

    result = run_strategy_to_paper_bridge(
        [_plan(symbol="NIFTY26JUL24300CE", premium=120.0)],
        session=session,
        output_dir=tmp_path / "reports" / "second",
    )

    assert existing.session is session
    assert result.session is session
    assert result.submitted_orders_count == 1
    assert result.summary.total_orders == 2
    assert len(result.session.list_open_positions()) == 2


def test_strategy_to_paper_bridge_writes_empty_report_for_no_plans(tmp_path):
    result = run_strategy_to_paper_bridge(
        [],
        output_dir=tmp_path / "reports" / "empty_strategy_to_paper",
    )

    assert result.submitted_orders == ()
    assert result.skipped_plans == ()
    assert result.exit_records == ()
    assert result.failed_exit_symbols == ()
    assert result.summary.total_orders == 0
    assert result.report_paths.summary_json.exists()


def test_strategy_to_paper_bridge_rejects_output_outside_reports(tmp_path):
    with pytest.raises(ValueError, match="reports/"):
        run_strategy_to_paper_bridge(
            [_plan()],
            output_dir=tmp_path / "strategy_to_paper",
        )


def test_strategy_to_paper_bridge_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/strategy_to_paper_bridge.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
