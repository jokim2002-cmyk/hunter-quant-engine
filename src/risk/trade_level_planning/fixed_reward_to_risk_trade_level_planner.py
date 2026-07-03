"""
Fixed Reward-to-Risk Trade Level Planner

Plans take-profit levels using a fixed reward-to-risk multiple.
"""

from src.risk.risk_profile import RiskProfile
from src.risk.trade_level_planning.base_trade_level_planner import BaseTradeLevelPlanner
from src.risk.trade_level_planning.trade_levels import TradeLevels
from src.strategy.signal_type import SignalType


class FixedRewardToRiskTradeLevelPlanner(BaseTradeLevelPlanner):
    """
    Calculates take-profit using:

    price risk per unit * reward_to_risk
    """

    def plan(
        self,
        signal_type: SignalType,
        entry_price: float,
        stop_loss: float,
        risk_profile: RiskProfile,
    ) -> TradeLevels:
        """
        Plan trade levels using fixed reward-to-risk.

        Args:
            signal_type: Directional strategy signal type.
            entry_price: Planned trade entry price.
            stop_loss: Planned stop-loss price.
            risk_profile: Immutable risk profile.

        Returns:
            Immutable trade levels.
        """
        price_risk_per_unit = abs(entry_price - stop_loss)

        if signal_type == SignalType.LONG:
            take_profit = entry_price + (
                price_risk_per_unit * risk_profile.reward_to_risk
            )

            return TradeLevels(
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        if signal_type == SignalType.SHORT:
            take_profit = entry_price - (
                price_risk_per_unit * risk_profile.reward_to_risk
            )

            return TradeLevels(
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        return TradeLevels(
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=entry_price,
        )
