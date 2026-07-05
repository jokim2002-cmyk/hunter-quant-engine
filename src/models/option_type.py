"""
Option Type

Defines supported NIFTY option contract types.
"""

from enum import Enum


class OptionType(Enum):
    """
    Represents the type of an option contract.
    """

    CE = "CE"
    PE = "PE"

    @property
    def is_call(self) -> bool:
        """
        Return True when the option type is Call/CE.
        """
        return self is OptionType.CE

    @property
    def is_put(self) -> bool:
        """
        Return True when the option type is Put/PE.
        """
        return self is OptionType.PE
