"""
SMC Strategy

Generates TradeSignal objects from Smart Money Concept confluence.
"""

from src.models.institutional_setup import InstitutionalSetup
from src.strategy.base_strategy import BaseStrategy
from src.strategy.confluence.base_confluence_engine import BaseConfluenceEngine
from src.strategy.confluence.smc_confluence_engine import SMCConfluenceEngine
from src.strategy.rule_sets.bearish_smc_rule_set import BearishSMCRuleSet
from src.strategy.rule_sets.bullish_smc_rule_set import BullishSMCRuleSet
from src.strategy.rule_sets.smc_rule_set_result import SMCRuleSetResult
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.strategy_context import StrategyContext
from src.strategy.trade_signal import TradeSignal


class SMCStrategy(BaseStrategy):
    """
    Smart Money Concept strategy.

    Consumes bullish and bearish SMC rule sets, generates institutional
    setups through a confluence engine, and emits deterministic TradeSignal
    objects.
    """

    def __init__(
        self,
        bullish_rule_set: BullishSMCRuleSet | None = None,
        bearish_rule_set: BearishSMCRuleSet | None = None,
        confluence_engine: (
            BaseConfluenceEngine[SMCRuleSetResult, InstitutionalSetup] | None
        ) = None,
    ) -> None:
        self._bullish_rule_set = bullish_rule_set or BullishSMCRuleSet()
        self._bearish_rule_set = bearish_rule_set or BearishSMCRuleSet()
        self._confluence_engine = confluence_engine or SMCConfluenceEngine()

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

        bullish_setups = self._confluence_engine.generate(
            result=bullish_result,
            direction=SignalType.LONG,
            created_at=context.analysis_time,
        )
        bearish_setups = self._confluence_engine.generate(
            result=bearish_result,
            direction=SignalType.SHORT,
            created_at=context.analysis_time,
        )

        if bullish_setups and not bearish_setups:
            return (self._long_signal(context),)

        if bearish_setups and not bullish_setups:
            return (self._short_signal(context),)

        if bullish_setups and bearish_setups:
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
