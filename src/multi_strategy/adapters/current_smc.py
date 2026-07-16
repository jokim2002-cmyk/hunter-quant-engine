"""Compatibility adapter for HQE's current bidirectional SMC paper logic.

This adapter delegates to the verified current implementation. It does not
replace, fork, or modify the canonical runtime.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts import hqe_smc_live_direction as legacy_smc

from src.multi_strategy.decision import StrategyDecision
from src.multi_strategy.errors import ManifestValidationError
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    ParameterSpec,
    StrategyManifest,
)

CURRENT_SMC_STRATEGY_ID = "hqe_current_smc_compatibility"
CURRENT_SMC_STRATEGY_VERSION = "1.0.0"
CURRENT_SMC_IMPLEMENTATION_KEY = (
    "hqe.reviewed.current_smc_compatibility_v1"
)


def current_smc_manifest() -> StrategyManifest:
    """Return the reviewed manifest for the protected current strategy."""

    return StrategyManifest(
        strategy_id=CURRENT_SMC_STRATEGY_ID,
        display_name="Current SMC Bidirectional Compatibility",
        strategy_version=CURRENT_SMC_STRATEGY_VERSION,
        description=(
            "Compatibility wrapper around the verified current "
            "LONG-to-CE, SHORT-to-PE paper strategy path."
        ),
        implementation_key=CURRENT_SMC_IMPLEMENTATION_KEY,
        supported_instruments=("NIFTY_INDEX_OPTION_BUY",),
        required_timeframe="5m",
        required_data_columns=(
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "option_symbol",
            "ltp",
            "dte",
        ),
        warmup_bars=20,
        parameters=(
            ParameterSpec(
                name="er20_min",
                value_type="number",
                default=0.30,
                minimum=0.30,
                maximum=0.30,
                description=(
                    "Fixed compatibility threshold used by the current "
                    "verified implementation."
                ),
            ),
            ParameterSpec(
                name="minimum_dte",
                value_type="integer",
                default=1,
                minimum=0,
                maximum=30,
            ),
            ParameterSpec(
                name="minimum_ltp",
                value_type="number",
                default=20.0,
                minimum=0.0,
            ),
            ParameterSpec(
                name="maximum_ltp",
                value_type="number",
                default=200.0,
                minimum=0.0,
            ),
            ParameterSpec(
                name="stop_loss_percent",
                value_type="number",
                default=0.40,
                minimum=0.0,
                maximum=1.0,
            ),
            ParameterSpec(
                name="target_percent",
                value_type="number",
                default=1.20,
                minimum=0.0,
            ),
        ),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    ).require_valid()


def _parameters_hash(parameters: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(parameters),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _reason_tokens(reason_text: str) -> tuple[str, ...]:
    return tuple(
        token.strip()
        for token in str(reason_text).split(";")
        if token.strip()
    )


def _canonical_signal(
    raw: Mapping[str, Any],
    *,
    fallback_to_legacy: bool,
) -> str:
    if fallback_to_legacy:
        return "NEUTRAL"
    decision = str(raw.get("decision", "NEUTRAL")).upper()
    return decision if decision in CANONICAL_SIGNALS else "NEUTRAL"


class CurrentSmcCompatibilityAdapter:
    """Read-only adapter around ``hqe_smc_live_direction``."""

    manifest = current_smc_manifest()

    def __init__(
        self,
        parameters: Mapping[str, Any] | None = None,
    ) -> None:
        normalized = self.manifest.validate_parameters(parameters)
        if float(normalized["maximum_ltp"]) < float(
            normalized["minimum_ltp"]
        ):
            raise ManifestValidationError(
                ("maximum_ltp must be greater than or equal to minimum_ltp",)
            )
        self.parameters = normalized
        self.parameters_hash = _parameters_hash(normalized)

    @property
    def candidate(self) -> dict[str, Any]:
        """Return the exact candidate keys consumed by the legacy helper."""

        return {
            "min_dte": int(self.parameters["minimum_dte"]),
            "min_last_traded_price": float(
                self.parameters["minimum_ltp"]
            ),
            "max_last_traded_price": float(
                self.parameters["maximum_ltp"]
            ),
            "stop_loss_percent": float(
                self.parameters["stop_loss_percent"]
            ),
            "target_percent": float(
                self.parameters["target_percent"]
            ),
        }

    def evaluate_from_csv(
        self,
        index_csv: Path,
        premium_csv: Path,
        er20: float | None,
    ) -> StrategyDecision:
        """Delegate to the current helper and add structured identity."""

        raw = legacy_smc.evaluate_from_csv(
            Path(index_csv),
            Path(premium_csv),
            self.candidate,
            er20,
        )
        raw_copy = copy.deepcopy(dict(raw))
        fallback = bool(raw_copy.get("fallback_to_legacy", False))
        signal = _canonical_signal(
            raw_copy,
            fallback_to_legacy=fallback,
        )
        option_side = str(
            raw_copy.get(
                "side",
                CANONICAL_OPTION_MAPPING[signal],
            )
        ).upper()
        if option_side not in set(CANONICAL_OPTION_MAPPING.values()):
            option_side = CANONICAL_OPTION_MAPPING[signal]

        return StrategyDecision(
            strategy_id=self.manifest.strategy_id,
            strategy_version=self.manifest.strategy_version,
            parameters_hash=self.parameters_hash,
            signal=signal,
            option_side=option_side,
            entry_eligible=bool(
                raw_copy.get("signal_generated", False)
            ),
            fallback_to_legacy=fallback,
            reason_text=str(raw_copy.get("reason", "")),
            reason_tokens=_reason_tokens(
                str(raw_copy.get("reason", ""))
            ),
            entry=raw_copy.get("entry"),
            stop_loss=raw_copy.get("stop_loss"),
            target=raw_copy.get("target"),
            latest_price=raw_copy.get("ltp"),
            dte=raw_copy.get("dte"),
            close_change=raw_copy.get("close_change"),
            legacy_payload=raw_copy,
        )


def build_current_smc_adapter(
    parameters: Mapping[str, Any] | None = None,
) -> CurrentSmcCompatibilityAdapter:
    """Reviewed local factory for the current compatibility adapter."""

    return CurrentSmcCompatibilityAdapter(parameters)
