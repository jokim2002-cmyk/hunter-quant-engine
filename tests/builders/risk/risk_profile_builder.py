"""
Risk Profile Builder

Test builder for creating RiskProfile objects.
"""

from src.risk.risk_profile import RiskProfile


class RiskProfileBuilder:
    """
    Builder for RiskProfile test objects.
    """

    def __init__(self):
        self._account_balance = 10000.0
        self._risk_per_trade = 0.01
        self._reward_to_risk = 2.0

    def with_account_balance(self, account_balance: float):
        self._account_balance = account_balance
        return self

    def with_risk_per_trade(self, risk_per_trade: float):
        self._risk_per_trade = risk_per_trade
        return self

    def with_reward_to_risk(self, reward_to_risk: float):
        self._reward_to_risk = reward_to_risk
        return self

    def build(self):
        return RiskProfile(
            account_balance=self._account_balance,
            risk_per_trade=self._risk_per_trade,
            reward_to_risk=self._reward_to_risk,
        )
