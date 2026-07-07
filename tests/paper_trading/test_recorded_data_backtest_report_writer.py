import json
from pathlib import Path

from src.paper_trading.recorded_data_backtest_report_writer import (
    build_and_write_backtest_report_writer_report,
    build_backtest_report_writer_report,
    safety_notice,
)


def _metrics(status="pass", ready=True, trades=3):
    return {
        "status": status,
        "ready_for_future_backtest_report_writer": ready,
        "metric_trade_count": trades,
        "winning_trade_count": 1,
        "losing_trade_count": 1,
        "flat_trade_count": 1,
        "win_rate_percent": 33.3333333333,
        "loss_rate_percent": 33.3333333333,
        "flat_rate_percent": 33.3333333333,
        "simulated_gross_result_total": 250.0,
        "average_trade_result": 83.3333333333,
        "largest_winning_trade_result": 500.0,
        "largest_losing_trade_result": -250.0,
        "final_equity_reference": 100250.0,
        "max_drawdown_reference": 250.0,
        "max_drawdown_percent_reference": 0.2493765586,
        "equity_curve": [],
    }


def _ledger_row(index, result):
    return {
        "ledger_row_index": index,
        "trade_id": f"PAPER-BACKTEST-TRADE-{index:06d}",
        "decision": "LONG" if result >= 0 else "SHORT",
        "option_type": "CE" if result >= 0 else "PE",
        "simulated_gross_result": result,
        "outcome": "WIN" if result > 0 else "LOSS" if result < 0 else "FLAT",
        "exit_timestamp": f"2026-01-01T09:{18 + index:02d}:00+05:30",
        "broker_execution_mode": "broker_disabled",
        "order_mode": "orders_not_created",
        "money_mode": "real_money_not_used",
    }


def _ledger(status="pass", ready=True, rows=None):
    if rows is None:
        rows = [_ledger_row(1, 500.0), _ledger_row(2, -250.0), _ledger_row(3, 0.0)]
    return {
        "status": status,
        "ready_for_future_backtest_metrics_engine": ready,
        "ledger_trade_count": len(rows),
        "ledger_rows": rows,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _inputs(tmp_path, metrics=None, ledger=None):
    metrics_path = _write_json(tmp_path / "metrics.json", metrics or _metrics())
    ledger_path = _write_json(tmp_path / "ledger.json", ledger or _ledger())
    return metrics_path, ledger_path


def test_safety_notice_preserves_report_writer_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation backtest report" in notice
    assert "simulated reference values" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_metrics_fails(tmp_path):
    _, ledger_path = _inputs(tmp_path)

    report = build_backtest_report_writer_report(
        metrics_path=tmp_path / "missing.json",
        trade_ledger_path=ledger_path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "backtest_metrics_missing" for issue in report.issues)


def test_missing_trade_ledger_fails(tmp_path):
    metrics_path, _ = _inputs(tmp_path)

    report = build_backtest_report_writer_report(
        metrics_path=metrics_path,
        trade_ledger_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "trade_ledger_missing" for issue in report.issues)


def test_valid_metrics_and_ledger_create_report_summary(tmp_path):
    metrics_path, ledger_path = _inputs(tmp_path)

    report = build_backtest_report_writer_report(
        metrics_path=metrics_path,
        trade_ledger_path=ledger_path,
        output_dir=tmp_path / "out",
        min_trades=3,
    )

    assert report.status == "pass"
    assert report.ready_for_future_one_command_backtest_runner is True
    assert report.summary.metric_trade_count == 3
    assert report.summary.winning_trade_count == 1
    assert report.summary.losing_trade_count == 1
    assert report.summary.simulated_gross_result_total == 250.0
    assert "LONG=CE BUY" in report.strategy_scope
    assert "SHORT=PE BUY" in report.strategy_scope
    assert "NEUTRAL=no trade" in report.strategy_scope


def test_warning_metrics_fails_by_default(tmp_path):
    metrics_path, ledger_path = _inputs(tmp_path, metrics=_metrics(status="warn", ready=True))

    report = build_backtest_report_writer_report(
        metrics_path=metrics_path,
        trade_ledger_path=ledger_path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "backtest_metrics_warn" for issue in report.issues)


def test_warning_metrics_can_remain_warning_when_allowed(tmp_path):
    metrics_path, ledger_path = _inputs(tmp_path, metrics=_metrics(status="warn", ready=True))

    report = build_backtest_report_writer_report(
        metrics_path=metrics_path,
        trade_ledger_path=ledger_path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_one_command_backtest_runner is True


def test_not_ready_metrics_fails(tmp_path):
    metrics_path, ledger_path = _inputs(tmp_path, metrics=_metrics(status="pass", ready=False))

    report = build_backtest_report_writer_report(
        metrics_path=metrics_path,
        trade_ledger_path=ledger_path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "backtest_metrics_not_ready" for issue in report.issues)


def test_trade_count_mismatch_fails(tmp_path):
    metrics_path, ledger_path = _inputs(
        tmp_path,
        metrics=_metrics(trades=2),
        ledger=_ledger(rows=[_ledger_row(1, 500.0), _ledger_row(2, -250.0), _ledger_row(3, 0.0)]),
    )

    report = build_backtest_report_writer_report(
        metrics_path=metrics_path,
        trade_ledger_path=ledger_path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "metric_ledger_trade_count_mismatch" for issue in report.issues)


def test_forbidden_metrics_fields_fail(tmp_path):
    bad_metrics = _metrics()
    bad_metrics["order_id"] = "not-allowed"
    metrics_path, ledger_path = _inputs(tmp_path, metrics=bad_metrics)

    report = build_backtest_report_writer_report(
        metrics_path=metrics_path,
        trade_ledger_path=ledger_path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "backtest_metrics_forbidden_fields" for issue in report.issues)


def test_min_trades_rule_can_fail(tmp_path):
    metrics_path, ledger_path = _inputs(
        tmp_path,
        metrics=_metrics(trades=0),
        ledger=_ledger(rows=[]),
    )

    report = build_backtest_report_writer_report(
        metrics_path=metrics_path,
        trade_ledger_path=ledger_path,
        output_dir=tmp_path / "out",
        min_trades=1,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_metric_trades" for issue in report.issues)
    assert any(issue.code == "insufficient_ledger_trades" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_report_writer(tmp_path):
    metrics_path, ledger_path = _inputs(tmp_path)

    report, outputs = build_and_write_backtest_report_writer_report(
        metrics_path=metrics_path,
        trade_ledger_path=ledger_path,
        output_dir=tmp_path / "out",
        min_trades=3,
    )

    text_report = outputs["backtest_report_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_DATA_BACKTEST_REPORT_WRITER.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["backtest_report_json"].exists()
    assert outputs["backtest_report_summary_csv"].exists()
    assert outputs["backtest_report_trade_preview_jsonl"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_one_command_backtest_runner"] is True
    assert "hqe_recorded_data_backtest_report_writer.bat" in combined_docs
    assert "paper-only backtest report" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
