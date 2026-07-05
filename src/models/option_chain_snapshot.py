"""
Option Chain Snapshot

Core broker-agnostic model for option chain data at a point in time.
"""

from dataclasses import dataclass
from datetime import date, datetime

from src.models.option_chain_entry import OptionChainEntry
from src.models.option_type import OptionType


@dataclass(frozen=True)
class OptionChainSnapshot:
    """
    Represents a NIFTY option chain snapshot for one timestamp.
    """

    underlying_symbol: str
    underlying_price: float
    timestamp: datetime
    entries: tuple[OptionChainEntry, ...]

    def __post_init__(self):
        """
        Validate snapshot and normalize entries to an immutable tuple.
        """
        if not self.underlying_symbol.strip():
            raise ValueError("underlying_symbol is required")

        if self.underlying_price <= 0:
            raise ValueError("underlying_price must be greater than 0")

        object.__setattr__(self, "entries", tuple(self.entries))

        for entry in self.entries:
            if entry.contract.underlying_symbol != self.underlying_symbol:
                raise ValueError(
                    "entry contract underlying_symbol must match snapshot"
                )

    @property
    def calls(self) -> tuple[OptionChainEntry, ...]:
        """
        Return CE entries.
        """
        return self.entries_for_type(OptionType.CE)

    @property
    def puts(self) -> tuple[OptionChainEntry, ...]:
        """
        Return PE entries.
        """
        return self.entries_for_type(OptionType.PE)

    def entries_for_type(
        self,
        option_type: OptionType,
    ) -> tuple[OptionChainEntry, ...]:
        """
        Return entries matching an option type.
        """
        return tuple(
            entry for entry in self.entries if entry.contract.option_type == option_type
        )

    def entries_for_expiry(
        self,
        expiry_date: date,
    ) -> tuple[OptionChainEntry, ...]:
        """
        Return entries matching an expiry date.
        """
        return tuple(
            entry
            for entry in self.entries
            if entry.contract.expiry_date == expiry_date
        )
