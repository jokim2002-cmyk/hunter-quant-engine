"""
Run SMC Research Workflow

One-command workflow for real-data SMC research:

1. Normalize raw broker/data-provider CSV
2. Inspect normalized CSV quality
3. Run SMC diagnostics
4. Run SMC backtest
5. Export completed trades to CSV
6. Export net equity curve to CSV
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.costs.transaction_cost_profile import TransactionCostProfile
from src.costs.transaction_cost_profile_preset import (
    supported_transaction_cost_profile_names,
)
from scripts.diagnose_smc_backtest import (
    DiagnosticSummary,
    build_report as build_diagnostic_report,
    diagnose,
)
from scripts.inspect_csv_data import (
    CSVInspectionSummary,
    build_report as build_inspection_report,
    inspect_csv,
)
from scripts.normalize_csv_data import (
    NormalizationSummary,
    build_report as build_normalization_report,
    normalize_csv,
)
from scripts.run_smc_backtest import (
    DEFAULT_BROKERAGE_PER_ORDER,
    DEFAULT_COST_PROFILE,
    DEFAULT_EXCHANGE_TRANSACTION_CHARGE_RATE,
    DEFAULT_GST_RATE,
    DEFAULT_SEBI_CHARGE_RATE,
    DEFAULT_STAMP_DUTY_RATE,
    DEFAULT_STT_RATE,
    build_pipeline,
    build_report as build_backtest_report,
    build_risk_profile,
    build_transaction_cost_calculator,
    build_transaction_cost_profile,
    export_equity_curve_to_csv,
    export_trades_to_csv,
    net_total_pnl,
    total_transaction_charges,
)


DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "nifty_5min.csv"
DEFAULT_NORMALIZED_OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "smc_research_normalized.csv"
)
DEFAULT_TRADES_OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "smc_research_trades.csv"
)
DEFAULT_EQUITY_OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "smc_research_equity_curve.csv"
)
DEFAULT_SYMBOL = "NIFTY"
DEFAULT_TIMEFRAME = "5m"
DEFAULT_ACCOUNT_BALANCE = 10000.0
DEFAULT_RISK_PER_TRADE = 0.01
DEFAULT_REWARD_TO_RISK = 2.0


@dataclass(frozen=True)
class SMCResearchWorkflowSummary:
    """
    Immutable one-command SMC research workflow summary.
    """

    input_path: Path
    normalized_output_path: Path
    trades_output_path: Path
    equity_output_path: Path
    symbol: str
    timeframe: str
    transaction_cost_profile: TransactionCostProfile
    normalization_summary: NormalizationSummary
    inspection_summary: CSVInspectionSummary
    diagnostic_summary: DiagnosticSummary
    backtest_result: Any


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build command-line argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Run full HQE SMC research workflow over raw CSV data.",
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Raw input CSV path.",
    )
    parser.add_argument(
        "--normalized-output",
        default=str(DEFAULT_NORMALIZED_OUTPUT_PATH),
        help="Output path for HQE-compatible normalized CSV.",
    )
    parser.add_argument(
        "--trades-output",
        default=str(DEFAULT_TRADES_OUTPUT_PATH),
        help="Output path for completed trade export CSV.",
    )
    parser.add_argument(
        "--equity-output",
        default=str(DEFAULT_EQUITY_OUTPUT_PATH),
        help="Output path for trade-by-trade net equity curve CSV.",
    )
    parser.add_argument(
        "--symbol",
        default=DEFAULT_SYMBOL,
        help="Market symbol used in StrategyContext.",
    )
    parser.add_argument(
        "--timeframe",
        default=DEFAULT_TIMEFRAME,
        help="Market timeframe used in StrategyContext.",
    )
    parser.add_argument(
        "--account-balance",
        type=float,
        default=DEFAULT_ACCOUNT_BALANCE,
        help="Account balance used for risk calculations.",
    )
    parser.add_argument(
        "--risk-per-trade",
        type=float,
        default=DEFAULT_RISK_PER_TRADE,
        help="Risk per trade as decimal. Example: 0.01 means 1%%.",
    )
    parser.add_argument(
        "--reward-to-risk",
        type=float,
        default=DEFAULT_REWARD_TO_RISK,
        help="Reward-to-risk multiple used for take-profit planning.",
    )
    parser.add_argument(
        "--cost-profile",
        default=DEFAULT_COST_PROFILE,
        choices=supported_transaction_cost_profile_names(),
        help="Named broker/segment cost profile. Use custom for manual rates.",
    )
    parser.add_argument(
        "--brokerage-per-order",
        type=float,
        default=DEFAULT_BROKERAGE_PER_ORDER,
        help="Brokerage charged per order. Round trip applies it twice.",
    )
    parser.add_argument(
        "--stt-rate",
        type=float,
        default=DEFAULT_STT_RATE,
        help="STT/CTT rate as decimal applied on exit turnover.",
    )
    parser.add_argument(
        "--exchange-transaction-charge-rate",
        type=float,
        default=DEFAULT_EXCHANGE_TRANSACTION_CHARGE_RATE,
        help="Exchange transaction charge rate as decimal on total turnover.",
    )
    parser.add_argument(
        "--sebi-charge-rate",
        type=float,
        default=DEFAULT_SEBI_CHARGE_RATE,
        help="SEBI charge rate as decimal on total turnover.",
    )
    parser.add_argument(
        "--stamp-duty-rate",
        type=float,
        default=DEFAULT_STAMP_DUTY_RATE,
        help="Stamp duty rate as decimal on entry turnover.",
    )
    parser.add_argument(
        "--gst-rate",
        type=float,
        default=DEFAULT_GST_RATE,
        help="GST rate as decimal on brokerage plus exchange and SEBI charges.",
    )

    parser.add_argument(
        "--datetime-column",
        default=None,
        help="Input datetime/timestamp column name.",
    )
    parser.add_argument(
        "--date-column",
        default=None,
        help="Input date column name when date and time are separate.",
    )
    parser.add_argument(
        "--time-column",
        default=None,
        help="Input time column name when date and time are separate.",
    )
    parser.add_argument(
        "--open-column",
        default=None,
        help="Input open column name.",
    )
    parser.add_argument(
        "--high-column",
        default=None,
        help="Input high column name.",
    )
    parser.add_argument(
        "--low-column",
        default=None,
        help="Input low column name.",
    )
    parser.add_argument(
        "--close-column",
        default=None,
        help="Input close column name.",
    )
    parser.add_argument(
        "--volume-column",
        default=None,
        help="Input volume column name.",
    )
    parser.add_argument(
        "--default-volume",
        type=float,
        default=0.0,
        help="Volume value used when no volume column exists.",
    )

    return parser


def run_workflow(
    input_path: str | Path,
    normalized_output_path: str | Path,
    trades_output_path: str | Path,
    equity_output_path: str | Path,
    symbol: str,
    timeframe: str,
    account_balance: float,
    risk_per_trade: float,
    reward_to_risk: float,
    datetime_column: str | None = None,
    date_column: str | None = None,
    time_column: str | None = None,
    open_column: str | None = None,
    high_column: str | None = None,
    low_column: str | None = None,
    close_column: str | None = None,
    volume_column: str | None = None,
    default_volume: float = 0.0,
    cost_profile: str = DEFAULT_COST_PROFILE,
    brokerage_per_order: float = DEFAULT_BROKERAGE_PER_ORDER,
    stt_rate: float = DEFAULT_STT_RATE,
    exchange_transaction_charge_rate: float = DEFAULT_EXCHANGE_TRANSACTION_CHARGE_RATE,
    sebi_charge_rate: float = DEFAULT_SEBI_CHARGE_RATE,
    stamp_duty_rate: float = DEFAULT_STAMP_DUTY_RATE,
    gst_rate: float = DEFAULT_GST_RATE,
) -> SMCResearchWorkflowSummary:
    """
    Run the full SMC research workflow.

    Returns:
        Immutable SMCResearchWorkflowSummary.
    """
    normalization_summary = normalize_csv(
        input_path=input_path,
        output_path=normalized_output_path,
        datetime_column=datetime_column,
        date_column=date_column,
        time_column=time_column,
        open_column=open_column,
        high_column=high_column,
        low_column=low_column,
        close_column=close_column,
        volume_column=volume_column,
        default_volume=default_volume,
    )

    inspection_summary = inspect_csv(normalization_summary.output_path)

    if not inspection_summary.ready_for_hqe:
        raise ValueError(
            "Normalized CSV is not ready for HQE. "
            "Run inspect_csv_data.py for detailed quality errors."
        )

    risk_profile = build_risk_profile(
        account_balance=account_balance,
        risk_per_trade=risk_per_trade,
        reward_to_risk=reward_to_risk,
    )
    transaction_cost_profile = build_transaction_cost_profile(
        brokerage_per_order=brokerage_per_order,
        stt_rate=stt_rate,
        exchange_transaction_charge_rate=exchange_transaction_charge_rate,
        sebi_charge_rate=sebi_charge_rate,
        stamp_duty_rate=stamp_duty_rate,
        gst_rate=gst_rate,
        cost_profile=cost_profile,
    )
    transaction_cost_calculator = build_transaction_cost_calculator(
        transaction_cost_profile
    )

    diagnostic_summary = diagnose(
        csv_path=normalization_summary.output_path,
        symbol=symbol,
        timeframe=timeframe,
        risk_profile=risk_profile,
    )

    pipeline = build_pipeline(
        csv_path=normalization_summary.output_path,
        symbol=symbol,
        timeframe=timeframe,
        risk_profile=risk_profile,
    )
    backtest_result = pipeline.run()

    export_trades_to_csv(
        trades=tuple(backtest_result.trades),
        output_path=trades_output_path,
        transaction_cost_calculator=transaction_cost_calculator,
    )
    export_equity_curve_to_csv(
        trades=tuple(backtest_result.trades),
        output_path=equity_output_path,
        starting_balance=account_balance,
        transaction_cost_calculator=transaction_cost_calculator,
    )

    return SMCResearchWorkflowSummary(
        input_path=Path(input_path),
        normalized_output_path=Path(normalized_output_path),
        trades_output_path=Path(trades_output_path),
        equity_output_path=Path(equity_output_path),
        symbol=symbol,
        timeframe=timeframe,
        transaction_cost_profile=transaction_cost_profile,
        normalization_summary=normalization_summary,
        inspection_summary=inspection_summary,
        diagnostic_summary=diagnostic_summary,
        backtest_result=backtest_result,
    )


def format_metric(
    label: str,
    value,
) -> str:
    """
    Format workflow metric line.
    """
    return f"{label}: {value}"


def build_workflow_summary_report(
    summary: SMCResearchWorkflowSummary,
) -> str:
    """
    Build compact workflow summary report.
    """
    performance_summary = summary.backtest_result.performance_summary
    transaction_cost_calculator = build_transaction_cost_calculator(
        summary.transaction_cost_profile
    )
    trades = tuple(summary.backtest_result.trades)
    charges = total_transaction_charges(
        trades=trades,
        transaction_cost_calculator=transaction_cost_calculator,
    )
    net_pnl = net_total_pnl(
        gross_total_pnl=performance_summary.total_pnl,
        trades=trades,
        transaction_cost_calculator=transaction_cost_calculator,
    )

    lines = [
        "",
        "============================================================",
        "Hunter Quant Engine - SMC Research Workflow Summary",
        "============================================================",
        format_metric("Input CSV", summary.input_path),
        format_metric("Normalized CSV", summary.normalized_output_path),
        format_metric("Trades CSV", summary.trades_output_path),
        format_metric("Equity Curve CSV", summary.equity_output_path),
        format_metric("Symbol", summary.symbol),
        format_metric("Timeframe", summary.timeframe),
        "------------------------------------------------------------",
        format_metric("Rows Normalized", summary.normalization_summary.rows_written),
        format_metric("Ready For HQE", summary.inspection_summary.ready_for_hqe),
        "------------------------------------------------------------",
        format_metric("Candles Loaded", summary.diagnostic_summary.candles_loaded),
        format_metric("Long Signals", summary.diagnostic_summary.long_signals),
        format_metric("Short Signals", summary.diagnostic_summary.short_signals),
        format_metric("Neutral Signals", summary.diagnostic_summary.neutral_signals),
        format_metric(
            "Trade Plans Before De-duplication",
            summary.diagnostic_summary.trade_plans_before_deduplication,
        ),
        format_metric(
            "Duplicate Trade Plans Removed",
            summary.diagnostic_summary.duplicate_trade_plans_removed,
        ),
        format_metric(
            "Trade Plans After De-duplication",
            summary.diagnostic_summary.trade_plans_after_deduplication,
        ),
        "------------------------------------------------------------",
        format_metric("Total Trades", performance_summary.total_trades),
        format_metric("Total PnL", performance_summary.total_pnl),
        format_metric("Total Charges", charges),
        format_metric("Net PnL", net_pnl),
        "============================================================",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    """
    Run full SMC research workflow and print reports.
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    summary = run_workflow(
        input_path=args.input,
        normalized_output_path=args.normalized_output,
        trades_output_path=args.trades_output,
        equity_output_path=args.equity_output,
        symbol=args.symbol,
        timeframe=args.timeframe,
        account_balance=args.account_balance,
        risk_per_trade=args.risk_per_trade,
        reward_to_risk=args.reward_to_risk,
        datetime_column=args.datetime_column,
        date_column=args.date_column,
        time_column=args.time_column,
        open_column=args.open_column,
        high_column=args.high_column,
        low_column=args.low_column,
        close_column=args.close_column,
        volume_column=args.volume_column,
        default_volume=args.default_volume,
        cost_profile=args.cost_profile,
        brokerage_per_order=args.brokerage_per_order,
        stt_rate=args.stt_rate,
        exchange_transaction_charge_rate=args.exchange_transaction_charge_rate,
        sebi_charge_rate=args.sebi_charge_rate,
        stamp_duty_rate=args.stamp_duty_rate,
        gst_rate=args.gst_rate,
    )

    transaction_cost_calculator = build_transaction_cost_calculator(
        summary.transaction_cost_profile
    )

    print(build_normalization_report(summary.normalization_summary))
    print(build_inspection_report(summary.inspection_summary))
    print(build_diagnostic_report(summary.diagnostic_summary))
    print(
        build_backtest_report(
            result=summary.backtest_result,
            csv_path=summary.normalized_output_path,
            symbol=summary.symbol,
            timeframe=summary.timeframe,
            transaction_cost_calculator=transaction_cost_calculator,
        )
    )
    print(build_workflow_summary_report(summary))


if __name__ == "__main__":
    main()
