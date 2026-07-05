"""
Transaction Cost Profile

Defines configurable brokerage, tax, and fee rates for backtesting.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionCostProfile:
    """
    Immutable transaction cost profile.

    Rates are decimals. Example:
        0.00025 means 0.025%.

    Brokerage supports two modes:
        1. Fixed brokerage per order.
        2. Percentage brokerage with optional cap per order.

    When brokerage_rate is greater than zero, percentage brokerage is used.
    When brokerage_cap_per_order is greater than zero, brokerage is capped.
    """

    brokerage_per_order: float = 0.0
    brokerage_rate: float = 0.0
    brokerage_cap_per_order: float = 0.0
    stt_rate: float = 0.0
    exchange_transaction_charge_rate: float = 0.0
    sebi_charge_rate: float = 0.0
    stamp_duty_rate: float = 0.0
    clearing_charge_rate: float = 0.0
    investor_protection_fund_rate: float = 0.0
    gst_rate: float = 0.0

    def __post_init__(self):
        """
        Validate profile values.
        """
        values = {
            "brokerage_per_order": self.brokerage_per_order,
            "brokerage_rate": self.brokerage_rate,
            "brokerage_cap_per_order": self.brokerage_cap_per_order,
            "stt_rate": self.stt_rate,
            "exchange_transaction_charge_rate": self.exchange_transaction_charge_rate,
            "sebi_charge_rate": self.sebi_charge_rate,
            "stamp_duty_rate": self.stamp_duty_rate,
            "clearing_charge_rate": self.clearing_charge_rate,
            "investor_protection_fund_rate": self.investor_protection_fund_rate,
            "gst_rate": self.gst_rate,
        }

        for field_name, value in values.items():
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative")
