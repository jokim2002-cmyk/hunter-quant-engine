"""
Strategy to Paper Bridge

Connects approved option-buy strategy/trade-planning output to the local paper
trading session and report writer.

Fake/local paper trading only.
No broker code. No real orders. No live market data.
Not a profitability claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from src.paper_trading.option_buy_plan_to_paper_order import (
    create_paper_order_request_from_option_buy_plan,
)
from src.paper_trading.paper_order_journal import PaperOrderRecord
from src.paper_trading.paper_realized_exit_record import (
    PaperExitReason,
    PaperRealizedExitRecord,
)
from src.paper_trading.paper_trading_report_writer import (
    PaperTradingReportPaths,
    write_paper_trading_report,
)
from src.paper_trading.paper_trading_session import PaperTradingSession
from src.paper_trading.paper_trading_session_summary import (
    PaperTradingSessionSummary,
    build_paper_trading_session_summary,
)
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import (
    OptionBuyTradePlanStatus,
)


DEFAULT_STRATEGY_TO_PAPER_OUTPUT_DIR = (
    Path("reports") / "paper_trading" / "strategy_to_paper"
)


@dataclass(frozen=True)
class StrategyPaperPlanSkip:
    """
    Describes a strategy plan skipped before paper submission.
    """

    index: int
    symbol: str
    status: str
    reason: str


@dataclass(frozen=True)
class StrategyPaperExitInstruction:
    """
    Local paper-only close instruction for an open paper position.
    """

    symbol: str
    closed_at: datetime
    exit_reason: PaperExitReason = PaperExitReason.MANUAL
    exit_price: float | None = None
    estimated_exit_charges: float = 0.0
    estimated_slippage: float = 0.0


@dataclass(frozen=True)
class StrategyPaperBridgeResult:
    """
    Result returned by the strategy-to-paper bridge.
    """

    session: PaperTradingSession
    submitted_orders: tuple[PaperOrderRecord, ...]
    skipped_plans: tuple[StrategyPaperPlanSkip, ...]
    exit_records: tuple[PaperRealizedExitRecord, ...]
    failed_exit_symbols: tuple[str, ...]
    summary: PaperTradingSessionSummary
    report_paths: PaperTradingReportPaths

    @property
    def submitted_orders_count(self) -> int:
        return len(self.submitted_orders)

    @property
    def skipped_plans_count(self) -> int:
        return len(self.skipped_plans)

    @property
    def exit_records_count(self) -> int:
        return len(self.exit_records)


def run_strategy_to_paper_bridge(
    plans: Iterable[OptionBuyTradePlan],
    *,
    exit_instructions: Iterable[StrategyPaperExitInstruction] = (),
    session: PaperTradingSession | None = None,
    output_dir: str | Path = DEFAULT_STRATEGY_TO_PAPER_OUTPUT_DIR,
    generated_at: datetime | None = None,
) -> StrategyPaperBridgeResult:
    """
    Submit approved option-buy plans into a local paper trading session.

    Rejected or non-approved plans are skipped. No live order path exists here.
    Reports are written under reports/ through the paper report writer.
    """
    paper_session = session or PaperTradingSession()
    submitted_orders: list[PaperOrderRecord] = []
    skipped_plans: list[StrategyPaperPlanSkip] = []

    for index, plan in enumerate(plans, start=1):
        if plan.status is not OptionBuyTradePlanStatus.APPROVED:
            skipped_plans.append(_build_plan_skip(index, plan))
            continue

        request = create_paper_order_request_from_option_buy_plan(plan)
        submitted_orders.append(paper_session.submit_order(request))

    exit_records: list[PaperRealizedExitRecord] = []
    failed_exit_symbols: list[str] = []

    for instruction in exit_instructions:
        exit_record = paper_session.close_position_with_exit_record(
            symbol=instruction.symbol,
            closed_at=instruction.closed_at,
            exit_reason=instruction.exit_reason,
            exit_price=instruction.exit_price,
            estimated_exit_charges=instruction.estimated_exit_charges,
            estimated_slippage=instruction.estimated_slippage,
        )
        if exit_record is None:
            failed_exit_symbols.append(instruction.symbol)
            continue
        exit_records.append(exit_record)

    summary = build_paper_trading_session_summary(paper_session)
    report_paths = _write_strategy_paper_report(
        paper_session,
        output_dir=output_dir,
        generated_at=generated_at,
    )

    return StrategyPaperBridgeResult(
        session=paper_session,
        submitted_orders=tuple(submitted_orders),
        skipped_plans=tuple(skipped_plans),
        exit_records=tuple(exit_records),
        failed_exit_symbols=tuple(failed_exit_symbols),
        summary=summary,
        report_paths=report_paths,
    )


def _build_plan_skip(index: int, plan: OptionBuyTradePlan) -> StrategyPaperPlanSkip:
    symbol = plan.entry.contract.symbol
    status = plan.status.value
    reasons = ", ".join(plan.rejection_reasons) if plan.rejection_reasons else status

    return StrategyPaperPlanSkip(
        index=index,
        symbol=symbol,
        status=status,
        reason=reasons,
    )


def _write_strategy_paper_report(
    session: PaperTradingSession,
    *,
    output_dir: str | Path,
    generated_at: datetime | None,
) -> PaperTradingReportPaths:
    if generated_at is None:
        return write_paper_trading_report(session, output_dir)

    return write_paper_trading_report(
        session,
        output_dir,
        generated_at=generated_at,
    )
