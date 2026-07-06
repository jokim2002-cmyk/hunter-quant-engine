"""
Option Buy Plan to Paper Order Adapter

Fake/local paper trading adapter only. No real orders. No live market data.
Not a profitability claim.
"""

from __future__ import annotations

from datetime import datetime

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import (
    OptionBuyTradePlanStatus,
)


def create_paper_order_request_from_option_buy_plan(
    plan: OptionBuyTradePlan,
    *,
    created_at: datetime | None = None,
) -> PaperOrderRequest:
    """
    Convert an approved option-buy trade plan into a fake/local paper order request.
    """
    if plan.status is not OptionBuyTradePlanStatus.APPROVED:
        raise ValueError("only approved option-buy trade plans can be converted")

    symbol = plan.entry.contract.symbol
    if not symbol.strip():
        raise ValueError("symbol is required")

    quantity = plan.quantity
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    planned_entry_price = plan.entry_premium
    if planned_entry_price <= 0:
        raise ValueError("planned_entry_price must be greater than 0")

    request_created_at = created_at or plan.signal.created_at

    plan_id = ""
    for attribute_name in ("plan_id", "signal_id"):
        candidate = getattr(plan, attribute_name, "")
        if isinstance(candidate, str) and candidate.strip():
            plan_id = candidate.strip()
            break

    signal_identifier = getattr(plan.signal, "signal_id", "")
    if not plan_id and isinstance(signal_identifier, str) and signal_identifier.strip():
        plan_id = signal_identifier.strip()

    return PaperOrderRequest(
        symbol=symbol,
        quantity=quantity,
        planned_entry_price=planned_entry_price,
        created_at=request_created_at,
        plan_id=plan_id,
    )
