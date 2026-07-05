"""
Dynamic Option Strike Selector

Selects an option chain entry for the first HQE option-buy module.
"""

from dataclasses import dataclass

from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_type import OptionType
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_strike_selection_result import (
    OptionStrikeSelectionRejection,
    OptionStrikeSelectionResult,
)


@dataclass(frozen=True)
class OptionLiquidityFilterConfig:
    """
    Defines broker-agnostic liquidity requirements for option strike selection.
    """

    min_volume: int = 0
    min_open_interest: int = 0
    require_bid_ask_quote: bool = False
    max_spread: float | None = None

    def __post_init__(self):
        """
        Validate liquidity filter settings.
        """
        if self.min_volume < 0:
            raise ValueError("min_volume cannot be negative")

        if self.min_open_interest < 0:
            raise ValueError("min_open_interest cannot be negative")

        if self.max_spread is not None and self.max_spread <= 0:
            raise ValueError("max_spread must be greater than 0 when provided")


@dataclass(frozen=True)
class OptionGreekFilterConfig:
    """
    Defines broker-agnostic Greek requirements for option strike selection.
    """

    require_greeks: bool = False
    min_abs_delta: float | None = None
    max_abs_delta: float | None = None
    max_abs_theta: float | None = None
    max_vega: float | None = None
    max_gamma: float | None = None

    def __post_init__(self):
        """
        Validate Greek filter settings.
        """
        if self.min_abs_delta is not None and not 0 < self.min_abs_delta <= 1:
            raise ValueError("min_abs_delta must be greater than 0 and <= 1")

        if self.max_abs_delta is not None and not 0 < self.max_abs_delta <= 1:
            raise ValueError("max_abs_delta must be greater than 0 and <= 1")

        if (
            self.min_abs_delta is not None
            and self.max_abs_delta is not None
            and self.min_abs_delta > self.max_abs_delta
        ):
            raise ValueError("min_abs_delta cannot be greater than max_abs_delta")

        if self.max_abs_theta is not None and self.max_abs_theta <= 0:
            raise ValueError("max_abs_theta must be greater than 0 when provided")

        if self.max_vega is not None and self.max_vega <= 0:
            raise ValueError("max_vega must be greater than 0 when provided")

        if self.max_gamma is not None and self.max_gamma <= 0:
            raise ValueError("max_gamma must be greater than 0 when provided")


