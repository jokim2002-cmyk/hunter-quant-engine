import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_fill_exit_simulator import (
    build_and_write_paper_fill_exit_report,
    build_paper_fill_exit_report,
    safety_notice,
)


def _decision_event(index, close, decision="NEUTRAL"):
    mapping = {
        "LONG": "future_CE_buy_paper_plan_only",
        "SHORT": "future_PE_buy_paper_plan_only",
        "NEUTRAL": "no_trade",
    }[decision]
    return {
        "decision_event_index": index,
        "event_type": "strategy_decision_audit",
        "timestamp": f"2026-01-01T09:{14 + index:02d}:00+05:30",
        "close": close,
        "decision": decision,
        "option_buy_mapping": mapping,
        "decision_mode": "deterministic_close_to_close_audit_only",
        "execution_mode": "paper_backtest_decision_audit_only",
        "trade_plan_mode": "trade_plans_not_created",
        "broker_execution_mode": "broker_disabled",
        "output_mode": "decision_audit_manifest_only",
    }


def _decision_audit(status="pass", ready=True):
    events = [
        _decision_event(1, 100.0, "NEUTRAL"),
        _decision_event(2, 100.0, "LONG"),
        _decision_event(3, 115.0, "LONG"),
        _decision_event(4, 115.0, "SHORT"),
        _decision_event(5, 100.0, "SHORT"),
    ]
    return {
        "status": status,
        "ready_for_future_paper_trade_plan_simulator": ready,
        "decision_event_count": len(events),
        "long_count": 2,
        "short_count": 2,
        "neutral_count": 1,
        "decision_events": events,
    }


def _plan(index, decision):
    option_type = "CE" if decision == "LONG" else "PE"
    source_index = 2 if decision == "LONG" else 4
    close_reference = 100.0 if decision == "LONG" else 115.0
    timestamp = "2026-01-01T09:16:00+05:30" if decision == "LONG" else "2026-01-01T09:18:00+05:30"
    return {
        "paper_trade_plan_index": index,
        "event_type": "paper_option_trade_plan_created",
        "paper_trade_plan_id": f"PAPER-OPTION-PLAN-{index:06d}",
        "source_decision_event_index": source_index,
        "source_path": "sample.csv",
        "source_type": "csv",
        "source_row_number": source_index,
        "timestamp": timestamp,
        "decision": decision,
        "option_type": option_type,
        "option_action": "BUY",
        "option_buy_mapping": (
            "future_CE_buy_paper_plan_only"
            if decision == "LONG"
            else "future_PE_buy_paper_plan_only"
        ),
        "underlying_symbol": "NIFTY",
        "underlying_close_reference": close_reference,
        "quantity_lots": 1,
        "lot_size": 50,
        "stop_loss_points": 5.0,
        "target_points": 10.0,
        "max_holding_bars": 2,
        "plan_mode": "paper_option_buy_plan_only",
        "execution_mode": "paper_backtest_plan_only",
        "fill_mode": "fills_not_simulated",
        "broker_execution_mode": "broker_disabled",
        "order_mode": "orders_not_created",
        "output_mode": "paper_trade_plan_manifest_only",
    }


