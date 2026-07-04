"""
Tests for Strategy Experiment Runner.
"""

from pathlib import Path
import subprocess
import sys

import pytest

from scripts.run_strategy_experiments import (
    ExperimentResult,
    ExperimentSpec,
    best_experiment_results,
    build_argument_parser,
    build_default_experiment_specs,
    build_dry_run_report,
    build_experiment_output_paths,
    build_experiment_report,
    run_experiment_spec,
    sanitize_experiment_name,
    sort_experiment_results,
    worst_experiment_results,
    write_summary_csv,
)
from src.config.strategy_config import supported_strategy_mode_names


def make_experiment_result(
    name: str,
    net_pnl: float,
    return_percent: float,
    total_charges: float = 0.0,
) -> ExperimentResult:
    return ExperimentResult(
        name=name,
        strategy_mode=name.split("_")[0],
        risk_per_trade=0.01,
        reward_to_risk=2.0,
        total_trades=1,
        gross_pnl=net_pnl + total_charges,
        total_charges=total_charges,
        net_pnl=net_pnl,
        ending_balance=10000.0 + net_pnl,
        return_percent=return_percent,
        normalized_output_path=Path(f"{name}_normalized.csv"),
        trades_output_path=Path(f"{name}_trades.csv"),
        equity_output_path=Path(f"{name}_equity.csv"),
    )


def test_build_default_experiment_specs_creates_one_spec_per_mode():
    specs = build_default_experiment_specs(
        risk_per_trade=0.02,
        reward_to_risk=3.0,
    )

    assert tuple(spec.strategy_mode for spec in specs) == supported_strategy_mode_names()
    assert all(spec.risk_per_trade == 0.02 for spec in specs)
    assert all(spec.reward_to_risk == 3.0 for spec in specs)
    assert tuple(spec.name for spec in specs) == (
        "strict_default",
        "balanced_default",
        "relaxed_default",
    )


def test_sanitize_experiment_name_returns_safe_name():
    assert sanitize_experiment_name(" Strict Mode / Test ") == "strict_mode_test"


def test_sanitize_experiment_name_rejects_empty_name():
    try:
        sanitize_experiment_name("   ")
    except ValueError as error:
        assert "Experiment name cannot be empty." in str(error)
    else:
        raise AssertionError("Expected ValueError.")


def test_build_experiment_output_paths_are_deterministic(tmp_path: Path):
    output_paths = build_experiment_output_paths(
        output_dir=tmp_path,
        output_prefix="experiment",
        experiment_name="Strict Mode",
    )

    assert output_paths.normalized_output_path == tmp_path / "experiment_strict_mode_normalized.csv"
    assert output_paths.trades_output_path == tmp_path / "experiment_strict_mode_trades.csv"
    assert output_paths.equity_output_path == tmp_path / "experiment_strict_mode_equity_curve.csv"


def test_build_argument_parser_defaults_to_dry_run():
    args = build_argument_parser().parse_args([])

    assert args.execute is False
    assert args.modes == list(supported_strategy_mode_names())


def test_build_dry_run_report_lists_specs():
    specs = (
        ExperimentSpec(
            name="strict_default",
            strategy_mode="strict",
            risk_per_trade=0.01,
            reward_to_risk=2.0,
        ),
    )

    report = build_dry_run_report(specs)

    assert "Mode: DRY RUN" in report
    assert "No backtests were executed." in report
    assert "strict_default | strict | 0.0100 | 2.00" in report


def test_build_experiment_report_lists_results():
    result = ExperimentResult(
        name="strict_default",
        strategy_mode="strict",
        risk_per_trade=0.01,
        reward_to_risk=2.0,
        total_trades=1,
        gross_pnl=100.0,
        total_charges=10.0,
        net_pnl=90.0,
        ending_balance=10090.0,
        return_percent=0.9,
        normalized_output_path=Path("normalized.csv"),
        trades_output_path=Path("trades.csv"),
        equity_output_path=Path("equity.csv"),
    )

    report = build_experiment_report((result,))

    assert "Hunter Quant Engine - Strategy Experiment Results" in report
    assert "strict_default | strict | 1 | 100.00 | 10.00 | 90.00" in report


def test_write_summary_csv_creates_expected_file(tmp_path: Path):
    output_path = tmp_path / "summary.csv"
    result = ExperimentResult(
        name="balanced_default",
        strategy_mode="balanced",
        risk_per_trade=0.01,
        reward_to_risk=2.0,
        total_trades=1,
        gross_pnl=100.0,
        total_charges=10.0,
        net_pnl=90.0,
        ending_balance=10090.0,
        return_percent=0.9,
        normalized_output_path=Path("normalized.csv"),
        trades_output_path=Path("trades.csv"),
        equity_output_path=Path("equity.csv"),
    )

    write_summary_csv((result,), output_path)

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert lines[0].startswith("name,strategy_mode,risk_per_trade")
    assert "balanced_default,balanced,0.01,2.0,1,100.0,10.0,90.0" in lines[1]


