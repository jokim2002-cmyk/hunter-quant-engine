import json
from pathlib import Path

from src.paper_trading.recorded_data_strategy_decision_audit import (
    build_and_write_strategy_decision_audit_report,
    build_strategy_decision_audit_report,
    safety_notice,
)


def _sandbox_event(index, close):
    return {
        "sandbox_event_index": index,
        "event_type": "strategy_replay_bar_available",
        "source_path": "sample.csv",
        "source_type": "csv",
        "source_row_number": index,
        "timestamp": f"2026-01-01T09:{14 + index:02d}:00+05:30",
        "open": close - 1,
        "high": close + 1,
        "low": close - 2,
        "close": close,
        "volume": 1000,
        "data_mode": "recorded_replay",
        "replay_mode": "strategy_replay_sandbox",
        "strategy_execution_mode": "not_executed_sandbox_only",
        "signal_mode": "signals_not_generated",
        "trade_plan_mode": "trade_plans_not_created",
        "broker_execution_mode": "broker_disabled",
        "output_mode": "sandbox_event_manifest_only",
    }


def _sandbox_report(status="pass", ready=True, events=None):
    return {
        "status": status,
        "ready_for_future_strategy_decision_audit": ready,
        "sandbox_event_count": len(events or []),
        "sandbox_events": events or [
            _sandbox_event(1, 100.0),
            _sandbox_event(2, 102.0),
            _sandbox_event(3, 101.0),
        ],
    }


def _write_report(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_decision_and_trade_boundaries():
    notice = safety_notice().lower()

    assert "long means future ce buy" in notice
    assert "short means future pe buy" in notice
    assert "neutral means no trade" in notice
    assert "does not create trade plans" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_sandbox_report_fails(tmp_path):
    report = build_strategy_decision_audit_report(
        sandbox_report_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "sandbox_report_missing" for issue in report.issues)


def test_valid_sandbox_report_creates_long_short_neutral_decisions(tmp_path):
    sandbox = _write_report(tmp_path / "sandbox.json", _sandbox_report())

    report = build_strategy_decision_audit_report(
        sandbox_report_path=sandbox,
        output_dir=tmp_path / "out",
    )

    decisions = [event.decision for event in report.decision_events]

    assert report.status == "pass"
    assert report.ready_for_future_paper_trade_plan_simulator is True
    assert decisions == ["NEUTRAL", "LONG", "SHORT"]
    assert report.long_count == 1
    assert report.short_count == 1
    assert report.neutral_count == 1
    assert report.decision_events[1].option_buy_mapping == "future_CE_buy_paper_plan_only"
    assert report.decision_events[2].option_buy_mapping == "future_PE_buy_paper_plan_only"


def test_warning_sandbox_report_fails_by_default(tmp_path):
    sandbox = _write_report(
        tmp_path / "sandbox.json",
        _sandbox_report(status="warn", ready=True),
    )

    report = build_strategy_decision_audit_report(
        sandbox_report_path=sandbox,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "sandbox_report_warn" for issue in report.issues)


def test_warning_sandbox_report_can_remain_warning_when_allowed(tmp_path):
    sandbox = _write_report(
        tmp_path / "sandbox.json",
        _sandbox_report(status="warn", ready=True),
    )

    report = build_strategy_decision_audit_report(
        sandbox_report_path=sandbox,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_paper_trade_plan_simulator is True


def test_not_ready_sandbox_report_fails(tmp_path):
    sandbox = _write_report(
        tmp_path / "sandbox.json",
        _sandbox_report(status="pass", ready=False),
    )

    report = build_strategy_decision_audit_report(
        sandbox_report_path=sandbox,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "sandbox_report_not_ready" for issue in report.issues)


def test_wrong_sandbox_event_modes_fail(tmp_path):
    bad_event = _sandbox_event(1, 100.0)
    bad_event["broker_execution_mode"] = "enabled"
    sandbox = _write_report(tmp_path / "sandbox.json", _sandbox_report(events=[bad_event]))

    report = build_strategy_decision_audit_report(
        sandbox_report_path=sandbox,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "sandbox_event_wrong_modes" for issue in report.issues)


def test_sandbox_event_missing_required_fields_fails(tmp_path):
    bad_event = _sandbox_event(1, 100.0)
    bad_event.pop("close")
    sandbox = _write_report(tmp_path / "sandbox.json", _sandbox_report(events=[bad_event]))

    report = build_strategy_decision_audit_report(
        sandbox_report_path=sandbox,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "sandbox_event_missing_required_fields"
        for issue in report.issues
    )


def test_forbidden_sandbox_event_fields_fail(tmp_path):
    bad_event = _sandbox_event(1, 100.0)
    bad_event["order_id"] = "not-allowed"
    sandbox = _write_report(tmp_path / "sandbox.json", _sandbox_report(events=[bad_event]))

    report = build_strategy_decision_audit_report(
        sandbox_report_path=sandbox,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "sandbox_event_forbidden_fields" for issue in report.issues)


def test_min_decisions_rule_can_fail(tmp_path):
    sandbox = _write_report(
        tmp_path / "sandbox.json",
        _sandbox_report(events=[_sandbox_event(1, 100.0)]),
    )

    report = build_strategy_decision_audit_report(
        sandbox_report_path=sandbox,
        output_dir=tmp_path / "out",
        min_decisions=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_strategy_decisions" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_decision_audit(tmp_path):
    sandbox = _write_report(tmp_path / "sandbox.json", _sandbox_report())

    report, outputs = build_and_write_strategy_decision_audit_report(
        sandbox_report_path=sandbox,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["strategy_decision_audit_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_DATA_STRATEGY_DECISION_AUDIT.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["strategy_decision_audit_json"].exists()
    assert outputs["strategy_decision_audit_events_jsonl"].exists()
    assert outputs["strategy_decision_audit_events_csv"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_paper_trade_plan_simulator"] is True
    assert "hqe_recorded_data_strategy_decision_audit.bat" in combined_docs
    assert "LONG / SHORT / NEUTRAL" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
