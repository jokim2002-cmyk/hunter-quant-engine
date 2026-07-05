"""
Bullish SMC Rule Set

Composes bullish Smart Money Concept rules.
"""

from src.strategy.rule_sets.base_rule_set import BaseRuleSet
from src.strategy.rule_sets.smc_rule_set_result import SMCRuleSetResult
from src.strategy.rules.liquidity.buy_side_sweep_rule import BuySideSweepRule
from src.strategy.rules.liquidity.bullish_fvg_rule import BullishFVGRule
from src.strategy.rules.liquidity.bullish_order_block_rule import BullishOrderBlockRule
from src.strategy.rules.market_structure.bullish_bos_rule import BullishBOSRule
from src.strategy.rules.market_structure.bullish_choch_rule import BullishCHOCHRule
from src.strategy.strategy_context import StrategyContext


class BullishSMCRuleSet(BaseRuleSet[SMCRuleSetResult]):
    """
    Composes bullish SMC rules into a typed rule set result.
    """

    def __init__(self):
        self._bos_rule = BullishBOSRule()
        self._choch_rule = BullishCHOCHRule()
        self._sweep_rule = BuySideSweepRule()
        self._fvg_rule = BullishFVGRule()
        self._order_block_rule = BullishOrderBlockRule()

    def evaluate(
        self,
        context: StrategyContext,
    ) -> SMCRuleSetResult:
        """
        Evaluate all bullish SMC rules.

        Args:
            context: Immutable market snapshot.

        Returns:
            Immutable bullish SMC rule set result.
        """
        return SMCRuleSetResult(
            bos_events=self._bos_rule.evaluate(context),
            choch_events=self._choch_rule.evaluate(context),
            liquidity_sweeps=self._sweep_rule.evaluate(context),
            fair_value_gaps=self._fvg_rule.evaluate(context),
            order_blocks=self._order_block_rule.evaluate(context),
            analysis_index=self._analysis_index(context),
        )

    def _analysis_index(
        self,
        context: StrategyContext,
    ) -> int | None:
        if not context.candles:
            return None

        return len(context.candles) - 1
