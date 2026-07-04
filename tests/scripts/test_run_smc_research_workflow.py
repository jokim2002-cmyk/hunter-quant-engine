"""
Run SMC Research Workflow Script Tests
"""

import csv

from scripts.run_smc_research_workflow import (
    DEFAULT_ACCOUNT_BALANCE,
    DEFAULT_EQUITY_OUTPUT_PATH,
    DEFAULT_INPUT_PATH,
    DEFAULT_NORMALIZED_OUTPUT_PATH,
    DEFAULT_REWARD_TO_RISK,
    DEFAULT_RISK_PER_TRADE,
    DEFAULT_SYMBOL,
    DEFAULT_TIMEFRAME,
    DEFAULT_TRADES_OUTPUT_PATH,
    build_argument_parser,
    build_workflow_summary_report,
    run_workflow,
)


def _read_rows(csv_path):
    with csv_path.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        return tuple(csv.DictReader(csv_file))


def test_build_argument_parser_uses_expected_defaults():
    args = build_argument_parser().parse_args([])

    assert args.input == str(DEFAULT_INPUT_PATH)
    assert args.normalized_output == str(DEFAULT_NORMALIZED_OUTPUT_PATH)
    assert args.trades_output == str(DEFAULT_TRADES_OUTPUT_PATH)
    assert args.equity_output == str(DEFAULT_EQUITY_OUTPUT_PATH)
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
            "data/raw/broker.csv",
            "--normalized-output",
            "data/processed/normalized.csv",
            "--trades-output",
            "data/processed/trades.csv",
            "--equity-output",
            "data/processed/equity_curve.csv",
            "--symbol",
            "BANKNIFTY",
            "--timeframe",
            "15m",
            "--account-balance",
            "50000",
            "--risk-per-trade",
            "0.02",
            "--reward-to-risk",
            "3.0",
            "--datetime-column",
            "Timestamp",
            "--open-column",
            "O",
            "--high-column",
            "H",
            "--low-column",
            "L",
            "--close-column",
            "C",
            "--volume-column",
            "V",
            "--default-volume",
            "100",
        ]
    )

    assert args.input == "data/raw/broker.csv"
    assert args.normalized_output == "data/processed/normalized.csv"
    assert args.trades_output == "data/processed/trades.csv"
    assert args.equity_output == "data/processed/equity_curve.csv"
    assert args.symbol == "BANKNIFTY"
    assert args.timeframe == "15m"
    assert args.account_balance == 50000.0
    assert args.risk_per_trade == 0.02
    assert args.reward_to_risk == 3.0
    assert args.datetime_column == "Timestamp"
    assert args.open_column == "O"
    assert args.high_column == "H"
    assert args.low_column == "L"
    assert args.close_column == "C"
    assert args.volume_column == "V"
    assert args.default_volume == 100.0


def test_run_workflow_creates_normalized_trade_and_equity_files(tmp_path):
    input_path = tmp_path / "raw.csv"
    normalized_output_path = tmp_path / "processed" / "normalized.csv"
    trades_output_path = tmp_path / "processed" / "trades.csv"
    equity_output_path = tmp_path / "processed" / "equity_curve.csv"

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

    summary = run_workflow(
        input_path=input_path,
        normalized_output_path=normalized_output_path,
        trades_output_path=trades_output_path,
        equity_output_path=equity_output_path,
        symbol="TEST",
        timeframe="5m",
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
    )

    normalized_rows = _read_rows(normalized_output_path)
    trade_rows = _read_rows(trades_output_path)
    equity_rows = _read_rows(equity_output_path)

    assert summary.input_path == input_path
    assert summary.normalized_output_path == normalized_output_path
    assert summary.trades_output_path == trades_output_path
    assert summary.equity_output_path == equity_output_path
    assert summary.symbol == "TEST"
    assert summary.timeframe == "5m"
    assert summary.normalization_summary.rows_written == 2
    assert summary.inspection_summary.ready_for_hqe is True
    assert summary.diagnostic_summary.candles_loaded == 2
    assert summary.backtest_result.performance_summary.total_trades == 0
    assert normalized_output_path.exists()
    assert trades_output_path.exists()
    assert equity_output_path.exists()
    assert len(normalized_rows) == 2
    assert trade_rows == ()
    assert equity_rows == ()


def test_run_workflow_supports_broker_column_mapping(tmp_path):
    input_path = tmp_path / "broker.csv"
    normalized_output_path = tmp_path / "processed" / "normalized.csv"
    trades_output_path = tmp_path / "processed" / "trades.csv"
    equity_output_path = tmp_path / "processed" / "equity_curve.csv"

    input_path.write_text(
        "\n".join(
            [
                "Date,Time,Open,High,Low,Close",
                "01-01-2026,09:15:00,100.0,105.0,95.0,102.0",
            ]
        ),
        encoding="utf-8",
    )

    summary = run_workflow(
        input_path=input_path,
        normalized_output_path=normalized_output_path,
        trades_output_path=trades_output_path,
        equity_output_path=equity_output_path,
        symbol="TEST",
        timeframe="5m",
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
        default_volume=10.0,
    )

    rows = _read_rows(normalized_output_path)

    assert summary.normalization_summary.date_column == "Date"
    assert summary.normalization_summary.time_column == "Time"
    assert summary.normalization_summary.volume_column is None
    assert summary.inspection_summary.ready_for_hqe is True
    assert rows[0]["datetime"] == "2026-01-01T09:15:00"
    assert rows[0]["volume"] == "10.0"


def test_build_workflow_summary_report_includes_key_metrics(tmp_path):
    input_path = tmp_path / "raw.csv"
    normalized_output_path = tmp_path / "processed" / "normalized.csv"
    trades_output_path = tmp_path / "processed" / "trades.csv"
    equity_output_path = tmp_path / "processed" / "equity_curve.csv"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = run_workflow(
        input_path=input_path,
        normalized_output_path=normalized_output_path,
        trades_output_path=trades_output_path,
        equity_output_path=equity_output_path,
        symbol="TEST",
        timeframe="5m",
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
    )

    report = build_workflow_summary_report(summary)

    assert "Hunter Quant Engine - SMC Research Workflow Summary" in report
    assert "Input CSV:" in report
    assert "Normalized CSV:" in report
    assert "Trades CSV:" in report
    assert "Equity Curve CSV:" in report
    assert "Rows Normalized: 1" in report
    assert "Ready For HQE: True" in report
    assert "Candles Loaded: 1" in report
    assert "Total Trades: 0" in report
    assert "Total PnL: 0.0" in report

def test_build_argument_parser_accepts_transaction_cost_values():
    args = build_argument_parser().parse_args(
        [
            "--brokerage-per-order",
            "20",
            "--stt-rate",
            "0.00025",
            "--exchange-transaction-charge-rate",
            "0.0000325",
            "--sebi-charge-rate",
            "0.000001",
            "--stamp-duty-rate",
            "0.00003",
            "--gst-rate",
            "0.18",
        ]
    )

    assert args.brokerage_per_order == 20.0
    assert args.stt_rate == 0.00025
    assert args.exchange_transaction_charge_rate == 0.0000325
    assert args.sebi_charge_rate == 0.000001
    assert args.stamp_duty_rate == 0.00003
    assert args.gst_rate == 0.18

def test_build_argument_parser_accepts_fyers_cost_profile():
    args = build_argument_parser().parse_args(
        [
            "--cost-profile",
            "fyers-equity-intraday",
        ]
    )

    assert args.cost_profile == "fyers-equity-intraday"
