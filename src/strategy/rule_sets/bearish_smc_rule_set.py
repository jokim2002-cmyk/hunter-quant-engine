"""
Bearish SMC Rule Set

Composes bearish Smart Money Concept rules.
"""

from src.strategy.rule_sets.base_rule_set import BaseRuleSet
from src.strategy.rule_sets.smc_rule_set_result import SMCRuleSetResult
from src.strategy.rules.liquidity.bearish_fvg_rule import BearishFVGRule
from src.strategy.rules.liquidity.bearish_order_block_rule import BearishOrderBlockRule
from src.strategy.rules.liquidity.sell_side_sweep_rule import SellSideSweepRule
from src.strategy.rules.market_structure.bearish_bos_rule import BearishBOSRule
from src.strategy.rules.market_structure.bearish_choch_rule import BearishCHOCHRule
from src.strategy.strategy_context import StrategyContext


class BearishSMCRuleSet(BaseRuleSet[SMCRuleSetResult]):
    """
    Composes bearish SMC rules into a typed rule set result.
    """

    def __init__(self):
        self._bos_rule = BearishBOSRule()
        self._choch_rule = BearishCHOCHRule()
        self._sweep_rule = SellSideSweepRule()
        self._fvg_rule = BearishFVGRule()
        self._order_block_rule = BearishOrderBlockRule()

    def evaluate(
        self,
        context: StrategyContext,
    ) -> SMCRuleSetResult:
        """
        Evaluate all bearish SMC rules.

        Args:
            context: Immutable market snapshot.

        Returns:
            Immutable bearish SMC rule set result.
        """
        return SMCRuleSetResult(
            bos_events=self._bos_rule.evaluate(context),
            choch_events=self._choch_rule.evaluate(context),
            liquidity_sweeps=self._sweep_rule.evaluate(context),
            fair_value_gaps=self._fvg_rule.evaluate(context),
            order_blocks=self._order_block_rule.evaluate(context),
        )
