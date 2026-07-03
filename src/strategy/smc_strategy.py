"""
SMC Strategy

Generates TradeSignal objects from Smart Money Concept confluence.
"""

from src.strategy.base_strategy import BaseStrategy
from src.strategy.rule_sets.bearish_smc_rule_set import BearishSMCRuleSet
from src.strategy.rule_sets.bullish_smc_rule_set import BullishSMCRuleSet
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.setup_validators.smc_setup_validator import SMCSetupValidator
from src.strategy.strategy_context import StrategyContext
from src.strategy.trade_signal import TradeSignal


class SMCStrategy(BaseStrategy):
    """
    Smart Money Concept strategy.

    Consumes bullish and bearish SMC rule sets, validates confluence,
    and emits deterministic TradeSignal objects.
    """

    def __init__(self):
        self._bullish_rule_set = BullishSMCRuleSet()
        self._bearish_rule_set = BearishSMCRuleSet()
        self._setup_validator = SMCSetupValidator()

    def generate(
        self,
        context: StrategyContext,
    ) -> tuple[TradeSignal, ...]:
        """
        Generate an SMC trade signal from the current StrategyContext.

        Args:
            context: Immutable strategy context.

        Returns:
            Tuple containing one deterministic TradeSignal.
        """
        bullish_result = self._bullish_rule_set.evaluate(context)
        bearish_result = self._bearish_rule_set.evaluate(context)

        bullish_is_valid = self._setup_validator.is_valid(bullish_result)
        bearish_is_valid = self._setup_validator.is_valid(bearish_result)

        if bullish_is_valid and not bearish_is_valid:
            return (self._long_signal(context),)

        if bearish_is_valid and not bullish_is_valid:
            return (self._short_signal(context),)

        if bullish_is_valid and bearish_is_valid:
            return (self._conflicting_neutral_signal(context),)

        return (self._no_setup_neutral_signal(context),)

    def _long_signal(
        self,
        context: StrategyContext,
    ) -> TradeSignal:
        return TradeSignal(
            signal_type=SignalType.LONG,
            strength=SignalStrength.MEDIUM,
            confidence=0.75,
            rationale=(
                "Bullish SMC setup is valid.",
                "Bearish SMC setup is invalid.",
            ),
            created_at=context.analysis_time,
        )

    def _short_signal(
        self,
        context: StrategyContext,
    ) -> TradeSignal:
        return TradeSignal(
            signal_type=SignalType.SHORT,
            strength=SignalStrength.MEDIUM,
            confidence=0.75,
            rationale=(
                "Bearish SMC setup is valid.",
                "Bullish SMC setup is invalid.",
            ),
            created_at=context.analysis_time,
        )

    def _conflicting_neutral_signal(
        self,
        context: StrategyContext,
    ) -> TradeSignal:
        return TradeSignal(
            signal_type=SignalType.NEUTRAL,
            strength=SignalStrength.WEAK,
            confidence=0.0,
            rationale=(
                "Conflicting bullish and bearish SMC setups exist.",
            ),
            created_at=context.analysis_time,
        )

    def _no_setup_neutral_signal(
        self,
        context: StrategyContext,
    ) -> TradeSignal:
        return TradeSignal(
            signal_type=SignalType.NEUTRAL,
            strength=SignalStrength.WEAK,
            confidence=0.0,
            rationale=(
                "No valid directional SMC setup exists.",
            ),
            created_at=context.analysis_time,
        )
