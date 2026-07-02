"""
CHOCH Configuration

This module stores configuration values for CHOCH detection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CHOCHConfig:
    """
    Configuration for CHOCH Engine.
    """

    use_close_break: bool = True


DEFAULT_CHOCH_CONFIG = CHOCHConfig()
