"""
Swing Configuration

This module stores configuration values for swing detection.

Keeping configuration separate from business logic makes the system:
- cleaner
- easier to tune
- safer to modify
- ready for optimization later
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SwingConfig:
    """
    Configuration for Swing Detection Engine.

    Attributes:
        lookback: Number of candles checked on left and right side.
    """

    lookback: int = 1

    def __post_init__(self) -> None:
        """
        Validate swing configuration after object creation.
        """
        if self.lookback < 1:
            raise ValueError("SwingConfig lookback must be greater than or equal to 1")


DEFAULT_SWING_CONFIG = SwingConfig()