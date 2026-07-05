"""
Transaction Cost Breakdown

Defines charge breakdown for a completed trade.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionCostBreakdown:
    """
    Immutable transaction cost breakdown.
    """

    gross_pnl: float
    brokerage: float
    stt: float
    exchange_transaction_charge: float
    sebi_charge: float
    stamp_duty: float
    clearing_charge: float
    investor_protection_fund: float
    gst: float
    total_charges: float
    net_pnl: float
