"""
Run FYERS NIFTY Research

Convenience one-command runner for FYERS NIFTY 5-minute SMC research.

This script wraps the generic SMC research workflow with:
- FYERS equity intraday transaction cost profile
- NIFTY symbol default
- 5m timeframe default
- standard processed output file names
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.strategy_config import supported_strategy_mode_names
from src.costs.transaction_cost_profile_preset import (
    COST_PROFILE_FYERS_EQUITY_INTRADAY,
)
from scripts.run_smc_research_workflow import (
    DEFAULT_ACCOUNT_BALANCE,
    DEFAULT_STRATEGY_MODE,
    DEFAULT_REWARD_TO_RISK,
    DEFAULT_RISK_PER_TRADE,
    build_workflow_summary_report,
    run_workflow,
)
from scripts.diagnose_smc_backtest import (
    build_report as build_diagnostic_report,
)
from scripts.inspect_csv_data import (
    build_report as build_inspection_report,
)
from scripts.normalize_csv_data import (
    build_report as build_normalization_report,
)
from scripts.run_smc_backtest import (
    build_report as build_backtest_report,
    build_transaction_cost_calculator,
)


DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "fyers_nifty_5min.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_OUTPUT_PREFIX = "fyers_nifty_5m"
DEFAULT_SYMBOL = "NIFTY"
DEFAULT_TIMEFRAME = "5m"


@dataclass(frozen=True)
class FYERSNIFTYOutputPaths:
    """
    Immutable output paths for FYERS NIFTY research.
    """

    normalized_output_path: Path
    trades_output_path: Path
    equity_output_path: Path


def build_output_paths(
    output_dir: str | Path,
    output_prefix: str,
) -> FYERSNIFTYOutputPaths:
    """
    Build standard output paths.

    Args:
        output_dir: Output directory.
        output_prefix: File prefix.

    Returns:
        Immutable output paths.
    """
    directory = Path(output_dir)

    return FYERSNIFTYOutputPaths(
        normalized_output_path=directory / f"{output_prefix}_normalized.csv",
        trades_output_path=directory / f"{output_prefix}_trades.csv",
        equity_output_path=directory / f"{output_prefix}_equity_curve.csv",
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build command-line argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Run FYERS NIFTY SMC research workflow.",
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Raw FYERS NIFTY CSV path.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for normalized, trades, and equity curve CSV outputs.",
    )
    parser.add_argument(
        "--output-prefix",
        default=DEFAULT_OUTPUT_PREFIX,
        help="Output file prefix.",
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
        "--strategy-mode",
        default=DEFAULT_STRATEGY_MODE,
        choices=supported_strategy_mode_names(),
        help="SMC strategy mode: strict, balanced, or relaxed.",
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


def run_fyers_nifty_research(
    input_path: str | Path,
    output_dir: str | Path,
    output_prefix: str,
    symbol: str,
    timeframe: str,
    account_balance: float,
    risk_per_trade: float,
    reward_to_risk: float,
    strategy_mode: str = DEFAULT_STRATEGY_MODE,
    datetime_column: str | None = None,
    date_column: str | None = None,
    time_column: str | None = None,
    open_column: str | None = None,
    high_column: str | None = None,
    low_column: str | None = None,
    close_column: str | None = None,
    volume_column: str | None = None,
    default_volume: float = 0.0,
):
    """
    Run FYERS NIFTY research workflow.

    Args:
        input_path: Raw input CSV path.
        output_dir: Output directory.
        output_prefix: Output file prefix.
        symbol: Market symbol.
        timeframe: Market timeframe.
        account_balance: Account balance.
        risk_per_trade: Risk per trade as decimal.
        reward_to_risk: Reward-to-risk multiple.
        datetime_column: Optional explicit datetime column.
        date_column: Optional explicit date column.
        time_column: Optional explicit time column.
        open_column: Optional explicit open column.
        high_column: Optional explicit high column.
        low_column: Optional explicit low column.
        close_column: Optional explicit close column.
        volume_column: Optional explicit volume column.
        default_volume: Default volume when no volume column exists.

    Returns:
        SMCResearchWorkflowSummary.
    """
    output_paths = build_output_paths(
        output_dir=output_dir,
        output_prefix=output_prefix,
    )

    return run_workflow(
        input_path=input_path,
        normalized_output_path=output_paths.normalized_output_path,
        trades_output_path=output_paths.trades_output_path,
        equity_output_path=output_paths.equity_output_path,
        symbol=symbol,
        timeframe=timeframe,
        account_balance=account_balance,
        risk_per_trade=risk_per_trade,
        reward_to_risk=reward_to_risk,
        strategy_mode=strategy_mode,
        datetime_column=datetime_column,
        date_column=date_column,
        time_column=time_column,
        open_column=open_column,
        high_column=high_column,
        low_column=low_column,
        close_column=close_column,
        volume_column=volume_column,
        default_volume=default_volume,
        cost_profile=COST_PROFILE_FYERS_EQUITY_INTRADAY,
    )


def main() -> None:
    """
    Run FYERS NIFTY research workflow and print reports.
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    summary = run_fyers_nifty_research(
        input_path=args.input,
        output_dir=args.output_dir,
        output_prefix=args.output_prefix,
        symbol=args.symbol,
        timeframe=args.timeframe,
        account_balance=args.account_balance,
        risk_per_trade=args.risk_per_trade,
        reward_to_risk=args.reward_to_risk,
        strategy_mode=args.strategy_mode,
        datetime_column=args.datetime_column,
        date_column=args.date_column,
        time_column=args.time_column,
        open_column=args.open_column,
        high_column=args.high_column,
        low_column=args.low_column,
        close_column=args.close_column,
        volume_column=args.volume_column,
        default_volume=args.default_volume,
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
