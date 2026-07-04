"""
Strategy Experiment Runner

Runs named strategy experiments and writes a summary report.

Safety rule:
- Default mode is dry-run only.
- Real workflow execution requires --execute.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.benchmark_strategy_modes import load_trade_cost_summary
from scripts.compare_hqe_to_buy_and_hold import load_strategy_result
from scripts.run_smc_research_workflow import (
    DEFAULT_ACCOUNT_BALANCE,
    DEFAULT_INPUT_PATH,
    DEFAULT_REWARD_TO_RISK,
    DEFAULT_RISK_PER_TRADE,
    DEFAULT_SYMBOL,
    DEFAULT_TIMEFRAME,
    run_workflow,
)
from src.config.strategy_config import supported_strategy_mode_names


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "experiments"
DEFAULT_OUTPUT_PREFIX = "strategy_experiment"
DEFAULT_REPORT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "strategy_experiment_report.txt"
DEFAULT_SUMMARY_OUTPUT = PROJECT_ROOT / "data" / "processed" / "strategy_experiment_summary.csv"


WorkflowRunner = Callable[..., Any]


@dataclass(frozen=True)
class ExperimentSpec:
    """
    Strategy experiment definition.
    """

    name: str
    strategy_mode: str
    risk_per_trade: float
    reward_to_risk: float


@dataclass(frozen=True)
class ExperimentOutputPaths:
    """
    Output paths for one experiment.
    """

    normalized_output_path: Path
    trades_output_path: Path
    equity_output_path: Path


@dataclass(frozen=True)
class ExperimentResult:
    """
    Finished experiment result.
    """

    name: str
    strategy_mode: str
    risk_per_trade: float
    reward_to_risk: float
    total_trades: int
    gross_pnl: float
    total_charges: float
    net_pnl: float
    ending_balance: float
    return_percent: float
    normalized_output_path: Path
    trades_output_path: Path
    equity_output_path: Path


def sanitize_experiment_name(name: str) -> str:
    """
    Convert experiment names into safe file-name fragments.
    """
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower())
    safe_name = safe_name.strip("_")

    if not safe_name:
        raise ValueError("Experiment name cannot be empty.")

    return safe_name


def build_default_experiment_specs(
    risk_per_trade: float = DEFAULT_RISK_PER_TRADE,
    reward_to_risk: float = DEFAULT_REWARD_TO_RISK,
) -> tuple[ExperimentSpec, ...]:
    """
    Build default experiments for each supported strategy mode.
    """
    return tuple(
        ExperimentSpec(
            name=f"{strategy_mode}_default",
            strategy_mode=strategy_mode,
            risk_per_trade=risk_per_trade,
            reward_to_risk=reward_to_risk,
        )
        for strategy_mode in supported_strategy_mode_names()
    )


def build_experiment_output_paths(
    output_dir: str | Path,
    output_prefix: str,
    experiment_name: str,
) -> ExperimentOutputPaths:
    """
    Build deterministic output paths for one experiment.
    """
    safe_name = sanitize_experiment_name(experiment_name)
    base_path = Path(output_dir) / f"{output_prefix}_{safe_name}"

    return ExperimentOutputPaths(
        normalized_output_path=base_path.with_name(f"{base_path.name}_normalized.csv"),
        trades_output_path=base_path.with_name(f"{base_path.name}_trades.csv"),
        equity_output_path=base_path.with_name(f"{base_path.name}_equity_curve.csv"),
    )


def run_experiment_spec(
    spec: ExperimentSpec,
    input_path: str | Path,
    output_dir: str | Path,
    output_prefix: str,
    symbol: str,
    timeframe: str,
    account_balance: float,
    workflow_runner: WorkflowRunner = run_workflow,
) -> ExperimentResult:
    """
    Run one experiment spec using the supplied workflow runner.
    """
    output_paths = build_experiment_output_paths(
        output_dir=output_dir,
        output_prefix=output_prefix,
        experiment_name=spec.name,
    )

    output_paths.normalized_output_path.parent.mkdir(parents=True, exist_ok=True)

    workflow_runner(
        input_path=input_path,
        normalized_output_path=output_paths.normalized_output_path,
        trades_output_path=output_paths.trades_output_path,
        equity_output_path=output_paths.equity_output_path,
        symbol=symbol,
        timeframe=timeframe,
        account_balance=account_balance,
        risk_per_trade=spec.risk_per_trade,
        reward_to_risk=spec.reward_to_risk,
        strategy_mode=spec.strategy_mode,
    )

    trade_summary = load_trade_cost_summary(output_paths.trades_output_path)
    strategy_result = load_strategy_result(
        equity_curve_csv_path=output_paths.equity_output_path,
        starting_balance=account_balance,
    )

    return ExperimentResult(
        name=spec.name,
        strategy_mode=spec.strategy_mode,
        risk_per_trade=spec.risk_per_trade,
        reward_to_risk=spec.reward_to_risk,
        total_trades=trade_summary.total_trades,
        gross_pnl=trade_summary.gross_pnl,
        total_charges=trade_summary.total_charges,
        net_pnl=trade_summary.net_pnl,
        ending_balance=strategy_result.ending_balance,
        return_percent=strategy_result.return_percent,
        normalized_output_path=output_paths.normalized_output_path,
        trades_output_path=output_paths.trades_output_path,
        equity_output_path=output_paths.equity_output_path,
    )


def run_experiments(
    specs: tuple[ExperimentSpec, ...],
    input_path: str | Path,
    output_dir: str | Path,
    output_prefix: str,
    symbol: str,
    timeframe: str,
    account_balance: float,
    workflow_runner: WorkflowRunner = run_workflow,
) -> tuple[ExperimentResult, ...]:
    """
    Run multiple experiment specs.
    """
    return tuple(
        run_experiment_spec(
            spec=spec,
            input_path=input_path,
            output_dir=output_dir,
            output_prefix=output_prefix,
            symbol=symbol,
            timeframe=timeframe,
            account_balance=account_balance,
            workflow_runner=workflow_runner,
        )
        for spec in specs
    )


EXPERIMENT_RESULT_SORT_FIELDS = (
    "net_pnl",
    "return_percent",
    "gross_pnl",
    "ending_balance",
    "total_trades",
    "total_charges",
)


def sort_experiment_results(
    results: tuple[ExperimentResult, ...],
    sort_by: str = "net_pnl",
    descending: bool = True,
) -> tuple[ExperimentResult, ...]:
    """
    Sort experiment results by a supported numeric result field.
    """
    if sort_by not in EXPERIMENT_RESULT_SORT_FIELDS:
        supported_fields = ", ".join(EXPERIMENT_RESULT_SORT_FIELDS)
        raise ValueError(
            f"Unsupported experiment result sort field: {sort_by}. "
            f"Supported fields: {supported_fields}"
        )

    return tuple(
        sorted(
            results,
            key=lambda result: getattr(result, sort_by),
            reverse=descending,
        )
    )


def best_experiment_results(
    results: tuple[ExperimentResult, ...],
    limit: int = 3,
    sort_by: str = "net_pnl",
) -> tuple[ExperimentResult, ...]:
    """
    Return best experiment results for a supported metric.
    """
    if limit < 1:
        raise ValueError("Best experiment result limit must be at least 1.")

    return sort_experiment_results(
        results=results,
        sort_by=sort_by,
        descending=True,
    )[:limit]


def worst_experiment_results(
    results: tuple[ExperimentResult, ...],
    limit: int = 3,
    sort_by: str = "net_pnl",
) -> tuple[ExperimentResult, ...]:
    """
    Return worst experiment results for a supported metric.
    """
    if limit < 1:
        raise ValueError("Worst experiment result limit must be at least 1.")

    return sort_experiment_results(
        results=results,
        sort_by=sort_by,
        descending=False,
    )[:limit]


def build_dry_run_report(
    specs: tuple[ExperimentSpec, ...],
) -> str:
    """
    Build a dry-run report listing planned experiments.
    """
    lines = [
        "",
        "============================================================",
        "Hunter Quant Engine - Strategy Experiment Plan",
        "============================================================",
        "Mode: DRY RUN",
        "No backtests were executed.",
        "Use --execute to run experiments on the selected machine.",
        "------------------------------------------------------------",
        "Name | Strategy Mode | Risk Per Trade | Reward To Risk",
        "------------------------------------------------------------",
    ]

    for spec in specs:
        lines.append(
            (
                f"{spec.name} | "
                f"{spec.strategy_mode} | "
                f"{spec.risk_per_trade:.4f} | "
                f"{spec.reward_to_risk:.2f}"
            )
        )

    lines.extend(
        [
            "============================================================",
            "",
        ]
    )

    return "\n".join(lines)


def build_experiment_report(
    results: tuple[ExperimentResult, ...],
) -> str:
    """
    Build finished experiment report.
    """
    lines = [
        "",
        "============================================================",
        "Hunter Quant Engine - Strategy Experiment Results",
        "============================================================",
        "Results include transaction costs through exported trade/equity files.",
        "------------------------------------------------------------",
        (
            "Name | Mode | Trades | Gross PnL | Charges | Net PnL | "
            "Ending Balance | Return %"
        ),
        "------------------------------------------------------------",
    ]

    for result in results:
        lines.append(
            (
                f"{result.name} | "
                f"{result.strategy_mode} | "
                f"{result.total_trades} | "
                f"{result.gross_pnl:.2f} | "
                f"{result.total_charges:.2f} | "
                f"{result.net_pnl:.2f} | "
                f"{result.ending_balance:.2f} | "
                f"{result.return_percent:.4f}"
            )
        )

    lines.extend(
        [
            "============================================================",
            "",
        ]
    )

    return "\n".join(lines)


def write_report(
    report: str,
    output_path: Path,
) -> None:
    """
    Write report text file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")


