"""
Fixed Risk Position Sizer

Calculates position size using fixed account risk.
"""

from src.risk.position_sizing.base_position_sizer import BasePositionSizer
from src.risk.risk_profile import RiskProfile


class FixedRiskPositionSizer(BasePositionSizer):
    """
    Calculates position size using:

    risk amount / absolute price risk per unit
    """

    def calculate(
        self,
        risk_profile: RiskProfile,
        entry_price: float,
        stop_loss: float,
    ) -> float:
        """
        Calculate fixed-risk position size.

        Args:
            risk_profile: Immutable risk profile.
            entry_price: Planned trade entry price.
            stop_loss: Planned stop-loss price.

        Returns:
            Position size.
        """
        self._validate_price("entry_price", entry_price)
        self._validate_price("stop_loss", stop_loss)
        self._validate_prices_are_different(entry_price, stop_loss)

        price_risk_per_unit = abs(entry_price - stop_loss)

        return risk_profile.risk_amount() / price_risk_per_unit

    def _validate_price(
        self,
        field_name: str,
        price: float,
    ):
        if price <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")

    def _validate_prices_are_different(
        self,
        entry_price: float,
        stop_loss: float,
    ):
        if entry_price == stop_loss:
            raise ValueError("entry_price and stop_loss cannot be equal.")
