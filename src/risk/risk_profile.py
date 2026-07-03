"""
Risk Profile Model

Defines immutable account-level risk configuration.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskProfile:
    account_balance: float
    risk_per_trade: float
    reward_to_risk: float

    def __post_init__(self):
        if self.account_balance <= 0:
            raise ValueError("account_balance must be greater than zero.")

        if self.risk_per_trade <= 0:
            raise ValueError("risk_per_trade must be greater than zero.")

        if self.risk_per_trade > 1:
            raise ValueError("risk_per_trade must be less than or equal to 1.")

        if self.reward_to_risk <= 0:
            raise ValueError("reward_to_risk must be greater than zero.")

    def risk_amount(self) -> float:
        """
        Return the maximum account currency amount risked per trade.
        """
        return self.account_balance * self.risk_per_trade
