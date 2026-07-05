"""
Run FYERS NIFTY Research Script Tests
"""

import csv
from pathlib import Path

from scripts.run_fyers_nifty_research import (
    DEFAULT_ACCOUNT_BALANCE,
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OUTPUT_PREFIX,
    DEFAULT_REWARD_TO_RISK,
    DEFAULT_RISK_PER_TRADE,
    DEFAULT_SYMBOL,
    DEFAULT_TIMEFRAME,
    build_argument_parser,
    build_output_paths,
    run_fyers_nifty_research,
)
from src.costs.transaction_cost_profile_preset import (
    COST_PROFILE_FYERS_EQUITY_INTRADAY,
)


def _read_rows(csv_path: Path):
    with csv_path.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        return tuple(csv.DictReader(csv_file))


def test_build_argument_parser_uses_expected_defaults():
    args = build_argument_parser().parse_args([])

    assert args.input == str(DEFAULT_INPUT_PATH)
    assert args.output_dir == str(DEFAULT_OUTPUT_DIR)
    assert args.output_prefix == DEFAULT_OUTPUT_PREFIX
    assert args.symbol == DEFAULT_SYMBOL
    assert args.timeframe == DEFAULT_TIMEFRAME
    assert args.account_balance == DEFAULT_ACCOUNT_BALANCE
    assert args.risk_per_trade == DEFAULT_RISK_PER_TRADE
    assert args.reward_to_risk == DEFAULT_REWARD_TO_RISK
    assert args.datetime_column is None
    assert args.default_volume == 0.0


def test_build_argument_parser_accepts_custom_values():
    args = build_argument_parser().parse_args(
        [
            "--input",
            "data/raw/custom_fyers.csv",
            "--output-dir",
            "data/processed/custom",
            "--output-prefix",
            "custom_nifty",
            "--symbol",
            "BANKNIFTY",
            "--timeframe",
            "15m",
            "--account-balance",
            "25000",
            "--risk-per-trade",
            "0.02",
            "--reward-to-risk",
            "3.0",
            "--datetime-column",
            "Datetime",
            "--open-column",
            "Open",
            "--high-column",
            "High",
            "--low-column",
            "Low",
            "--close-column",
            "Close",
            "--volume-column",
            "Volume",
            "--default-volume",
            "100",
        ]
    )

    assert args.input == "data/raw/custom_fyers.csv"
    assert args.output_dir == "data/processed/custom"
    assert args.output_prefix == "custom_nifty"
    assert args.symbol == "BANKNIFTY"
    assert args.timeframe == "15m"
    assert args.account_balance == 25000.0
    assert args.risk_per_trade == 0.02
    assert args.reward_to_risk == 3.0
    assert args.datetime_column == "Datetime"
    assert args.open_column == "Open"
    assert args.high_column == "High"
    assert args.low_column == "Low"
    assert args.close_column == "Close"
    assert args.volume_column == "Volume"
    assert args.default_volume == 100.0


def test_build_output_paths_uses_output_prefix(tmp_path):
    output_paths = build_output_paths(
        output_dir=tmp_path,
        output_prefix="fyers_nifty_test",
    )

    assert output_paths.normalized_output_path == (
        tmp_path / "fyers_nifty_test_normalized.csv"
    )
    assert output_paths.trades_output_path == (
        tmp_path / "fyers_nifty_test_trades.csv"
    )
    assert output_paths.equity_output_path == (
        tmp_path / "fyers_nifty_test_equity_curve.csv"
    )


