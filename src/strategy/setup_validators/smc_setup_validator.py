"""
SMC Setup Validator

Validates Smart Money Concept rule set confluence.
"""

from src.strategy.rule_sets.smc_rule_set_result import SMCRuleSetResult
from src.strategy.setup_validators.base_setup_validator import BaseSetupValidator


class SMCSetupValidator(BaseSetupValidator[SMCRuleSetResult]):
    """
    Validates whether an SMC rule set result has enough confluence.

    A valid SMC setup requires:
    - market structure evidence
    - liquidity sweep evidence
    - entry zone evidence
    """

    def is_valid(
        self,
        result: SMCRuleSetResult,
    ) -> bool:
        """
        Validate SMC setup confluence.

        Args:
            result: Immutable SMC rule set result.

        Returns:
            True when required SMC confluence exists.
            False otherwise.
        """
        return (
            self._has_market_structure(result)
            and self._has_liquidity_sweep(result)
            and self._has_entry_zone(result)
        )

    def _has_market_structure(
        self,
        result: SMCRuleSetResult,
    ) -> bool:
        return bool(result.bos_events or result.choch_events)

    def _has_liquidity_sweep(
        self,
        result: SMCRuleSetResult,
    ) -> bool:
        return bool(result.liquidity_sweeps)

    def _has_entry_zone(
        self,
        result: SMCRuleSetResult,
    ) -> bool:
        return bool(result.fair_value_gaps or result.order_blocks)
