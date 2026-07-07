import json
from pathlib import Path

from src.paper_trading.recorded_data_backtest_trade_ledger import (
    build_and_write_backtest_trade_ledger_report,
    build_backtest_trade_ledger_report,
    safety_notice,
)


def _lifecycle(index, option_type="CE", points=10.0):
    decision = "LONG" if option_type == "CE" else "SHORT"
    return {
        "paper_fill_exit_index": index,
        "event_type": "paper_option_fill_exit_lifecycle_created",
        "paper_fill_exit_id": f"PAPER-FILL-EXIT-{index:06d}",
        "source_paper_trade_plan_id": f"PAPER-OPTION-PLAN-{index:06d}",
        "source_paper_trade_plan_index": index,
        "source_decision_event_index": index + 1,
        "underlying_symbol": "NIFTY",
        "decision": decision,
        "option_type": option_type,
        "option_action": "BUY",
        "entry_timestamp": "2026-01-01T09:15:00+05:30",
        "exit_timestamp": "2026-01-01T09:18:00+05:30",
        "entry_underlying_close_reference": 100.0,
        "exit_underlying_close_reference": 110.0,
        "entry_option_price_reference": 100.0,
        "exit_option_price_reference": 100.0 + points,
        "option_points_result": points,
        "exit_reason": "target_points_reached" if points > 0 else "stop_loss_points_reached",
        "holding_bars": 2,
        "quantity_lots": 1,
        "lot_size": 50,
        "stop_loss_points": 5.0,
        "target_points": 10.0,
        "lifecycle_mode": "paper_fill_exit_lifecycle_only",
        "fill_mode": "paper_fills_simulated_from_recorded_replay_references",
        "broker_execution_mode": "broker_disabled",
        "order_mode": "orders_not_created",
        "account_pnl_mode": "account_pnl_not_calculated",
        "output_mode": "paper_fill_exit_manifest_only",
    }


def _fill_exit_report(status="pass", ready=True, lifecycles=None):
    if lifecycles is None:
        lifecycles = [
            _lifecycle(1, "CE", 10.0),
            _lifecycle(2, "PE", -5.0),
            _lifecycle(3, "CE", 0.0),
        ]
    return {
        "status": status,
        "ready_for_future_backtest_ledger": ready,
        "paper_fill_exit_lifecycle_count": len(lifecycles),
        "paper_fill_exit_lifecycles": lifecycles,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_paper_ledger_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation backtest trade ledger" in notice
    assert "simulated paper reference amounts" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_fill_exit_report_fails(tmp_path):
    report = build_backtest_trade_ledger_report(
        fill_exit_report_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "fill_exit_report_missing" for issue in report.issues)


def test_valid_fill_exit_lifecycles_create_ledger_rows(tmp_path):
    fill_exit = _write_json(tmp_path / "fill_exit.json", _fill_exit_report())

    report = build_backtest_trade_ledger_report(
        fill_exit_report_path=fill_exit,
        output_dir=tmp_path / "out",
        min_trades=3,
    )

    assert report.status == "pass"
    assert report.ready_for_future_backtest_metrics_engine is True
    assert report.ledger_trade_count == 3
    assert report.ce_trade_count == 2
    assert report.pe_trade_count == 1
    assert report.winning_trade_count == 1
    assert report.losing_trade_count == 1
    assert report.flat_trade_count == 1
    assert report.gross_option_points_result == 5.0
    assert report.simulated_gross_result_total == 250.0
    assert report.ledger_rows[0].outcome == "WIN"
    assert report.ledger_rows[1].outcome == "LOSS"
    assert report.ledger_rows[2].outcome == "FLAT"


def test_warning_fill_exit_report_fails_by_default(tmp_path):
    fill_exit = _write_json(
        tmp_path / "fill_exit.json",
        _fill_exit_report(status="warn", ready=True),
    )

    report = build_backtest_trade_ledger_report(
        fill_exit_report_path=fill_exit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "fill_exit_report_warn" for issue in report.issues)


def test_warning_fill_exit_report_can_remain_warning_when_allowed(tmp_path):
    fill_exit = _write_json(
        tmp_path / "fill_exit.json",
        _fill_exit_report(status="warn", ready=True),
    )

    report = build_backtest_trade_ledger_report(
        fill_exit_report_path=fill_exit,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_backtest_metrics_engine is True


def test_not_ready_fill_exit_report_fails(tmp_path):
    fill_exit = _write_json(
        tmp_path / "fill_exit.json",
        _fill_exit_report(status="pass", ready=False),
    )

    report = build_backtest_trade_ledger_report(
        fill_exit_report_path=fill_exit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "fill_exit_report_not_ready" for issue in report.issues)


def test_wrong_lifecycle_modes_fail(tmp_path):
    bad_lifecycle = _lifecycle(1, "CE", 10.0)
    bad_lifecycle["broker_execution_mode"] = "enabled"
    fill_exit = _write_json(
        tmp_path / "fill_exit.json",
        _fill_exit_report(lifecycles=[bad_lifecycle]),
    )

    report = build_backtest_trade_ledger_report(
        fill_exit_report_path=fill_exit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "paper_fill_exit_lifecycle_wrong_modes" for issue in report.issues)


def test_wrong_option_type_fails(tmp_path):
    bad_lifecycle = _lifecycle(1, "CE", 10.0)
    bad_lifecycle["decision"] = "SHORT"
    fill_exit = _write_json(
        tmp_path / "fill_exit.json",
        _fill_exit_report(lifecycles=[bad_lifecycle]),
    )

    report = build_backtest_trade_ledger_report(
        fill_exit_report_path=fill_exit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "paper_fill_exit_lifecycle_wrong_option_type" for issue in report.issues)


def test_forbidden_lifecycle_fields_fail(tmp_path):
    bad_lifecycle = _lifecycle(1, "PE", 10.0)
    bad_lifecycle["order_id"] = "not-allowed"
    fill_exit = _write_json(
        tmp_path / "fill_exit.json",
        _fill_exit_report(lifecycles=[bad_lifecycle]),
    )

    report = build_backtest_trade_ledger_report(
        fill_exit_report_path=fill_exit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "paper_fill_exit_lifecycle_forbidden_fields" for issue in report.issues)


def test_min_trades_rule_can_fail(tmp_path):
    fill_exit = _write_json(
        tmp_path / "fill_exit.json",
        _fill_exit_report(lifecycles=[]),
    )

    report = build_backtest_trade_ledger_report(
        fill_exit_report_path=fill_exit,
        output_dir=tmp_path / "out",
        min_trades=1,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_backtest_ledger_trades" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_trade_ledger(tmp_path):
    fill_exit = _write_json(tmp_path / "fill_exit.json", _fill_exit_report())

    report, outputs = build_and_write_backtest_trade_ledger_report(
        fill_exit_report_path=fill_exit,
        output_dir=tmp_path / "out",
        min_trades=3,
    )

    text_report = outputs["backtest_trade_ledger_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_DATA_BACKTEST_TRADE_LEDGER.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["backtest_trade_ledger_json"].exists()
    assert outputs["backtest_trade_ledger_rows_jsonl"].exists()
    assert outputs["backtest_trade_ledger_rows_csv"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_backtest_metrics_engine"] is True
    assert "hqe_recorded_data_backtest_trade_ledger.bat" in combined_docs
    assert "paper-only backtest ledger" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
