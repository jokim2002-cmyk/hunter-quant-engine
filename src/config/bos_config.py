"""
BOS Configuration

This module stores configuration values for BOS detection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BOSConfig:
    """
    Configuration for BOS Engine.
    """

    use_close_break: bool = True


DEFAULT_BOS_CONFIG = BOSConfig()
