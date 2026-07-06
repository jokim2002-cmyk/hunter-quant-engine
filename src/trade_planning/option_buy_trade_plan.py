"""
Option Buy Trade Plan

Broker-agnostic model for the first HQE NIFTY option-buy module.
"""

from dataclasses import dataclass

from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan_status import (
    OptionBuyTradePlanStatus,
)


@dataclass(frozen=True)
class OptionBuyTradePlan:
    """
    Represents a broker-agnostic NIFTY CE/PE buy trade plan.
    """

    signal: TradeSignal
    entry: OptionChainEntry
    action: OptionAction
    underlying_price: float
    entry_premium: float
    stop_loss_premium: float
    target_premium: float
    lots: int
    estimated_charges: float
    status: OptionBuyTradePlanStatus
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self):
        """
        Validate and normalize trade plan fields.
        """
        object.__setattr__(self, "rejection_reasons", tuple(self.rejection_reasons))

        if self.action is not OptionAction.BUY:
            raise ValueError("action must be OptionAction.BUY")

        if self.underlying_price <= 0:
            raise ValueError("underlying_price must be greater than 0")

        if self.entry_premium <= 0:
            raise ValueError("entry_premium must be greater than 0")

        if self.stop_loss_premium <= 0:
            raise ValueError("stop_loss_premium must be greater than 0")

        if self.stop_loss_premium >= self.entry_premium:
            raise ValueError("stop_loss_premium must be below entry_premium")

        if self.target_premium <= self.entry_premium:
            raise ValueError("target_premium must be above entry_premium")

        if self.lots <= 0:
            raise ValueError("lots must be greater than 0")

        if self.estimated_charges < 0:
            raise ValueError("estimated_charges cannot be negative")

        if (
            self.status is OptionBuyTradePlanStatus.APPROVED
            and self.rejection_reasons
        ):
            raise ValueError("approved plan should not contain rejection reasons")

        if (
            self.status is OptionBuyTradePlanStatus.REJECTED
            and not self.rejection_reasons
        ):
            raise ValueError("rejected plan should contain at least one rejection reason")

    @property
    def quantity(self) -> int:
        """
        Return total option quantity for the planned lots.
        """
        return self.entry.contract.quantity_for_lots(self.lots)

    @property
    def gross_risk(self) -> float:
        """
        Return premium risk before charges.
        """
        return (self.entry_premium - self.stop_loss_premium) * self.quantity

    @property
    def gross_reward(self) -> float:
        """
        Return premium reward before charges.
        """
        return (self.target_premium - self.entry_premium) * self.quantity

    @property
    def max_loss(self) -> float:
        """
        Return maximum planned loss including estimated charges.
        """
        return self.gross_risk + self.estimated_charges

    @property
    def estimated_net_reward(self) -> float:
        """
        Return target reward after estimated charges.
        """
        return self.gross_reward - self.estimated_charges

    @property
    def risk_reward_ratio(self) -> float:
        """
        Return estimated net reward divided by maximum planned loss.
        """
        return self.estimated_net_reward / self.max_loss