def write_summary_csv(
    results: tuple[ExperimentResult, ...],
    output_path: Path,
) -> None:
    """
    Write experiment summary CSV.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            [
                "name",
                "strategy_mode",
                "risk_per_trade",
                "reward_to_risk",
                "total_trades",
                "gross_pnl",
                "total_charges",
                "net_pnl",
                "ending_balance",
                "return_percent",
                "normalized_output_path",
                "trades_output_path",
                "equity_output_path",
            ]
        )

        for result in results:
            writer.writerow(
                [
                    result.name,
                    result.strategy_mode,
                    result.risk_per_trade,
                    result.reward_to_risk,
                    result.total_trades,
                    result.gross_pnl,
                    result.total_charges,
                    result.net_pnl,
                    result.ending_balance,
                    result.return_percent,
                    result.normalized_output_path,
                    result.trades_output_path,
                    result.equity_output_path,
                ]
            )


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Run HQE strategy experiments. Defaults to dry-run only.",
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Input raw market CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for per-experiment output files.",
    )
    parser.add_argument(
        "--output-prefix",
        default=DEFAULT_OUTPUT_PREFIX,
        help="Prefix for per-experiment output files.",
    )
    parser.add_argument(
        "--summary-output",
        default=str(DEFAULT_SUMMARY_OUTPUT),
        help="Experiment summary CSV path.",
    )
    parser.add_argument(
        "--report-output",
        default=str(DEFAULT_REPORT_OUTPUT),
        help="Experiment report text path.",
    )
    parser.add_argument(
        "--symbol",
        default=DEFAULT_SYMBOL,
        help="Market symbol.",
    )
    parser.add_argument(
        "--timeframe",
        default=DEFAULT_TIMEFRAME,
        help="Market timeframe.",
    )
    parser.add_argument(
        "--account-balance",
        type=float,
        default=DEFAULT_ACCOUNT_BALANCE,
        help="Account balance.",
    )
    parser.add_argument(
        "--risk-per-trade",
        type=float,
        default=DEFAULT_RISK_PER_TRADE,
        help="Risk per trade as decimal.",
    )
    parser.add_argument(
        "--reward-to-risk",
        type=float,
        default=DEFAULT_REWARD_TO_RISK,
        help="Reward-to-risk multiple.",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=list(supported_strategy_mode_names()),
        choices=supported_strategy_mode_names(),
        help="Strategy modes to include.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run experiments. Without this flag, only a dry-run plan is printed.",
    )

    return parser


def main() -> None:
    """
    Run CLI.
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    all_specs = build_default_experiment_specs(
        risk_per_trade=args.risk_per_trade,
        reward_to_risk=args.reward_to_risk,
    )
    specs = tuple(spec for spec in all_specs if spec.strategy_mode in args.modes)

    if not args.execute:
        print(build_dry_run_report(specs))
        return

    results = run_experiments(
        specs=specs,
        input_path=args.input,
        output_dir=args.output_dir,
        output_prefix=args.output_prefix,
        symbol=args.symbol,
        timeframe=args.timeframe,
        account_balance=args.account_balance,
    )

    report = build_experiment_report(results)

    write_report(report, Path(args.report_output))
    write_summary_csv(results, Path(args.summary_output))

    print(report)
    print(f"Report saved: {Path(args.report_output).resolve()}")
    print(f"Summary saved: {Path(args.summary_output).resolve()}")


if __name__ == "__main__":
    main()
