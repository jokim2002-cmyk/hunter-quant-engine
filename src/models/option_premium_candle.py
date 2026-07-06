"""
Option Premium Candle

Broker-agnostic OHLC candle for an option premium series.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OptionPremiumCandle:
    """
    Represents one option premium OHLC candle.
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0

    def __post_init__(self):
        """
        Validate premium OHLC values.
        """
        prices = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }
        for field_name, value in prices.items():
            if value <= 0:
                raise ValueError(f"{field_name} must be greater than 0")

        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to open, close, and low")

        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to open, close, and high")

        if self.volume < 0:
            raise ValueError("volume must be greater than or equal to 0")
