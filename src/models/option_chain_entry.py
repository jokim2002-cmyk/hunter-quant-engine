"""
Option Chain Entry

Core broker-agnostic model for one option chain row.
"""

from dataclasses import dataclass

from src.models.option_contract import OptionContract
from src.models.option_greeks import OptionGreeks
from src.models.option_type import OptionType


@dataclass(frozen=True)
class OptionChainEntry:
    """
    Represents market data for one option contract in an option chain.
    """

    contract: OptionContract
    last_traded_price: float
    bid_price: float | None = None
    ask_price: float | None = None
    volume: int = 0
    open_interest: int = 0
    greeks: OptionGreeks | None = None

    def __post_init__(self):
        """
        Validate option chain market data.
        """
        if self.last_traded_price <= 0:
            raise ValueError("last_traded_price must be greater than 0")

        if self.bid_price is not None and self.bid_price < 0:
            raise ValueError("bid_price must not be negative")

        if self.ask_price is not None and self.ask_price < 0:
            raise ValueError("ask_price must not be negative")

        if (
            self.bid_price is not None
            and self.ask_price is not None
            and self.ask_price < self.bid_price
        ):
            raise ValueError("ask_price must be greater than or equal to bid_price")

        if self.volume < 0:
            raise ValueError("volume must not be negative")

        if self.open_interest < 0:
            raise ValueError("open_interest must not be negative")

    @property
    def option_type(self) -> OptionType:
        """
        Return CE or PE option type.
        """
        return self.contract.option_type

    @property
    def has_bid_ask_quote(self) -> bool:
        """
        Return True when both bid and ask are available.
        """
        return self.bid_price is not None and self.ask_price is not None

    @property
    def spread(self) -> float | None:
        """
        Return bid-ask spread when both prices are available.
        """
        if not self.has_bid_ask_quote:
            return None

        return self.ask_price - self.bid_price

    @property
    def mid_price(self) -> float | None:
        """
        Return bid-ask midpoint when both prices are available.
        """
        if not self.has_bid_ask_quote:
            return None

        return (self.bid_price + self.ask_price) / 2

    @property
    def is_call(self) -> bool:
        """
        Return True for CE entries.
        """
        return self.contract.option_type.is_call

    @property
    def is_put(self) -> bool:
        """
        Return True for PE entries.
        """
        return self.contract.option_type.is_put