def _trade_plan_report(status="pass", ready=True, plans=None):
    if plans is None:
        plans = [_plan(1, "LONG"), _plan(2, "SHORT")]
    return {
        "status": status,
        "ready_for_future_paper_fill_simulator": ready,
        "paper_trade_plan_count": len(plans),
        "paper_trade_plans": plans,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _inputs(tmp_path, trade_plan_report=None, decision_audit=None):
    trade_plan_path = _write_json(
        tmp_path / "trade_plan_report.json",
        trade_plan_report or _trade_plan_report(),
    )
    decision_audit_path = _write_json(
        tmp_path / "decision_audit.json",
        decision_audit or _decision_audit(),
    )
    return trade_plan_path, decision_audit_path


def test_safety_notice_preserves_fill_exit_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "entry/exit lifecycle" in notice
    assert "does not connect to brokers" in notice
    assert "calculate account pnl" in notice
    assert "prove profitability" in notice


def test_missing_trade_plan_report_fails(tmp_path):
    _, decision_audit = _inputs(tmp_path)

    report = build_paper_fill_exit_report(
        trade_plan_report_path=tmp_path / "missing.json",
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "trade_plan_report_missing" for issue in report.issues)


def test_missing_decision_audit_fails(tmp_path):
    trade_plan, _ = _inputs(tmp_path)

    report = build_paper_fill_exit_report(
        trade_plan_report_path=trade_plan,
        decision_audit_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_audit_missing" for issue in report.issues)


def test_valid_trade_plans_create_ce_and_pe_fill_exit_lifecycles(tmp_path):
    trade_plan, decision_audit = _inputs(tmp_path)

    report = build_paper_fill_exit_report(
        trade_plan_report_path=trade_plan,
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
        min_lifecycles=2,
    )

    assert report.status == "pass"
    assert report.ready_for_future_backtest_ledger is True
    assert report.paper_fill_exit_lifecycle_count == 2
    assert report.ce_lifecycle_count == 1
    assert report.pe_lifecycle_count == 1
    assert report.target_exit_count == 2
    assert report.paper_fill_exit_lifecycles[0].option_type == "CE"
    assert report.paper_fill_exit_lifecycles[0].exit_reason == "target_points_reached"
    assert report.paper_fill_exit_lifecycles[1].option_type == "PE"
    assert report.paper_fill_exit_lifecycles[1].exit_reason == "target_points_reached"


def test_warning_trade_plan_report_fails_by_default(tmp_path):
    trade_plan, decision_audit = _inputs(
        tmp_path,
        trade_plan_report=_trade_plan_report(status="warn", ready=True),
    )

    report = build_paper_fill_exit_report(
        trade_plan_report_path=trade_plan,
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "trade_plan_report_warn" for issue in report.issues)


def test_warning_trade_plan_report_can_remain_warning_when_allowed(tmp_path):
    trade_plan, decision_audit = _inputs(
        tmp_path,
        trade_plan_report=_trade_plan_report(status="warn", ready=True),
    )

    report = build_paper_fill_exit_report(
        trade_plan_report_path=trade_plan,
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_backtest_ledger is True


def test_trade_plan_not_ready_fails(tmp_path):
    trade_plan, decision_audit = _inputs(
        tmp_path,
        trade_plan_report=_trade_plan_report(status="pass", ready=False),
    )

    report = build_paper_fill_exit_report(
        trade_plan_report_path=trade_plan,
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "trade_plan_report_not_ready" for issue in report.issues)


def test_wrong_plan_modes_fail(tmp_path):
    bad_plan = _plan(1, "LONG")
    bad_plan["broker_execution_mode"] = "enabled"
    trade_plan, decision_audit = _inputs(
        tmp_path,
        trade_plan_report=_trade_plan_report(plans=[bad_plan]),
    )

    report = build_paper_fill_exit_report(
        trade_plan_report_path=trade_plan,
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "paper_trade_plan_wrong_modes" for issue in report.issues)


def test_forbidden_plan_fields_fail(tmp_path):
    bad_plan = _plan(1, "SHORT")
    bad_plan["order_id"] = "not-allowed"
    trade_plan, decision_audit = _inputs(
        tmp_path,
        trade_plan_report=_trade_plan_report(plans=[bad_plan]),
    )

    report = build_paper_fill_exit_report(
        trade_plan_report_path=trade_plan,
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "paper_trade_plan_forbidden_fields" for issue in report.issues)


def test_min_lifecycles_rule_can_fail(tmp_path):
    trade_plan, decision_audit = _inputs(
        tmp_path,
        trade_plan_report=_trade_plan_report(plans=[]),
    )

    report = build_paper_fill_exit_report(
        trade_plan_report_path=trade_plan,
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
        min_lifecycles=1,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_paper_fill_exit_lifecycles" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_fill_exit_simulator(tmp_path):
    trade_plan, decision_audit = _inputs(tmp_path)

    report, outputs = build_and_write_paper_fill_exit_report(
        trade_plan_report_path=trade_plan,
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
        min_lifecycles=2,
    )

    text_report = outputs["paper_fill_exit_simulator_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_FILL_EXIT_SIMULATOR.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_fill_exit_simulator_json"].exists()
    assert outputs["paper_fill_exit_lifecycles_jsonl"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_backtest_ledger"] is True
    assert "hqe_recorded_data_paper_fill_exit_simulator.bat" in combined_docs
    assert "paper entry/exit lifecycle" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()

