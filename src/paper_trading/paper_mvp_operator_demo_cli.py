"""
Paper MVP Operator Demo CLI

Runs the paper MVP operator workflow locally:

approved option-buy plan -> paper session -> paper exit -> paper report -> evidence gates

Paper/simulation only.
No broker code. No real orders. No live market data.
Not a profitability claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.paper_trading.paper_backtest_evidence_runner import (
    PaperBacktestEvidencePaths,
    PaperBacktestEvidenceReport,
    run_paper_backtest_evidence,
)
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.strategy_to_paper_bridge import (
    StrategyPaperBridgeResult,
    StrategyPaperExitInstruction,
    run_strategy_to_paper_bridge,
)
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


DEFAULT_OPERATOR_DEMO_OUTPUT_DIR = (
    Path("reports") / "paper_trading" / "operator_demo"
)


@dataclass(frozen=True)
class PaperMvpOperatorDemoResult:
    """
    Result for the paper MVP operator demo.
    """

    bridge_result: StrategyPaperBridgeResult
    evidence_report: PaperBacktestEvidenceReport
    evidence_paths: PaperBacktestEvidencePaths


def run_paper_mvp_operator_demo(
    *,
    output_dir: str | Path = DEFAULT_OPERATOR_DEMO_OUTPUT_DIR,
    generated_at: datetime | None = None,
) -> PaperMvpOperatorDemoResult:
    """
    Run one local paper MVP operator demo workflow.
    """
    safe_output_dir = _ensure_reports_output_dir(output_dir)
    started_at = generated_at or datetime.now(timezone.utc)
    closed_at = started_at + timedelta(minutes=15)

    plan = _build_demo_option_buy_plan(started_at)

    bridge_result = run_strategy_to_paper_bridge(
        [plan],
        exit_instructions=[
            StrategyPaperExitInstruction(
                symbol=plan.entry.contract.symbol,
                closed_at=closed_at,
                exit_reason=PaperExitReason.TARGET,
                exit_price=135.0,
                estimated_exit_charges=10.0,
                estimated_slippage=5.0,
            )
        ],
        output_dir=safe_output_dir / "strategy_to_paper",
        generated_at=started_at,
    )

    evidence_report, evidence_paths = run_paper_backtest_evidence(
        bridge_result.session,
        output_dir=safe_output_dir / "evidence",
        generated_at=closed_at,
    )

    return PaperMvpOperatorDemoResult(
        bridge_result=bridge_result,
        evidence_report=evidence_report,
        evidence_paths=evidence_paths,
    )


def format_paper_mvp_operator_demo_result(
    result: PaperMvpOperatorDemoResult,
) -> str:
    """
    Format the paper MVP operator demo result for terminal output.
    """
    bridge = result.bridge_result
    evidence = result.evidence_report

    lines = [
        "Hunter Quant Engine - Paper MVP Operator Demo",
        "paper/simulation only",
        "no broker",
        "no live market data",
        "no real orders",
        "not a profitability claim",
        "",
        "Workflow",
        "approved option-buy plan -> paper session -> paper exit -> report -> evidence",
        "",
        "Paper Session",
        f"submitted orders: {bridge.submitted_orders_count}",
        f"skipped plans: {bridge.skipped_plans_count}",
        f"exit records: {bridge.exit_records_count}",
        f"open positions: {bridge.summary.open_positions_count}",
        f"closed trades: {bridge.summary.closed_trades_count}",
        "",
        "Evidence Gates",
        f"passed gates: {evidence.passed}",
        f"blocking reasons: {len(evidence.blocking_reasons)}",
        "",
        "Files",
        f"paper report: {bridge.report_paths.report_text}",
        f"paper summary json: {bridge.report_paths.summary_json}",
        f"evidence text: {result.evidence_paths.evidence_text}",
        f"evidence json: {result.evidence_paths.evidence_json}",
    ]

    if evidence.blocking_reasons:
        lines.append("")
        lines.append("Blocking Reasons")
        lines.extend(f"- {reason}" for reason in evidence.blocking_reasons)

    return "\n".join(lines) + "\n"


def main() -> int:
    """
    CLI entrypoint.
    """
    result = run_paper_mvp_operator_demo()
    print(format_paper_mvp_operator_demo_result(result), end="")
    return 0 if result.evidence_report.passed else 1


def _build_demo_option_buy_plan(created_at: datetime) -> OptionBuyTradePlan:
    contract = OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol="NIFTY26JUL24200CE",
    )
    entry = OptionChainEntry(
        contract=contract,
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10000,
        open_interest=50000,
    )
    signal = TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("paper MVP operator demo signal",),
        created_at=created_at,
    )

    return OptionBuyTradePlan(
        signal=signal,
        entry=entry,
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=100.0,
        stop_loss_premium=70.0,
        target_premium=160.0,
        lots=2,
        estimated_charges=40.0,
        status=OptionBuyTradePlanStatus.APPROVED,
        rejection_reasons=(),
    )


def _ensure_reports_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    if "reports" not in path.parts:
        raise ValueError("paper MVP operator demo output must be under reports/")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
