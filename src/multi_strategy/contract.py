"""Common deterministic Python contract for registered HQE strategies."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from src.multi_strategy.decision import StrategyDecision
    from src.strategy.strategy_context import StrategyContext
    from src.strategy.trade_signal import TradeSignal


@runtime_checkable
class StrategyImplementation(Protocol):
    """A reviewed strategy implementation.

    Implementations must be deterministic and side-effect free. They must not
    place orders, call a broker, mutate product runtime state, or perform
    network/filesystem writes from ``generate``.
    """

    def generate(
        self,
        context: "StrategyContext",
    ) -> tuple["TradeSignal", ...]:
        """Return immutable LONG/SHORT/NEUTRAL trade signals."""


class StrategyFactory(Protocol):
    """Factory bound to a reviewed implementation key."""

    def __call__(
        self,
        parameters: Mapping[str, Any],
    ) -> StrategyImplementation:
        """Build a strategy from a validated parameter snapshot."""


@runtime_checkable
class ForwardPaperCompatibilityAdapter(Protocol):
    """Temporary adapter contract for verified file-based paper logic.

    This protocol exists only for compatibility validation before the common
    normalized backtest/forward context is introduced.
    """

    def evaluate_from_csv(
        self,
        index_csv: "Path",
        premium_csv: "Path",
        er20: float | None,
    ) -> "StrategyDecision":
        """Return one structured decision while preserving legacy evidence."""
