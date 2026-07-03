"""
Fair Value Gap Config

Configuration for Fair Value Gap detection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FairValueGapConfig:
    """
    Immutable configuration for Fair Value Gap detection.
    """

    enabled: bool = True
    minimum_gap_size: float = 0.0
    require_body_imbalance: bool = False
    allow_wick_gap: bool = True


DEFAULT_FAIR_VALUE_GAP_CONFIG = FairValueGapConfig()