"""
SMC Setup Validator

Validates Smart Money Concept rule set confluence.
"""

from src.config.strategy_config import (
    DEFAULT_SMC_STRATEGY_CONFIG,
    SMCStrategyConfig,
)
from src.strategy.rule_sets.smc_rule_set_result import SMCRuleSetResult
from src.strategy.setup_validators.base_setup_validator import BaseSetupValidator


class SMCSetupValidator(BaseSetupValidator[SMCRuleSetResult]):
    """
    Validates whether an SMC rule set result has enough confluence.

    The exact confluence requirements are controlled by SMCStrategyConfig.
    Balanced mode preserves the original HQE behavior:
    - market structure evidence
    - liquidity sweep evidence
    - entry zone evidence
    """

    def __init__(
        self,
        config: SMCStrategyConfig | None = None,
    ) -> None:
        self._config = config or DEFAULT_SMC_STRATEGY_CONFIG

    def is_valid(
        self,
        result: SMCRuleSetResult,
    ) -> bool:
        """
        Validate SMC setup confluence.

        Args:
            result: Immutable SMC rule set result.

        Returns:
            True when configured SMC confluence exists.
            False otherwise.
        """
        if self._config.require_market_structure and not self._has_market_structure(
            result
        ):
            return False

        if self._config.require_liquidity_sweep and not self._has_liquidity_sweep(
            result
        ):
            return False

        if self._config.require_entry_zone and not self._has_entry_zone(result):
            return False

        if self._config.require_fair_value_gap and not result.fair_value_gaps:
            return False

        if self._config.require_order_block and not result.order_blocks:
            return False

        return True

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
