"""
Base Setup Validator Contract

Defines the abstract contract for strategy setup validation.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseSetupValidator(ABC, Generic[T]):
    """
    Base contract for all strategy setup validators.

    Setup validators evaluate immutable rule set results and determine
    whether sufficient confluence exists for a strategy decision.

    Setup validators do not:
    - create trade signals
    - execute trades
    - mutate rule set results
    - store stateful market data
    """

    @abstractmethod
    def is_valid(
        self,
        result: T,
    ) -> bool:
        """
        Validate a rule set result.

        Args:
            result: Immutable rule set result.

        Returns:
            True when the result satisfies setup requirements.
            False otherwise.
        """
        raise NotImplementedError
