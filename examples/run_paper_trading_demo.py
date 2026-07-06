"""Run a safe local paper trading demo.

This demo is fake/local only.
- It creates a synthetic approved OptionBuyTradePlan.
- It converts it to a PaperOrderRequest.
- It submits the request to PaperTradingSession.

No broker SDK. No broker platform integration. No live/real market data.

No real orders are placed.
Not a profitability claim.
"""

from __future__ import annotations

from datetime import date, datetime

from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.paper_trading.option_buy_plan_to_paper_order import (
    create_paper_order_request_from_option_buy_plan,
)
from src.paper_trading.paper_trading_session import PaperTradingSession
from src.paper_trading.paper_trading_session_summary import (
    build_paper_trading_session_summary,
)
from src.paper_trading.paper_trading_session_summary import build_paper_trading_session_summary
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


def run_demo() -> int:
    ts = datetime(2026, 7, 6, 9, 15)

    signal = TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("demo synthetic signal",),
        created_at=ts,
    )

    symbol = "NIFTY26JUL24200CE"

    contract = OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol=symbol,
    )

    entry = OptionChainEntry(
        contract=contract,
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10000,
        open_interest=50000,
    )

    plan = OptionBuyTradePlan(
        signal=signal,
        entry=entry,
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=100.0,
        stop_loss_premium=70.0,
        target_premium=160.0,
        lots=2,
        estimated_charges=40.0,
        status=OptionBuyTradePlanStatus.APPROVED,
        rejection_reasons=(),
    )

    request = create_paper_order_request_from_option_buy_plan(plan)

    session = PaperTradingSession()
    record = session.submit_order(request)

    position = session.find_position(symbol)

    qty = session.total_open_quantity(symbol)

    print("fake/local paper trading demo")
    print("synthetic option-buy trade plan")
    print(f"paper order id: {record.order_id}")
    print(f"paper order symbol: {record.symbol}")
    print(f"paper order quantity: {record.quantity}")
    if position is None:
        print("paper position: None")
    else:
        print(f"paper position symbol: {position.symbol}")
        print(f"paper position quantity: {position.quantity}")

    summary = build_paper_trading_session_summary(session)
    print(f"session summary total orders: {summary.total_orders}")
    print(f"session summary open positions: {summary.open_positions_count}")
    print(f"session summary total open quantity: {summary.total_open_quantity}")
    print(f"session summary symbols: {', '.join(summary.symbols)}")

    print("no broker/FYERS")
    print("no live/real market data")
    print("no real orders placed")
    print("not a profitability claim")

    # Basic sanity in the demo output.
    _ = qty

    return 0


def main() -> int:
    return run_demo()


if __name__ == "__main__":
    raise SystemExit(main())



