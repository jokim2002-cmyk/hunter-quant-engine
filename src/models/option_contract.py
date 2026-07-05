"""
Option Contract

Core immutable model for a NIFTY option contract.
"""

from dataclasses import dataclass
from datetime import date

from src.models.option_type import OptionType


@dataclass(frozen=True)
class OptionContract:
    """
    Represents an option contract selected or evaluated by HQE.

    This model is broker-agnostic. Broker-specific symbols and formatting
    must stay outside core option planning logic.
    """

    underlying_symbol: str
    expiry_date: date
    strike_price: float
    option_type: OptionType
    lot_size: int
    symbol: str

    def __post_init__(self):
        """
        Validate option contract fields.
        """
        if not self.underlying_symbol.strip():
            raise ValueError("underlying_symbol is required")

        if self.strike_price <= 0:
            raise ValueError("strike_price must be greater than 0")

        if self.lot_size <= 0:
            raise ValueError("lot_size must be greater than 0")

        if not self.symbol.strip():
            raise ValueError("symbol is required")

    def quantity_for_lots(
        self,
        lots: int,
    ) -> int:
        """
        Return total quantity for a number of lots.
        """
        if lots <= 0:
            raise ValueError("lots must be greater than 0")

        return self.lot_size * lots
