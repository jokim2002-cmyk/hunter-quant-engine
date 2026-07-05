"""
Option Greeks

Core broker-agnostic model for option Greeks.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OptionGreeks:
    """
    Represents option Greeks and implied volatility.

    Values may be None when the data provider does not supply them.
    HQE must not pretend missing Greeks were checked.
    """

    delta: float | None = None
    theta: float | None = None
    vega: float | None = None
    gamma: float | None = None
    implied_volatility: float | None = None

    def __post_init__(self):
        """
        Validate Greeks when values are provided.
        """
        if self.delta is not None and not -1.0 <= self.delta <= 1.0:
            raise ValueError("delta must be between -1 and 1")

        if self.vega is not None and self.vega < 0:
            raise ValueError("vega must not be negative")

        if self.gamma is not None and self.gamma < 0:
            raise ValueError("gamma must not be negative")

        if self.implied_volatility is not None and self.implied_volatility < 0:
            raise ValueError("implied_volatility must not be negative")

    @property
    def is_complete(self) -> bool:
        """
        Return True when all Greeks and IV are available.
        """
        return all(
            value is not None
            for value in (
                self.delta,
                self.theta,
                self.vega,
                self.gamma,
                self.implied_volatility,
            )
        )

    @property
    def has_missing_values(self) -> bool:
        """
        Return True when any Greek or IV value is missing.
        """
        return not self.is_complete
