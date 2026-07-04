"""
Strategy Configuration

This module stores strategy-level configuration values.

Detector configs control what market facts are detected.
Strategy configs control how detected facts are converted into signals.

Keeping this separate makes HQE safer to experiment with:
- default behavior stays stable
- strict/balanced/relaxed modes become testable
- future optimization can tune configs without changing strategy logic
"""

from dataclasses import dataclass
from enum import Enum

from src.strategy.signal_strength import SignalStrength


class StrategyMode(Enum):
    """
    Supported SMC strategy behavior modes.
    """

    STRICT = "strict"
    BALANCED = "balanced"
    RELAXED = "relaxed"


@dataclass(frozen=True)
class SMCStrategyConfig:
    """
    Immutable configuration for SMCStrategy.

    Attributes:
        mode: Named strategy behavior mode.
        directional_signal_strength: Strength used for LONG/SHORT signals.
        directional_signal_confidence: Confidence used for LONG/SHORT signals.
        neutral_signal_strength: Strength used for NEUTRAL signals.
        neutral_signal_confidence: Confidence used for NEUTRAL signals.
        emit_neutral_signal: Whether strategy should emit neutral signals when
            no valid directional setup exists.
    """

    mode: StrategyMode | str = StrategyMode.BALANCED
    directional_signal_strength: SignalStrength = SignalStrength.MEDIUM
    directional_signal_confidence: float = 0.75
    neutral_signal_strength: SignalStrength = SignalStrength.WEAK
    neutral_signal_confidence: float = 0.0
    emit_neutral_signal: bool = True

    def __post_init__(self) -> None:
        """
        Validate and normalize strategy configuration.
        """
        object.__setattr__(
            self,
            "mode",
            normalize_strategy_mode(self.mode),
        )

        _validate_confidence(
            value=self.directional_signal_confidence,
            field_name="directional_signal_confidence",
        )
        _validate_confidence(
            value=self.neutral_signal_confidence,
            field_name="neutral_signal_confidence",
        )


def normalize_strategy_mode(
    mode: StrategyMode | str,
) -> StrategyMode:
    """
    Normalize strategy mode input into StrategyMode enum.
    """
    if isinstance(mode, StrategyMode):
        return mode

    try:
        return StrategyMode(str(mode).lower())
    except ValueError as error:
        supported_modes = ", ".join(supported_strategy_mode_names())
        raise ValueError(
            f"Unsupported strategy mode: {mode}. "
            f"Supported modes: {supported_modes}"
        ) from error


def _validate_confidence(
    value: float,
    field_name: str,
) -> None:
    """
    Validate confidence values as decimal values between 0.0 and 1.0.
    """
    if value < 0.0 or value > 1.0:
        raise ValueError(
            f"SMCStrategyConfig {field_name} must be between 0.0 and 1.0"
        )


def supported_strategy_mode_names() -> tuple[str, ...]:
    """
    Return supported strategy mode names for CLI/parser usage.
    """
    return tuple(mode.value for mode in StrategyMode)


STRICT_SMC_STRATEGY_CONFIG = SMCStrategyConfig(
    mode=StrategyMode.STRICT,
    directional_signal_strength=SignalStrength.STRONG,
    directional_signal_confidence=0.9,
    neutral_signal_strength=SignalStrength.WEAK,
    neutral_signal_confidence=0.0,
    emit_neutral_signal=True,
)

BALANCED_SMC_STRATEGY_CONFIG = SMCStrategyConfig(
    mode=StrategyMode.BALANCED,
    directional_signal_strength=SignalStrength.MEDIUM,
    directional_signal_confidence=0.75,
    neutral_signal_strength=SignalStrength.WEAK,
    neutral_signal_confidence=0.0,
    emit_neutral_signal=True,
)

RELAXED_SMC_STRATEGY_CONFIG = SMCStrategyConfig(
    mode=StrategyMode.RELAXED,
    directional_signal_strength=SignalStrength.MEDIUM,
    directional_signal_confidence=0.6,
    neutral_signal_strength=SignalStrength.WEAK,
    neutral_signal_confidence=0.0,
    emit_neutral_signal=True,
)

DEFAULT_SMC_STRATEGY_CONFIG = BALANCED_SMC_STRATEGY_CONFIG


def smc_strategy_config_for_mode(
    mode: StrategyMode | str,
) -> SMCStrategyConfig:
    """
    Return the preset SMCStrategyConfig for a supported mode.
    """
    normalized_mode = normalize_strategy_mode(mode)

    if normalized_mode is StrategyMode.STRICT:
        return STRICT_SMC_STRATEGY_CONFIG

    if normalized_mode is StrategyMode.RELAXED:
        return RELAXED_SMC_STRATEGY_CONFIG

    return BALANCED_SMC_STRATEGY_CONFIG
