"""
Strategy Context Builder

Test builder for creating StrategyContext objects.
"""

from src.strategy.strategy_context import StrategyContext
from tests.builders.common.defaults import DEFAULT_TIMESTAMP


class StrategyContextBuilder:
    """
    Builder for StrategyContext test objects.
    """

    def __init__(self):
        self._symbol = "TEST"
        self._timeframe = "1H"
        self._analysis_time = DEFAULT_TIMESTAMP

        self._candles = []
        self._market_structure_points = []
        self._bos_events = []
        self._choch_events = []
        self._liquidity_points = []
        self._equal_high_points = []
        self._equal_low_points = []
        self._liquidity_clusters = []
        self._liquidity_sweeps = []
        self._fair_value_gaps = []
        self._order_blocks = []

    def symbol(self, symbol: str):
        self._symbol = symbol
        return self

    def timeframe(self, timeframe: str):
        self._timeframe = timeframe
        return self

    def analysis_time(self, analysis_time):
        self._analysis_time = analysis_time
        return self

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

    def build(self) -> StrategyContext:
        return StrategyContext(
            symbol=self._symbol,
            timeframe=self._timeframe,
            analysis_time=self._analysis_time,
            candles=tuple(self._candles),
            market_structure_points=tuple(self._market_structure_points),
            bos_events=tuple(self._bos_events),
            choch_events=tuple(self._choch_events),
            liquidity_points=tuple(self._liquidity_points),
            equal_high_points=tuple(self._equal_high_points),
            equal_low_points=tuple(self._equal_low_points),
            liquidity_clusters=tuple(self._liquidity_clusters),
            liquidity_sweeps=tuple(self._liquidity_sweeps),
            fair_value_gaps=tuple(self._fair_value_gaps),
            order_blocks=tuple(self._order_blocks),
        )