def test_run_experiment_spec_uses_injected_workflow_runner(tmp_path: Path):
    calls = []

    def fake_workflow_runner(**kwargs):
        calls.append(kwargs)

        Path(kwargs["trades_output_path"]).write_text(
            "pnl,total_charges,net_pnl\n"
            "100.0,10.0,90.0\n",
            encoding="utf-8",
        )
        Path(kwargs["equity_output_path"]).write_text(
            "trade_number,ending_balance\n"
            "1,10090.0\n",
            encoding="utf-8",
        )
        Path(kwargs["normalized_output_path"]).write_text(
            "datetime,open,high,low,close,volume\n"
            "2026-01-01 09:15:00,1,1,1,1,1\n",
            encoding="utf-8",
        )

    spec = ExperimentSpec(
        name="balanced_default",
        strategy_mode="balanced",
        risk_per_trade=0.01,
        reward_to_risk=2.0,
    )

    result = run_experiment_spec(
        spec=spec,
        input_path=tmp_path / "input.csv",
        output_dir=tmp_path,
        output_prefix="experiment",
        symbol="NIFTY",
        timeframe="5m",
        account_balance=10000.0,
        workflow_runner=fake_workflow_runner,
    )

    assert len(calls) == 1
    assert calls[0]["strategy_mode"] == "balanced"
    assert calls[0]["risk_per_trade"] == 0.01
    assert calls[0]["reward_to_risk"] == 2.0
    assert result.name == "balanced_default"
    assert result.total_trades == 1
    assert result.gross_pnl == 100.0
    assert result.total_charges == 10.0
    assert result.net_pnl == 90.0
    assert result.ending_balance == 10090.0
    assert result.return_percent == pytest.approx(0.9)


def test_strategy_experiments_script_runs_as_direct_file_in_dry_run():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_strategy_experiments.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "Mode: DRY RUN" in completed.stdout
    assert "No backtests were executed." in completed.stdout


def test_sort_experiment_results_orders_by_net_pnl():
    results = (
        make_experiment_result("strict_default", net_pnl=10.0, return_percent=0.1),
        make_experiment_result("balanced_default", net_pnl=30.0, return_percent=0.3),
        make_experiment_result("relaxed_default", net_pnl=-5.0, return_percent=-0.05),
    )

    sorted_results = sort_experiment_results(results)

    assert tuple(result.name for result in sorted_results) == (
        "balanced_default",
        "strict_default",
        "relaxed_default",
    )


def test_sort_experiment_results_can_sort_ascending_by_return_percent():
    results = (
        make_experiment_result("strict_default", net_pnl=10.0, return_percent=0.1),
        make_experiment_result("balanced_default", net_pnl=30.0, return_percent=0.3),
        make_experiment_result("relaxed_default", net_pnl=-5.0, return_percent=-0.05),
    )

    sorted_results = sort_experiment_results(
        results=results,
        sort_by="return_percent",
        descending=False,
    )

    assert tuple(result.name for result in sorted_results) == (
        "relaxed_default",
        "strict_default",
        "balanced_default",
    )


def test_sort_experiment_results_rejects_unknown_metric():
    results = (
        make_experiment_result("strict_default", net_pnl=10.0, return_percent=0.1),
    )

    try:
        sort_experiment_results(results=results, sort_by="unknown_metric")
    except ValueError as error:
        assert "Unsupported experiment result sort field" in str(error)
    else:
        raise AssertionError("Expected ValueError.")


def test_best_experiment_results_returns_top_limited_results():
    results = (
        make_experiment_result("strict_default", net_pnl=10.0, return_percent=0.1),
        make_experiment_result("balanced_default", net_pnl=30.0, return_percent=0.3),
        make_experiment_result("relaxed_default", net_pnl=-5.0, return_percent=-0.05),
    )

    best_results = best_experiment_results(results=results, limit=2)

    assert tuple(result.name for result in best_results) == (
        "balanced_default",
        "strict_default",
    )


def test_worst_experiment_results_returns_bottom_limited_results():
    results = (
        make_experiment_result("strict_default", net_pnl=10.0, return_percent=0.1),
        make_experiment_result("balanced_default", net_pnl=30.0, return_percent=0.3),
        make_experiment_result("relaxed_default", net_pnl=-5.0, return_percent=-0.05),
    )

    worst_results = worst_experiment_results(results=results, limit=2)

    assert tuple(result.name for result in worst_results) == (
        "relaxed_default",
        "strict_default",
    )


def test_best_and_worst_experiment_results_reject_invalid_limit():
    results = (
        make_experiment_result("strict_default", net_pnl=10.0, return_percent=0.1),
    )

    try:
        best_experiment_results(results=results, limit=0)
    except ValueError as error:
        assert "Best experiment result limit" in str(error)
    else:
        raise AssertionError("Expected ValueError.")

    try:
        worst_experiment_results(results=results, limit=0)
    except ValueError as error:
        assert "Worst experiment result limit" in str(error)
    else:
        raise AssertionError("Expected ValueError.")


def test_build_experiment_report_includes_best_and_worst_sections():
    results = (
        make_experiment_result("strict_default", net_pnl=10.0, return_percent=0.1),
        make_experiment_result("balanced_default", net_pnl=30.0, return_percent=0.3),
        make_experiment_result("relaxed_default", net_pnl=-5.0, return_percent=-0.05),
    )

    report = build_experiment_report(results)

    assert "BEST RESULTS BY NET PNL" in report
    assert "WORST RESULTS BY NET PNL" in report
    assert "balanced_default | balanced | Net PnL: 30.00 | Return %: 0.3000" in report
    assert "relaxed_default | relaxed | Net PnL: -5.00 | Return %: -0.0500" in report


def test_write_summary_csv_sorts_results_by_net_pnl_descending(tmp_path: Path):
    output_path = tmp_path / "summary.csv"
    results = (
        make_experiment_result("strict_default", net_pnl=10.0, return_percent=0.1),
        make_experiment_result("balanced_default", net_pnl=30.0, return_percent=0.3),
        make_experiment_result("relaxed_default", net_pnl=-5.0, return_percent=-0.05),
    )

    write_summary_csv(results, output_path)

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert lines[1].startswith("balanced_default,balanced")
    assert lines[2].startswith("strict_default,strict")
    assert lines[3].startswith("relaxed_default,relaxed")
