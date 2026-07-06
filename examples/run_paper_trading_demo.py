"""Run a safe local paper trading demo.

This demo is fake/local only.
- It creates a synthetic approved OptionBuyTradePlan.
- It converts it to a PaperOrderRequest.
- It submits the request to PaperTradingSession.
- It closes the open fake paper position locally.
- It shows a short trader-readable paper-only simulated P&L summary.
- It writes detailed local paper report files under reports/paper_trading/.

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
from src.paper_trading.paper_estimated_cost_model import estimate_paper_exit_costs
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.paper_trading_report_writer import write_paper_trading_report
from src.paper_trading.paper_trading_session import PaperTradingSession
from src.paper_trading.paper_trading_session_summary import (
    build_paper_trading_session_summary,
)
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


def run_demo() -> int:
    ts = datetime(2026, 7, 6, 9, 15)
    closed_at = datetime(2026, 7, 6, 9, 30)
    synthetic_exit_price = 135.0

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
    estimated_exit_costs = estimate_paper_exit_costs(quantity=request.quantity)

    session = PaperTradingSession()
    order_record = session.submit_order(request)

    exit_record = session.close_position_with_exit_record(
        symbol=symbol,
        closed_at=closed_at,
        exit_reason=PaperExitReason.MANUAL,
        exit_price=synthetic_exit_price,
        estimated_exit_charges=estimated_exit_costs.estimated_exit_charges,
        estimated_slippage=estimated_exit_costs.estimated_slippage,
    )

    summary = build_paper_trading_session_summary(session)
    report_paths = write_paper_trading_report(session)

    print("fake/local paper trading demo")
    print("synthetic option-buy trade plan")
    print(f"paper trade symbol: {order_record.symbol}")
    print(f"paper trade quantity: {order_record.quantity}")
    print(f"paper entry premium: {order_record.planned_entry_price}")
    print(f"paper simulated exit premium: {synthetic_exit_price}")
    print(f"paper order id: {order_record.order_id}")

    if exit_record is None:
        print("paper close status: not closed")
    else:
        print("paper close status: closed")
        print(f"paper exit id: {exit_record.exit_id}")
        print(f"paper simulated points: {exit_record.simulated_points}")
        print(f"paper simulated gross pnl: {exit_record.simulated_gross_pnl}")
        print(f"paper estimated costs: {exit_record.total_estimated_costs}")
        print(f"paper simulated net pnl: {exit_record.simulated_net_pnl}")

    print(f"paper open positions: {summary.open_positions_count}")
    print(f"paper closed trades: {summary.closed_trades_count}")
    print(f"paper report output dir: {report_paths.output_dir}")
    print(f"paper report text: {report_paths.report_text}")
    print("paper report files are local/generated")
    print("paper pnl is simulation only")
    print("estimated costs are included in net pnl only")
    print("gross pnl excludes costs")
    print("no broker/FYERS")
    print("no live/real market data")
    print("no real orders placed")
    print("not a profitability claim")

    return 0


def main() -> int:
    return run_demo()


if __name__ == "__main__":
    raise SystemExit(main())
