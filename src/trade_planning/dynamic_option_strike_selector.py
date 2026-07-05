"""
Dynamic Option Strike Selector

Selects an option chain entry for the first HQE option-buy module.
"""

from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_type import OptionType
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_strike_selection_result import (
    OptionStrikeSelectionRejection,
    OptionStrikeSelectionResult,
)


class DynamicOptionStrikeSelector:
    """
    Selects CE/PE option strikes from an option chain snapshot.

    First version rules:
    - LONG signal maps to CE buy candidates.
    - SHORT signal maps to PE buy candidates.
    - NEUTRAL signal does not create an option selection.
    - Selection chooses the strike closest to underlying spot price.
    """

    def select(
        self,
        signal: TradeSignal,
        snapshot: OptionChainSnapshot,
    ) -> OptionStrikeSelectionResult:
        """
        Select an option chain entry for a strategy signal.
        """
        target_option_type = self._target_option_type(signal.signal_type)

        if target_option_type is None:
            return OptionStrikeSelectionResult(
                signal=signal,
                selected_entry=None,
                selected_reason=(
                    "Neutral signal does not map to CE or PE option-buy selection"
                ),
                rejected_entries=tuple(
                    OptionStrikeSelectionRejection(
                        entry=entry,
                        reason="Neutral signal does not allow option-buy selection",
                    )
                    for entry in snapshot.entries
                ),
            )

        matching_entries = tuple(
            entry for entry in snapshot.entries if entry.option_type == target_option_type
        )

        rejected_entries = [
            OptionStrikeSelectionRejection(
                entry=entry,
                reason=(
                    f"{entry.option_type.value} entry rejected because "
                    f"{signal.signal_type.value} signal requires "
                    f"{target_option_type.value}"
                ),
            )
            for entry in snapshot.entries
            if entry.option_type != target_option_type
        ]

        if not matching_entries:
            return OptionStrikeSelectionResult(
                signal=signal,
                selected_entry=None,
                selected_reason=(
                    f"No {target_option_type.value} entries available for "
                    f"{signal.signal_type.value} signal"
                ),
                rejected_entries=tuple(rejected_entries),
            )

        selected_entry = self._closest_to_underlying(
            entries=matching_entries,
            underlying_price=snapshot.underlying_price,
        )

        rejected_entries.extend(
            OptionStrikeSelectionRejection(
                entry=entry,
                reason=(
                    f"{entry.option_type.value} strike rejected because another "
                    "matching strike is closer to underlying price"
                ),
            )
            for entry in matching_entries
            if entry != selected_entry
        )

        return OptionStrikeSelectionResult(
            signal=signal,
            selected_entry=selected_entry,
            selected_reason=(
                f"Selected {target_option_type.value} strike closest to "
                f"underlying price {snapshot.underlying_price}"
            ),
            rejected_entries=tuple(rejected_entries),
        )

    def _target_option_type(
        self,
        signal_type: SignalType,
    ) -> OptionType | None:
        """
        Map strategy signal direction to CE/PE option type.
        """
        if signal_type == SignalType.LONG:
            return OptionType.CE

        if signal_type == SignalType.SHORT:
            return OptionType.PE

        return None

    def _closest_to_underlying(
        self,
        entries: tuple[OptionChainEntry, ...],
        underlying_price: float,
    ) -> OptionChainEntry:
        """
        Return the option entry whose strike is closest to the underlying price.
        """
        return min(
            entries,
            key=lambda entry: (
                abs(entry.contract.strike_price - underlying_price),
                entry.contract.strike_price,
                entry.contract.symbol,
            ),
        )
