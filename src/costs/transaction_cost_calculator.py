"""
Transaction Cost Calculator

Calculates configurable brokerage, taxes, fees, total charges, and net PnL
for completed backtest trades.
"""

from src.costs.transaction_cost_breakdown import TransactionCostBreakdown
from src.costs.transaction_cost_profile import TransactionCostProfile


class TransactionCostCalculator:
    """
    Calculates transaction costs for completed trades.
    """

    def __init__(
        self,
        profile: TransactionCostProfile | None = None,
    ):
        self._profile = profile or TransactionCostProfile()

    def calculate(
        self,
        trade,
    ) -> TransactionCostBreakdown:
        """
        Calculate transaction costs for one completed trade.

        Args:
            trade: TradeResult-like object.

        Returns:
            Immutable TransactionCostBreakdown.
        """
        position_size = abs(float(trade.position_size))
        entry_turnover = abs(float(trade.entry_price) * position_size)
        exit_turnover = abs(float(trade.exit_price) * position_size)
        total_turnover = entry_turnover + exit_turnover

        brokerage = self._calculate_brokerage(entry_turnover) + self._calculate_brokerage(
            exit_turnover
        )
        stt = exit_turnover * self._profile.stt_rate
        exchange_transaction_charge = (
            total_turnover * self._profile.exchange_transaction_charge_rate
        )
        sebi_charge = total_turnover * self._profile.sebi_charge_rate
        stamp_duty = entry_turnover * self._profile.stamp_duty_rate
        clearing_charge = total_turnover * self._profile.clearing_charge_rate
        investor_protection_fund = (
            total_turnover * self._profile.investor_protection_fund_rate
        )
        gst = (
            brokerage
            + exchange_transaction_charge
            + sebi_charge
            + clearing_charge
            + investor_protection_fund
        ) * self._profile.gst_rate

        total_charges = (
            brokerage
            + stt
            + exchange_transaction_charge
            + sebi_charge
            + stamp_duty
            + clearing_charge
            + investor_protection_fund
            + gst
        )
        gross_pnl = float(trade.pnl)
        net_pnl = gross_pnl - total_charges

        return TransactionCostBreakdown(
            gross_pnl=gross_pnl,
            brokerage=brokerage,
            stt=stt,
            exchange_transaction_charge=exchange_transaction_charge,
            sebi_charge=sebi_charge,
            stamp_duty=stamp_duty,
            clearing_charge=clearing_charge,
            investor_protection_fund=investor_protection_fund,
            gst=gst,
            total_charges=total_charges,
            net_pnl=net_pnl,
        )

    def _calculate_brokerage(
        self,
        order_turnover: float,
    ) -> float:
        """
        Calculate brokerage for one executed order.

        Args:
            order_turnover: Single order turnover.

        Returns:
            Brokerage amount for one order.
        """
        if self._profile.brokerage_rate <= 0:
            return self._profile.brokerage_per_order

        percentage_brokerage = order_turnover * self._profile.brokerage_rate

        if self._profile.brokerage_cap_per_order <= 0:
            return percentage_brokerage

        return min(
            percentage_brokerage,
            self._profile.brokerage_cap_per_order,
        )
