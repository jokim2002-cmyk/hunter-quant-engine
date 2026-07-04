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

    Brokerage is per order, so a completed round-trip trade applies it twice:
    once for entry and once for exit.
    """

    brokerage_per_order: float = 0.0
    stt_rate: float = 0.0
    exchange_transaction_charge_rate: float = 0.0
    sebi_charge_rate: float = 0.0
    stamp_duty_rate: float = 0.0
    gst_rate: float = 0.0

    def __post_init__(self):
        """
        Validate profile values.
        """
        values = {
            "brokerage_per_order": self.brokerage_per_order,
            "stt_rate": self.stt_rate,
            "exchange_transaction_charge_rate": self.exchange_transaction_charge_rate,
            "sebi_charge_rate": self.sebi_charge_rate,
            "stamp_duty_rate": self.stamp_duty_rate,
            "gst_rate": self.gst_rate,
        }

        for field_name, value in values.items():
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative")
