"""
Option Premium Trade Levels

Broker-agnostic premium entry, stop-loss, and target levels.
"""

from dataclasses import dataclass

from src.models.option_chain_entry import OptionChainEntry


@dataclass(frozen=True)
class OptionPremiumTradeLevels:
    """
    Represents planned option premium levels for a CE/PE buy candidate.
    """

    entry: OptionChainEntry
    entry_premium: float
    stop_loss_premium: float
    target_premium: float
    premium_source: str

    def __post_init__(self):
        """
        Validate option premium levels.
        """
        if self.entry_premium <= 0:
            raise ValueError("entry_premium must be greater than 0")

        if self.stop_loss_premium <= 0:
            raise ValueError("stop_loss_premium must be greater than 0")

        if self.stop_loss_premium >= self.entry_premium:
            raise ValueError("stop_loss_premium must be below entry_premium")

        if self.target_premium <= self.entry_premium:
            raise ValueError("target_premium must be above entry_premium")

        if not self.premium_source.strip():
            raise ValueError("premium_source is required")

    @property
    def risk_per_unit(self) -> float:
        """
        Return premium risk per option unit.
        """
        return self.entry_premium - self.stop_loss_premium

    @property
    def reward_per_unit(self) -> float:
        """
        Return premium reward per option unit.
        """
        return self.target_premium - self.entry_premium

    @property
    def reward_to_risk(self) -> float:
        """
        Return reward-to-risk ratio using premium levels.
        """
        return self.reward_per_unit / self.risk_per_unit
