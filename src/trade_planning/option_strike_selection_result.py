"""
Option Strike Selection Result

Represents the output of dynamic option strike selection.
"""

from dataclasses import dataclass

from src.models.option_chain_entry import OptionChainEntry
from src.strategy.trade_signal import TradeSignal


@dataclass(frozen=True)
class OptionStrikeSelectionRejection:
    """
    Represents one rejected option chain entry and the reason.
    """

    entry: OptionChainEntry
    reason: str

    def __post_init__(self):
        """
        Validate rejection reason.
        """
        if not self.reason.strip():
            raise ValueError("reason is required")


@dataclass(frozen=True)
class OptionStrikeSelectionResult:
    """
    Represents dynamic option strike selection output.
    """

    signal: TradeSignal
    selected_entry: OptionChainEntry | None
    selected_reason: str
    rejected_entries: tuple[OptionStrikeSelectionRejection, ...]

    def __post_init__(self):
        """
        Validate and normalize result fields.
        """
        if not self.selected_reason.strip():
            raise ValueError("selected_reason is required")

        object.__setattr__(
            self,
            "rejected_entries",
            tuple(self.rejected_entries),
        )

    @property
    def has_selection(self) -> bool:
        """
        Return True when a strike was selected.
        """
        return self.selected_entry is not None

    @property
    def rejection_reasons(self) -> tuple[str, ...]:
        """
        Return rejection reasons.
        """
        return tuple(rejection.reason for rejection in self.rejected_entries)
