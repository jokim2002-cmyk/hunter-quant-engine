"""
Option Action

Defines allowed option execution actions for the first HQE option-buy module.
"""

from enum import Enum


class OptionAction(Enum):
    """
    Represents the allowed action for option execution.

    The first HQE option module is option-buy only.
    Option selling must not be added here without a roadmap update.
    """

    BUY = "BUY"
