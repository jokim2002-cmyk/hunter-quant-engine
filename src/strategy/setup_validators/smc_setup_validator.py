"""
SMC Setup Validator

Validates Smart Money Concept rule set confluence.
"""

from collections.abc import Iterable

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
    Balanced mode preserves the original HQE confluence categories while also
    requiring reasonably recent evidence:
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

        if self._config.require_fair_value_gap and not self._has_fair_value_gap(
            result
        ):
            return False

        if self._config.require_order_block and not self._has_order_block(result):
            return False

        return True

    def _has_market_structure(
        self,
        result: SMCRuleSetResult,
    ) -> bool:
        indices = [
            event.index
            for event in result.bos_events
        ]
        indices.extend(
            event.index
            for event in result.choch_events
        )

        return self._has_recent_index(
            indices=indices,
            analysis_index=result.analysis_index,
            max_age=self._config.max_market_structure_age_candles,
        )

    def _has_liquidity_sweep(
        self,
        result: SMCRuleSetResult,
    ) -> bool:
        return self._has_recent_index(
            indices=(
                sweep.created_at
                for sweep in result.liquidity_sweeps
            ),
            analysis_index=result.analysis_index,
            max_age=self._config.max_liquidity_sweep_age_candles,
        )

    def _has_entry_zone(
        self,
        result: SMCRuleSetResult,
    ) -> bool:
        return self._has_fair_value_gap(result) or self._has_order_block(result)

    def _has_fair_value_gap(
        self,
        result: SMCRuleSetResult,
    ) -> bool:
        return self._has_recent_index(
            indices=(
                fair_value_gap.created_at
                for fair_value_gap in result.fair_value_gaps
            ),
            analysis_index=result.analysis_index,
            max_age=self._config.max_entry_zone_age_candles,
        )

    def _has_order_block(
        self,
        result: SMCRuleSetResult,
    ) -> bool:
        return self._has_recent_index(
            indices=(
                order_block.candle_index
                for order_block in result.order_blocks
            ),
            analysis_index=result.analysis_index,
            max_age=self._config.max_entry_zone_age_candles,
        )

    def _has_recent_index(
        self,
        indices: Iterable[int],
        analysis_index: int | None,
        max_age: int | None,
    ) -> bool:
        for index in indices:
            if self._is_recent(
                index=index,
                analysis_index=analysis_index,
                max_age=max_age,
            ):
                return True

        return False

    def _is_recent(
        self,
        index: int,
        analysis_index: int | None,
        max_age: int | None,
    ) -> bool:
        if analysis_index is None or max_age is None:
            return True

        age = analysis_index - index

        return age >= 0 and age <= max_age
