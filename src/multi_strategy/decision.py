"""Structured immutable decision output for HQE multi-strategy adapters."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
)


@dataclass(frozen=True)
class StrategyDecision:
    """One structured strategy decision with legacy compatibility evidence."""

    strategy_id: str
    strategy_version: str
    parameters_hash: str
    signal: str
    option_side: str
    entry_eligible: bool
    fallback_to_legacy: bool
    reason_text: str
    reason_tokens: tuple[str, ...]
    entry: float | None
    stop_loss: float | None
    target: float | None
    latest_price: float | None
    dte: int | None
    close_change: float | None
    legacy_payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.signal not in CANONICAL_SIGNALS:
            raise ValueError(
                f"signal must be one of {CANONICAL_SIGNALS}"
            )
        if self.option_side not in set(
            CANONICAL_OPTION_MAPPING.values()
        ):
            raise ValueError(
                "option_side must be CE_BUY, PE_BUY, or NO_TRADE"
            )
        if self.fallback_to_legacy:
            if self.signal != "NEUTRAL":
                raise ValueError(
                    "legacy fallback must use canonical NEUTRAL signal"
                )
        elif self.option_side != CANONICAL_OPTION_MAPPING[self.signal]:
            raise ValueError(
                "option_side does not match canonical signal mapping"
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready structured decision snapshot."""

        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "parameters_hash": self.parameters_hash,
            "signal": self.signal,
            "option_side": self.option_side,
            "entry_eligible": self.entry_eligible,
            "fallback_to_legacy": self.fallback_to_legacy,
            "reason_text": self.reason_text,
            "reason_tokens": list(self.reason_tokens),
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "latest_price": self.latest_price,
            "dte": self.dte,
            "close_change": self.close_change,
        }

    def to_legacy_payload(self) -> dict[str, Any]:
        """Return a defensive copy of the exact wrapped legacy payload."""

        return copy.deepcopy(dict(self.legacy_payload))
