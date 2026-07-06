"""
Option Buy Trade Plan Status

Defines approval status for broker-agnostic option-buy trade plans.
"""

from enum import Enum


class OptionBuyTradePlanStatus(Enum):
    """
    Represents whether an option-buy trade plan is approved or rejected.
    """

    APPROVED = "approved"
    REJECTED = "rejected"
