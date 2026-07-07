import json
from pathlib import Path

from src.paper_trading.recorded_data_strategy_decision_acceptance import (
    build_and_write_strategy_decision_acceptance_report,
    build_strategy_decision_acceptance_report,
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
        "decision_mode": "smc_parameter_aligned_decision_audit_only",
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


def _write_report(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_acceptance_and_trade_boundaries():
    notice = safety_notice().lower()

    assert "long maps to future ce buy" in notice
    assert "short maps to future pe buy" in notice
    assert "neutral maps to no trade" in notice
    assert "does not create trade plans" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_decision_audit_fails(tmp_path):
    report = build_strategy_decision_acceptance_report(
        decision_audit_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_audit_missing" for issue in report.issues)


def test_valid_decision_audit_is_accepted(tmp_path):
    decision_audit = _write_report(tmp_path / "decision_audit.json", _decision_audit())

    report = build_strategy_decision_acceptance_report(
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
        min_decisions=3,
        min_non_neutral_decisions=2,
    )

    assert report.status == "pass"
    assert report.accepted_for_future_paper_trade_plan_simulator is True
    assert report.decision_event_count == 3
    assert report.long_count == 1
    assert report.short_count == 1
    assert report.neutral_count == 1
    assert report.non_neutral_count == 2


def test_warning_decision_audit_fails_by_default(tmp_path):
    decision_audit = _write_report(
        tmp_path / "decision_audit.json",
        _decision_audit(status="warn", ready=True),
    )

    report = build_strategy_decision_acceptance_report(
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_audit_warn" for issue in report.issues)


def test_warning_decision_audit_can_remain_warning_when_allowed(tmp_path):
    decision_audit = _write_report(
        tmp_path / "decision_audit.json",
        _decision_audit(status="warn", ready=True),
    )

    report = build_strategy_decision_acceptance_report(
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.accepted_for_future_paper_trade_plan_simulator is True


def test_not_ready_decision_audit_fails(tmp_path):
    decision_audit = _write_report(
        tmp_path / "decision_audit.json",
        _decision_audit(status="pass", ready=False),
    )

    report = build_strategy_decision_acceptance_report(
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_audit_not_ready" for issue in report.issues)


def test_invalid_decision_fails(tmp_path):
    bad_event = _decision_event(1, "LONG")
    bad_event["decision"] = "BUY"
    decision_audit = _write_report(
        tmp_path / "decision_audit.json",
        _decision_audit(events=[bad_event]),
    )

    report = build_strategy_decision_acceptance_report(
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_event_invalid_decision" for issue in report.issues)


def test_wrong_option_buy_mapping_fails(tmp_path):
    bad_event = _decision_event(1, "LONG")
    bad_event["option_buy_mapping"] = "future_PE_buy_paper_plan_only"
    decision_audit = _write_report(
        tmp_path / "decision_audit.json",
        _decision_audit(events=[bad_event]),
    )

    report = build_strategy_decision_acceptance_report(
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "decision_event_wrong_option_mapping"
        for issue in report.issues
    )


def test_wrong_decision_modes_fail(tmp_path):
    bad_event = _decision_event(1, "SHORT")
    bad_event["broker_execution_mode"] = "enabled"
    decision_audit = _write_report(
        tmp_path / "decision_audit.json",
        _decision_audit(events=[bad_event]),
    )

    report = build_strategy_decision_acceptance_report(
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "decision_event_wrong_modes" for issue in report.issues)


def test_min_non_neutral_rule_can_fail(tmp_path):
    decision_audit = _write_report(
        tmp_path / "decision_audit.json",
        _decision_audit(events=[_decision_event(1, "NEUTRAL")]),
    )

    report = build_strategy_decision_acceptance_report(
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
        min_non_neutral_decisions=1,
    )

    assert report.status == "fail"
    assert any(
        issue.code == "insufficient_non_neutral_strategy_decisions"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_acceptance(tmp_path):
    decision_audit = _write_report(tmp_path / "decision_audit.json", _decision_audit())

    report, outputs = build_and_write_strategy_decision_acceptance_report(
        decision_audit_path=decision_audit,
        output_dir=tmp_path / "out",
        min_decisions=3,
    )

    text_report = outputs["strategy_decision_acceptance_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_DATA_STRATEGY_DECISION_ACCEPTANCE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["strategy_decision_acceptance_json"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["accepted_for_future_paper_trade_plan_simulator"] is True
    assert "hqe_recorded_data_strategy_decision_acceptance.bat" in combined_docs
    assert "LONG / SHORT / NEUTRAL" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
