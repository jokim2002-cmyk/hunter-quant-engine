import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_option_trade_plan_simulator import (
    build_and_write_paper_option_trade_plan_report,
    build_paper_option_trade_plan_report,
    safety_notice,
)


def _decision_event(index, decision):
    mapping = {
        "LONG": "future_CE_buy_paper_plan_only",
        "SHORT": "future_PE_buy_paper_plan_only",
        "NEUTRAL": "no_trade",
    }[decision]
    return {
        "decision_event_index": index,
        "event_type": "strategy_decision_audit",
        "source_sandbox_event_index": index,
        "source_path": "sample.csv",
        "source_type": "csv",
        "source_row_number": index,
        "timestamp": f"2026-01-01T09:{14 + index:02d}:00+05:30",
        "close": 100.0 + index,
        "previous_close": None if index == 1 else 100.0,
        "close_change": None if index == 1 else 1.0,
        "decision": decision,
        "decision_reason": "test_reason",
        "decision_mode": "deterministic_close_to_close_audit_only",
        "option_buy_mapping": mapping,
        "execution_mode": "paper_backtest_decision_audit_only",
        "trade_plan_mode": "trade_plans_not_created",
        "broker_execution_mode": "broker_disabled",
        "output_mode": "decision_audit_manifest_only",
    }


def _decision_audit(status="pass", ready=True, events=None):
    events = events or [
        _decision_event(1, "NEUTRAL"),
        _decision_event(2, "LONG"),
        _decision_event(3, "SHORT"),
    ]
    return {
        "status": status,
        "ready_for_future_paper_trade_plan_simulator": ready,
        "decision_event_count": len(events),
        "long_count": sum(1 for event in events if event.get("decision") == "LONG"),
        "short_count": sum(1 for event in events if event.get("decision") == "SHORT"),
        "neutral_count": sum(1 for event in events if event.get("decision") == "NEUTRAL"),
        "decision_events": events,
    }


def _acceptance(status="pass", accepted=True):
    return {
        "status": status,
        "accepted_for_future_paper_trade_plan_simulator": accepted,
        "decision_event_count": 3,
        "long_count": 1,
        "short_count": 1,
        "neutral_count": 1,
        "non_neutral_count": 2,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _inputs(tmp_path, acceptance=None, decision_audit=None):
    acceptance_path = _write_json(
        tmp_path / "decision_acceptance.json",
        acceptance or _acceptance(),
    )
    audit_path = _write_json(
        tmp_path / "decision_audit.json",
        decision_audit or _decision_audit(),
    )
    return acceptance_path, audit_path


def test_safety_notice_preserves_ce_pe_and_no_real_execution_boundary():
    notice = safety_notice().lower()

    assert "long creates a ce" in notice
    assert "short creates a pe" in notice
    assert "neutral creates no trade" in notice
    assert "does not simulate fills" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_decision_acceptance_fails(tmp_path):
    _, audit = _inputs(tmp_path)

    report = build_paper_option_trade_plan_report(
        decision_acceptance_path=tmp_path / "missing.json",
        decision_audit_path=audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_acceptance_missing" for issue in report.issues)


def test_missing_decision_audit_fails(tmp_path):
    acceptance, _ = _inputs(tmp_path)

    report = build_paper_option_trade_plan_report(
        decision_acceptance_path=acceptance,
        decision_audit_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_audit_missing" for issue in report.issues)


def test_valid_decisions_create_ce_and_pe_paper_plans(tmp_path):
    acceptance, audit = _inputs(tmp_path)

    report = build_paper_option_trade_plan_report(
        decision_acceptance_path=acceptance,
        decision_audit_path=audit,
        output_dir=tmp_path / "out",
        min_plans=2,
    )

    assert report.status == "pass"
    assert report.ready_for_future_paper_fill_simulator is True
    assert report.paper_trade_plan_count == 2
    assert report.long_plan_count == 1
    assert report.short_plan_count == 1
    assert report.neutral_no_trade_count == 1
    assert report.paper_trade_plans[0].decision == "LONG"
    assert report.paper_trade_plans[0].option_type == "CE"
    assert report.paper_trade_plans[0].option_action == "BUY"
    assert report.paper_trade_plans[1].decision == "SHORT"
    assert report.paper_trade_plans[1].option_type == "PE"


def test_warning_acceptance_fails_by_default(tmp_path):
    acceptance, audit = _inputs(tmp_path, acceptance=_acceptance(status="warn", accepted=True))

    report = build_paper_option_trade_plan_report(
        decision_acceptance_path=acceptance,
        decision_audit_path=audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_acceptance_warn" for issue in report.issues)


def test_warning_acceptance_can_remain_warning_when_allowed(tmp_path):
    acceptance, audit = _inputs(tmp_path, acceptance=_acceptance(status="warn", accepted=True))

    report = build_paper_option_trade_plan_report(
        decision_acceptance_path=acceptance,
        decision_audit_path=audit,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_paper_fill_simulator is True


def test_not_accepted_decision_acceptance_fails(tmp_path):
    acceptance, audit = _inputs(tmp_path, acceptance=_acceptance(status="pass", accepted=False))

    report = build_paper_option_trade_plan_report(
        decision_acceptance_path=acceptance,
        decision_audit_path=audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_acceptance_not_accepted" for issue in report.issues)


def test_invalid_decision_event_mapping_fails(tmp_path):
    bad_event = _decision_event(1, "LONG")
    bad_event["option_buy_mapping"] = "future_PE_buy_paper_plan_only"
    acceptance, audit = _inputs(
        tmp_path,
        decision_audit=_decision_audit(events=[bad_event]),
    )

    report = build_paper_option_trade_plan_report(
        decision_acceptance_path=acceptance,
        decision_audit_path=audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_event_wrong_option_mapping" for issue in report.issues)


def test_neutral_only_can_fail_min_plans(tmp_path):
    acceptance, audit = _inputs(
        tmp_path,
        decision_audit=_decision_audit(events=[_decision_event(1, "NEUTRAL")]),
    )

    report = build_paper_option_trade_plan_report(
        decision_acceptance_path=acceptance,
        decision_audit_path=audit,
        output_dir=tmp_path / "out",
        min_plans=1,
    )

    assert report.status == "fail"
    assert report.neutral_no_trade_count == 1
    assert any(issue.code == "insufficient_paper_option_trade_plans" for issue in report.issues)


def test_forbidden_decision_event_fields_fail(tmp_path):
    bad_event = _decision_event(1, "SHORT")
    bad_event["order_id"] = "not-allowed"
    acceptance, audit = _inputs(
        tmp_path,
        decision_audit=_decision_audit(events=[bad_event]),
    )

    report = build_paper_option_trade_plan_report(
        decision_acceptance_path=acceptance,
        decision_audit_path=audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_event_forbidden_fields" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_trade_plan_simulator(tmp_path):
    acceptance, audit = _inputs(tmp_path)

    report, outputs = build_and_write_paper_option_trade_plan_report(
        decision_acceptance_path=acceptance,
        decision_audit_path=audit,
        output_dir=tmp_path / "out",
        min_plans=2,
    )

    text_report = outputs["paper_option_trade_plan_simulator_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_OPTION_TRADE_PLAN_SIMULATOR.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_option_trade_plan_simulator_json"].exists()
    assert outputs["paper_option_trade_plans_jsonl"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_paper_fill_simulator"] is True
    assert "hqe_recorded_data_paper_option_trade_plan_simulator.bat" in combined_docs
    assert "LONG = CE BUY paper plan" in combined_docs
    assert "SHORT = PE BUY paper plan" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
