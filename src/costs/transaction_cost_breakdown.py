"""
Transaction Cost Breakdown

Defines calculated brokerage, tax, fee, and net PnL values for one trade.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionCostBreakdown:
    """
    Immutable transaction cost breakdown for one completed trade.
    """

    gross_pnl: float
    brokerage: float
    stt: float
    exchange_transaction_charge: float
    sebi_charge: float
    stamp_duty: float
    gst: float
    total_charges: float
    net_pnl: float