def test_run_fyers_nifty_research_uses_fyers_profile_and_creates_outputs(tmp_path):
    input_path = tmp_path / "fyers_raw.csv"
    output_dir = tmp_path / "processed"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
                "2026-01-01T09:20:00,102.0,106.0,101.0,104.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = run_fyers_nifty_research(
        input_path=input_path,
        output_dir=output_dir,
        output_prefix="fyers_test",
        symbol="NIFTY",
        timeframe="5m",
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
    )
    output_paths = build_output_paths(
        output_dir=output_dir,
        output_prefix="fyers_test",
    )

    normalized_rows = _read_rows(output_paths.normalized_output_path)
    trade_rows = _read_rows(output_paths.trades_output_path)
    equity_rows = _read_rows(output_paths.equity_output_path)

    assert summary.symbol == "NIFTY"
    assert summary.timeframe == "5m"
    assert summary.transaction_cost_profile.brokerage_rate == 0.0003
    assert summary.transaction_cost_profile.brokerage_cap_per_order == 20.0
    assert summary.transaction_cost_profile.stt_rate == 0.00025
    assert summary.transaction_cost_profile.gst_rate == 0.18
    assert summary.transaction_cost_profile == summary.transaction_cost_profile
    assert summary.normalization_summary.rows_written == 2
    assert summary.inspection_summary.ready_for_hqe is True
    assert summary.diagnostic_summary.candles_loaded == 2
    assert output_paths.normalized_output_path.exists()
    assert output_paths.trades_output_path.exists()
    assert output_paths.equity_output_path.exists()
    assert len(normalized_rows) == 2
    assert trade_rows == ()
    assert equity_rows == ()
    assert COST_PROFILE_FYERS_EQUITY_INTRADAY == "fyers-equity-intraday"

def test_build_argument_parser_accepts_max_candles():
    args = build_argument_parser().parse_args(
        [
            "--max-candles",
            "250",
        ]
    )

    assert args.max_candles == 250


def test_run_fyers_nifty_research_limits_to_latest_max_candles(tmp_path):
    input_path = tmp_path / "fyers_raw.csv"
    output_dir = tmp_path / "processed"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,101.0,1000",
                "2026-01-01T09:20:00,101.0,106.0,96.0,102.0,1000",
                "2026-01-01T09:25:00,102.0,107.0,97.0,103.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = run_fyers_nifty_research(
        input_path=input_path,
        output_dir=output_dir,
        output_prefix="fyers_test",
        symbol="NIFTY",
        timeframe="5m",
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
        max_candles=2,
    )
    output_paths = build_output_paths(
        output_dir=output_dir,
        output_prefix="fyers_test",
    )

    rows = _read_rows(output_paths.normalized_output_path)

    assert summary.max_candles == 2
    assert summary.diagnostic_summary.candles_loaded == 2
    assert len(rows) == 2
    assert rows[0]["datetime"] == "2026-01-01T09:20:00"
    assert rows[1]["datetime"] == "2026-01-01T09:25:00"

def test_build_argument_parser_accepts_date_range():
    args = build_argument_parser().parse_args(
        [
            "--start-date",
            "2026-01-02",
            "--end-date",
            "2026-01-03",
        ]
    )

    assert args.start_date == "2026-01-02"
    assert args.end_date == "2026-01-03"


def test_run_fyers_nifty_research_filters_by_date_range(tmp_path):
    input_path = tmp_path / "fyers_raw.csv"
    output_dir = tmp_path / "processed"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,101.0,1000",
                "2026-01-02T09:15:00,101.0,106.0,96.0,102.0,1000",
                "2026-01-03T09:15:00,102.0,107.0,97.0,103.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = run_fyers_nifty_research(
        input_path=input_path,
        output_dir=output_dir,
        output_prefix="fyers_test",
        symbol="NIFTY",
        timeframe="5m",
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
        start_date="2026-01-02",
        end_date="2026-01-03",
    )
    output_paths = build_output_paths(
        output_dir=output_dir,
        output_prefix="fyers_test",
    )

    rows = _read_rows(output_paths.normalized_output_path)

    assert summary.start_date == "2026-01-02"
    assert summary.end_date == "2026-01-03"
    assert summary.diagnostic_summary.candles_loaded == 2
    assert len(rows) == 2
    assert rows[0]["datetime"] == "2026-01-02T09:15:00"
    assert rows[1]["datetime"] == "2026-01-03T09:15:00"
