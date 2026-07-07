import json
from pathlib import Path

from src.paper_trading.recorded_data_backtest_metrics_engine import (
    build_and_write_backtest_metrics_report,
    build_backtest_metrics_report,
    safety_notice,
)


def _ledger_row(index, result, option_type="CE"):
    decision = "LONG" if option_type == "CE" else "SHORT"
    outcome = "WIN" if result > 0 else "LOSS" if result < 0 else "FLAT"
    points = result / 50
    return {
        "ledger_row_index": index,
        "event_type": "paper_backtest_trade_ledger_row_created",
        "trade_id": f"PAPER-BACKTEST-TRADE-{index:06d}",
        "source_paper_fill_exit_id": f"PAPER-FILL-EXIT-{index:06d}",
        "source_paper_trade_plan_id": f"PAPER-OPTION-PLAN-{index:06d}",
        "source_decision_event_index": index + 1,
        "underlying_symbol": "NIFTY",
        "decision": decision,
        "option_type": option_type,
        "option_action": "BUY",
        "entry_timestamp": "2026-01-01T09:15:00+05:30",
        "exit_timestamp": f"2026-01-01T09:{18 + index:02d}:00+05:30",
        "entry_option_price_reference": 100.0,
        "exit_option_price_reference": 100.0 + points,
        "option_points_result": points,
        "quantity_lots": 1,
        "lot_size": 50,
        "simulated_gross_result": result,
        "outcome": outcome,
        "exit_reason": "target_points_reached" if result > 0 else "stop_loss_points_reached",
        "holding_bars": 2,
        "ledger_mode": "paper_backtest_trade_ledger_only",
        "result_mode": "simulated_paper_reference_result_only",
        "broker_execution_mode": "broker_disabled",
        "order_mode": "orders_not_created",
        "money_mode": "real_money_not_used",
        "output_mode": "paper_backtest_trade_ledger_manifest_only",
    }


def _ledger_report(status="pass", ready=True, rows=None):
    if rows is None:
        rows = [
            _ledger_row(1, 500.0, "CE"),
            _ledger_row(2, -250.0, "PE"),
            _ledger_row(3, 0.0, "CE"),
        ]
    return {
        "status": status,
        "ready_for_future_backtest_metrics_engine": ready,
        "ledger_trade_count": len(rows),
        "ledger_rows": rows,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_paper_metrics_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation backtest metrics" in notice
    assert "simulated reference values" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_trade_ledger_fails(tmp_path):
    report = build_backtest_metrics_report(
        trade_ledger_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "trade_ledger_missing" for issue in report.issues)


def test_valid_trade_ledger_creates_metrics_and_equity_curve(tmp_path):
    ledger = _write_json(tmp_path / "ledger.json", _ledger_report())

    report = build_backtest_metrics_report(
        trade_ledger_path=ledger,
        output_dir=tmp_path / "out",
        min_trades=3,
        starting_equity_reference=100000.0,
    )

    assert report.status == "pass"
    assert report.ready_for_future_backtest_report_writer is True
    assert report.metric_trade_count == 3
    assert report.winning_trade_count == 1
    assert report.losing_trade_count == 1
    assert report.flat_trade_count == 1
    assert report.win_rate_percent == 33.3333333333
    assert report.loss_rate_percent == 33.3333333333
    assert report.simulated_gross_result_total == 250.0
    assert report.average_trade_result == 83.3333333333
    assert report.final_equity_reference == 100250.0
    assert report.max_drawdown_reference == 250.0
    assert len(report.equity_curve) == 3


def test_warning_trade_ledger_fails_by_default(tmp_path):
    ledger = _write_json(
        tmp_path / "ledger.json",
        _ledger_report(status="warn", ready=True),
    )

    report = build_backtest_metrics_report(
        trade_ledger_path=ledger,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "trade_ledger_warn" for issue in report.issues)


def test_warning_trade_ledger_can_remain_warning_when_allowed(tmp_path):
    ledger = _write_json(
        tmp_path / "ledger.json",
        _ledger_report(status="warn", ready=True),
    )

    report = build_backtest_metrics_report(
        trade_ledger_path=ledger,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_backtest_report_writer is True


def test_not_ready_trade_ledger_fails(tmp_path):
    ledger = _write_json(
        tmp_path / "ledger.json",
        _ledger_report(status="pass", ready=False),
    )

    report = build_backtest_metrics_report(
        trade_ledger_path=ledger,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "trade_ledger_not_ready" for issue in report.issues)


def test_wrong_ledger_row_modes_fail(tmp_path):
    bad_row = _ledger_row(1, 500.0, "CE")
    bad_row["broker_execution_mode"] = "enabled"
    ledger = _write_json(
        tmp_path / "ledger.json",
        _ledger_report(rows=[bad_row]),
    )

    report = build_backtest_metrics_report(
        trade_ledger_path=ledger,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "ledger_row_wrong_modes" for issue in report.issues)


def test_missing_numeric_ledger_row_fields_fail(tmp_path):
    bad_row = _ledger_row(1, 500.0, "CE")
    bad_row.pop("simulated_gross_result")
    ledger = _write_json(
        tmp_path / "ledger.json",
        _ledger_report(rows=[bad_row]),
    )

    report = build_backtest_metrics_report(
        trade_ledger_path=ledger,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "ledger_row_missing_numeric_fields" for issue in report.issues)


def test_forbidden_ledger_row_fields_fail(tmp_path):
    bad_row = _ledger_row(1, 500.0, "PE")
    bad_row["order_id"] = "not-allowed"
    ledger = _write_json(
        tmp_path / "ledger.json",
        _ledger_report(rows=[bad_row]),
    )

    report = build_backtest_metrics_report(
        trade_ledger_path=ledger,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "ledger_row_forbidden_fields" for issue in report.issues)


def test_min_trades_rule_can_fail(tmp_path):
    ledger = _write_json(
        tmp_path / "ledger.json",
        _ledger_report(rows=[]),
    )

    report = build_backtest_metrics_report(
        trade_ledger_path=ledger,
        output_dir=tmp_path / "out",
        min_trades=1,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_backtest_metric_trades" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_metrics_engine(tmp_path):
    ledger = _write_json(tmp_path / "ledger.json", _ledger_report())

    report, outputs = build_and_write_backtest_metrics_report(
        trade_ledger_path=ledger,
        output_dir=tmp_path / "out",
        min_trades=3,
    )

    text_report = outputs["backtest_metrics_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_DATA_BACKTEST_METRICS_ENGINE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["backtest_metrics_json"].exists()
    assert outputs["backtest_equity_curve_jsonl"].exists()
    assert outputs["backtest_equity_curve_csv"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_backtest_report_writer"] is True
    assert "hqe_recorded_data_backtest_metrics_engine.bat" in combined_docs
    assert "paper-only backtest metrics" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
