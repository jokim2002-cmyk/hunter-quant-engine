"""
SMC Rule Set Result Builder

Test builder for creating SMCRuleSetResult objects.
"""

from src.strategy.rule_sets.smc_rule_set_result import SMCRuleSetResult


class SMCRuleSetResultBuilder:
    """
    Builder for SMCRuleSetResult test objects.
    """

    def __init__(self):
        self._bos_events = []
        self._choch_events = []
        self._liquidity_sweeps = []
        self._fair_value_gaps = []
        self._order_blocks = []

    def with_bos(self, *bos_events):
        self._bos_events.extend(bos_events)
        return self

    def with_choch(self, *choch_events):
        self._choch_events.extend(choch_events)
        return self

    def with_liquidity_sweeps(self, *liquidity_sweeps):
        self._liquidity_sweeps.extend(liquidity_sweeps)
        return self

    def with_fair_value_gaps(self, *fair_value_gaps):
        self._fair_value_gaps.extend(fair_value_gaps)
        return self

    def with_order_blocks(self, *order_blocks):
        self._order_blocks.extend(order_blocks)
        return self

    def build(self):
        return SMCRuleSetResult(
            bos_events=tuple(self._bos_events),
            choch_events=tuple(self._choch_events),
            liquidity_sweeps=tuple(self._liquidity_sweeps),
            fair_value_gaps=tuple(self._fair_value_gaps),
            order_blocks=tuple(self._order_blocks),
        )
