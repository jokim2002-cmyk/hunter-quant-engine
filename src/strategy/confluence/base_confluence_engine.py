"""
Base Confluence Engine Contract

Defines the abstract contract for strategy confluence engines.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar

from src.strategy.signal_type import SignalType

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseConfluenceEngine(ABC, Generic[InputT, OutputT]):
    """
    Base contract for all strategy confluence engines.

    Confluence engines transform lower-level rule set results into
    higher-level institutional setup objects.

    Confluence engines do not:
    - detect raw market structure
    - execute trades
    - calculate position sizing
    - mutate input rule set results
    """

    @abstractmethod
    def generate(
        self,
        result: InputT,
        direction: SignalType,
        created_at: datetime,
    ) -> tuple[OutputT, ...]:
        """
        Generate institutional setup objects from a rule set result.

        Args:
            result: Immutable rule set result.
            direction: Direction of the setup being generated.
            created_at: Timestamp used for generated setup objects.

        Returns:
            Tuple of generated immutable setup objects.
        """
        raise NotImplementedError
