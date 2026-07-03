"""
Risk Manager

Converts strategy signals into risk-approved trade plans.
"""

from src.risk.base_risk_manager import BaseRiskManager
from src.risk.position_sizing.fixed_risk_position_sizer import FixedRiskPositionSizer
from src.risk.risk_profile import RiskProfile
from src.risk.trade_level_planning.fixed_reward_to_risk_trade_level_planner import (
    FixedRewardToRiskTradeLevelPlanner,
)
from src.risk.trade_plan import TradePlan
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal


class RiskManager(BaseRiskManager):
    """
    Default HQE risk manager.

    Uses fixed reward-to-risk trade levels and fixed-risk position sizing.
    """

    def __init__(self):
        self._trade_level_planner = FixedRewardToRiskTradeLevelPlanner()
        self._position_sizer = FixedRiskPositionSizer()

    def plan(
        self,
        signal: TradeSignal,
        risk_profile: RiskProfile,
        entry_price: float,
        stop_loss: float,
    ) -> tuple[TradePlan, ...]:
        """
        Create a risk-approved trade plan from a strategy signal.

        Args:
            signal: Immutable strategy signal.
            risk_profile: Immutable risk profile.
            entry_price: Planned trade entry price.
            stop_loss: Planned stop-loss price.

        Returns:
            Tuple containing one TradePlan for directional signals.
            Empty tuple for neutral signals.
        """
        if signal.signal_type == SignalType.NEUTRAL:
            return ()

        trade_levels = self._trade_level_planner.plan(
            signal_type=signal.signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_profile=risk_profile,
        )

        position_size = self._position_sizer.calculate(
            risk_profile=risk_profile,
            entry_price=trade_levels.entry_price,
            stop_loss=trade_levels.stop_loss,
        )

        risk_amount = risk_profile.risk_amount()
        reward_amount = risk_amount * risk_profile.reward_to_risk

        return (
            TradePlan(
                signal_type=signal.signal_type,
                entry_price=trade_levels.entry_price,
                stop_loss=trade_levels.stop_loss,
                take_profit=trade_levels.take_profit,
                position_size=position_size,
                risk_amount=risk_amount,
                reward_amount=reward_amount,
                created_at=signal.created_at,
            ),
        )