class DynamicOptionStrikeSelector:
    """
    Selects CE/PE option strikes from an option chain snapshot.

    First version rules:
    - LONG signal maps to CE buy candidates.
    - SHORT signal maps to PE buy candidates.
    - NEUTRAL signal does not create an option selection.
    - Liquidity filters are applied before closest-strike selection.
    - Greek filters are applied after liquidity filters.
    - Selection chooses the liquid strike closest to underlying spot price.
    """

    def __init__(
        self,
        liquidity_config: OptionLiquidityFilterConfig | None = None,
        greek_config: OptionGreekFilterConfig | None = None,
    ):
        """
        Initialize selector with liquidity and Greek rules.
        """
        self.liquidity_config = liquidity_config or OptionLiquidityFilterConfig()
        self.greek_config = greek_config or OptionGreekFilterConfig()

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

        liquid_entries = []
        for entry in matching_entries:
            rejection_reason = self._liquidity_rejection_reason(entry)
            if rejection_reason is None:
                liquid_entries.append(entry)
            else:
                rejected_entries.append(
                    OptionStrikeSelectionRejection(
                        entry=entry,
                        reason=rejection_reason,
                    )
                )

        if not liquid_entries:
            return OptionStrikeSelectionResult(
                signal=signal,
                selected_entry=None,
                selected_reason=(
                    f"No {target_option_type.value} entries passed liquidity filters "
                    f"for {signal.signal_type.value} signal"
                ),
                rejected_entries=tuple(rejected_entries),
            )

        greek_checked_entries = []
        for entry in liquid_entries:
            rejection_reason = self._greek_rejection_reason(entry)
            if rejection_reason is None:
                greek_checked_entries.append(entry)
            else:
                rejected_entries.append(
                    OptionStrikeSelectionRejection(
                        entry=entry,
                        reason=rejection_reason,
                    )
                )

        if not greek_checked_entries:
            return OptionStrikeSelectionResult(
                signal=signal,
                selected_entry=None,
                selected_reason=(
                    f"No {target_option_type.value} entries passed Greek filters "
                    f"for {signal.signal_type.value} signal"
                ),
                rejected_entries=tuple(rejected_entries),
            )

        selected_entry = self._closest_to_underlying(
            entries=tuple(greek_checked_entries),
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
            for entry in greek_checked_entries
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

    def _liquidity_rejection_reason(
        self,
        entry: OptionChainEntry,
    ) -> str | None:
        """
        Return a clear liquidity rejection reason, or None when entry passes.
        """
        if entry.volume < self.liquidity_config.min_volume:
            return (
                f"{entry.option_type.value} strike {entry.contract.strike_price} "
                f"rejected because volume below minimum "
                f"{self.liquidity_config.min_volume}"
            )

        if entry.open_interest < self.liquidity_config.min_open_interest:
            return (
                f"{entry.option_type.value} strike {entry.contract.strike_price} "
                f"rejected because open interest below minimum "
                f"{self.liquidity_config.min_open_interest}"
            )

        if self.liquidity_config.require_bid_ask_quote and not entry.has_bid_ask_quote:
            return (
                f"{entry.option_type.value} strike {entry.contract.strike_price} "
                "rejected because missing bid/ask quote"
            )

        if (
            self.liquidity_config.max_spread is not None
            and entry.spread is not None
            and entry.spread > self.liquidity_config.max_spread
        ):
            return (
                f"{entry.option_type.value} strike {entry.contract.strike_price} "
                f"rejected because spread above maximum "
                f"{self.liquidity_config.max_spread}"
            )

        return None

    def _greek_rejection_reason(
        self,
        entry: OptionChainEntry,
    ) -> str | None:
        """
        Return a clear Greek rejection reason, or None when entry passes.
        """
        greeks = entry.greeks

        if self.greek_config.require_greeks and greeks is None:
            return (
                f"{entry.option_type.value} strike {entry.contract.strike_price} "
                "rejected because Greeks are missing"
            )

        if self.greek_config.min_abs_delta is not None:
            if greeks is None or greeks.delta is None:
                return (
                    f"{entry.option_type.value} strike {entry.contract.strike_price} "
                    "rejected because delta is missing"
                )

            if abs(greeks.delta) < self.greek_config.min_abs_delta:
                return (
                    f"{entry.option_type.value} strike {entry.contract.strike_price} "
                    f"rejected because absolute delta below minimum "
                    f"{self.greek_config.min_abs_delta}"
                )

        if self.greek_config.max_abs_delta is not None:
            if greeks is None or greeks.delta is None:
                return (
                    f"{entry.option_type.value} strike {entry.contract.strike_price} "
                    "rejected because delta is missing"
                )

            if abs(greeks.delta) > self.greek_config.max_abs_delta:
                return (
                    f"{entry.option_type.value} strike {entry.contract.strike_price} "
                    f"rejected because absolute delta above maximum "
                    f"{self.greek_config.max_abs_delta}"
                )

        if self.greek_config.max_abs_theta is not None:
            if greeks is None or greeks.theta is None:
                return (
                    f"{entry.option_type.value} strike {entry.contract.strike_price} "
                    "rejected because theta is missing"
                )

            if abs(greeks.theta) > self.greek_config.max_abs_theta:
                return (
                    f"{entry.option_type.value} strike {entry.contract.strike_price} "
                    f"rejected because absolute theta above maximum "
                    f"{self.greek_config.max_abs_theta}"
                )

        if self.greek_config.max_vega is not None:
            if greeks is None or greeks.vega is None:
                return (
                    f"{entry.option_type.value} strike {entry.contract.strike_price} "
                    "rejected because vega is missing"
                )

            if greeks.vega > self.greek_config.max_vega:
                return (
                    f"{entry.option_type.value} strike {entry.contract.strike_price} "
                    f"rejected because vega above maximum {self.greek_config.max_vega}"
                )

        if self.greek_config.max_gamma is not None:
            if greeks is None or greeks.gamma is None:
                return (
                    f"{entry.option_type.value} strike {entry.contract.strike_price} "
                    "rejected because gamma is missing"
                )

            if greeks.gamma > self.greek_config.max_gamma:
                return (
                    f"{entry.option_type.value} strike {entry.contract.strike_price} "
                    f"rejected because gamma above maximum "
                    f"{self.greek_config.max_gamma}"
                )

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
