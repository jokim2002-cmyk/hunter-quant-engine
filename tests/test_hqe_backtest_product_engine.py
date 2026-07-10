from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_backtest_product_engine.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_dataset(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["datetime", "open", "high", "low", "close", "volume"]
        )
        writer.writerow(["2026-07-10 09:15:00", 100, 102, 99, 101, 10])
        writer.writerow(["2026-07-10 09:20:00", 101, 103, 100, 102, 11])
        writer.writerow(["2026-07-10 09:25:00", 102, 104, 101, 103, 12])


def test_job_spec_validation_with_clean_data(tmp_path):
    module = load("backtest_job_validation")
    dataset = tmp_path / "data.csv"
    write_dataset(dataset)
    strategy = (
        REPO
        / "strategy_packs"
        / "builtin"
        / "hqe_breakout_option_buy.json"
    )
    job = module.create_job_spec(
        dataset_path=dataset,
        strategy_path=strategy,
        start_date="2026-07-01",
        end_date="2026-07-31",
        initial_capital=100000,
        brokerage_per_order=20,
        slippage_bps=5,
        tax_bps=2,
        max_trades_per_day=3,
    )
    validation = module.validate_job_spec(job)
    assert validation["valid"], validation["errors"]
    assert job["mode"] == "RECORDED_DATA_RESEARCH_BACKTEST"
    assert job["real_orders_enabled"] is False


def test_runner_compatibility_and_command_are_guarded(tmp_path):
    module = load("backtest_runner_command")
    repo = tmp_path / "repo"
    venv = repo / ".venv" / "Scripts"
    runner = repo / "scripts" / "sample_backtest.py"
    venv.mkdir(parents=True)
    runner.parent.mkdir(parents=True)
    runner.write_text("print('x')\n", encoding="utf-8")

    dataset = tmp_path / "data.csv"
    write_dataset(dataset)
    strategy = (
        REPO
        / "strategy_packs"
        / "builtin"
        / "hqe_breakout_option_buy.json"
    )
    job = module.create_job_spec(
        dataset_path=dataset,
        strategy_path=strategy,
    )
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")

    help_text = (
        "--guard-check --dataset --strategy-pack --output-dir "
        "--start-date --end-date --initial-capital "
        "--brokerage-per-order --slippage-bps --tax-bps "
        "--max-trades-per-day --recorded-data-only --write"
    )
    compatibility = module.runner_compatibility(
        repo,
        runner,
        help_text=help_text,
    )
    assert compatibility["compatible"] is True

    command = module.build_runner_command(
        repo,
        runner,
        job_path,
        tmp_path / "output",
        help_text=help_text,
    )
    joined = " ".join(command).lower()
    assert "--recorded-data-only" in joined
    assert "--dataset" in joined
    assert "--strategy-pack" in joined
    assert "place_order" not in joined
    assert "broker-execution" not in joined


def test_runner_without_guard_is_rejected(tmp_path):
    module = load("backtest_runner_reject")
    compatibility = module.runner_compatibility(
        tmp_path,
        tmp_path / "runner.py",
        help_text="--dataset --output-dir --write",
    )
    assert compatibility["compatible"] is False


def test_result_normalization_from_trade_csv(tmp_path):
    module = load("backtest_result_normalization")
    output = tmp_path / "run"
    output.mkdir()
    trade_file = output / "BACKTEST_TRADE_LOG.csv"
    with trade_file.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["trade_id", "net_pnl"])
        writer.writerow([1, 100])
        writer.writerow([2, -50])
        writer.writerow([3, 200])

    summary = module.normalize_backtest_results(output)
    metrics = summary["metrics"]
    assert metrics["trade_count"] == 3
    assert metrics["win_count"] == 2
    assert metrics["net_pnl"] == 250.0
    assert metrics["max_drawdown"] == 50.0
    assert Path(
        output / "HQE_BACKTEST_PRODUCT_SUMMARY.json"
    ).exists()


def test_engine_guard_locks_execution():
    module = load("backtest_engine_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["recorded_data_only"] is True
    assert payload["runner_guard_required"] is True
    assert payload["no_fake_option_prices"] is True
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["option_selling_enabled"] is False
