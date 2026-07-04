"""
SMC Confluence Engine

Generates institutional setups from Smart Money Concept rule set results.
"""

from datetime import datetime
from typing import TypeVar

from src.models.institutional_setup import InstitutionalSetup
from src.strategy.confluence.base_confluence_engine import BaseConfluenceEngine
from src.strategy.rule_sets.smc_rule_set_result import SMCRuleSetResult
from src.strategy.setup_validators.base_setup_validator import BaseSetupValidator
from src.strategy.setup_validators.smc_setup_validator import SMCSetupValidator
from src.strategy.signal_type import SignalType

T = TypeVar("T")


class SMCConfluenceEngine(
    BaseConfluenceEngine[SMCRuleSetResult, InstitutionalSetup]
):
    """
    Generates institutional SMC setups from rule set confluence.

    The engine delegates setup validity to SMCSetupValidator and then
    converts the strongest available rule evidence into a single
    InstitutionalSetup.
    """

    def __init__(
        self,
        setup_validator: BaseSetupValidator[SMCRuleSetResult] | None = None,
    ) -> None:
        self._setup_validator = setup_validator or SMCSetupValidator()

    def generate(
        self,
        result: SMCRuleSetResult,
        direction: SignalType,
        created_at: datetime,
    ) -> tuple[InstitutionalSetup, ...]:
        """
        Generate institutional SMC setups.

        Args:
            result: Immutable SMC rule set result.
            direction: Direction of the setup being generated.
            created_at: Timestamp used for generated setup objects.

        Returns:
            Tuple containing one InstitutionalSetup when valid confluence
            exists. Empty tuple otherwise.
        """
        if direction == SignalType.NEUTRAL:
            return ()

        if not self._setup_validator.is_valid(result):
            return ()

        setup = InstitutionalSetup(
            direction=direction,
            confidence=self._calculate_confidence(result),
            rationale=self._build_rationale(result, direction),
            created_at=created_at,
            bos_event=self._first(result.bos_events),
            choch_event=self._first(result.choch_events),
            liquidity_sweep=self._first(result.liquidity_sweeps),
            fair_value_gap=self._first(result.fair_value_gaps),
            order_block=self._first(result.order_blocks),
        )

        return (setup,)

    def _first(
        self,
        items: tuple[T, ...],
    ) -> T | None:
        if not items:
            return None

        return items[0]

    def _calculate_confidence(
        self,
        result: SMCRuleSetResult,
    ) -> float:
        confidence = 0.0

        if result.bos_events or result.choch_events:
            confidence += 30.0

        if result.liquidity_sweeps:
            confidence += 30.0

        if result.fair_value_gaps:
            confidence += 20.0

        if result.order_blocks:
            confidence += 20.0

        return min(confidence, 100.0)

    def _build_rationale(
        self,
        result: SMCRuleSetResult,
        direction: SignalType,
    ) -> tuple[str, ...]:
        rationale: list[str] = [
            f"{direction.value.upper()} institutional SMC setup generated.",
        ]

        if result.bos_events:
            rationale.append("BOS market structure evidence present.")

        if result.choch_events:
            rationale.append("CHOCH market structure evidence present.")

        if result.liquidity_sweeps:
            rationale.append("Liquidity sweep evidence present.")

        if result.fair_value_gaps:
            rationale.append("Fair value gap entry zone evidence present.")

        if result.order_blocks:
            rationale.append("Order block entry zone evidence present.")

        return tuple(rationale)
