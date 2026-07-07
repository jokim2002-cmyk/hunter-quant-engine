import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance import (
    build_adapter_dry_run_consumer_acceptance_report,
    build_and_write_adapter_dry_run_consumer_acceptance_report,
    safety_notice,
)


def _consumed_event(planned_bar_count=2):
    return {
        "consumption_index": 1,
        "consumption_type": "adapter_dry_run_event_consumed_no_strategy_execution",
        "source_event_index": 1,
        "request_id": "paper_strategy_adapter_request_001",
        "scenario_id": "recorded_strategy_replay_scenario_001",
        "source_path": "sample.csv",
        "source_type": "csv",
        "planned_bar_count": planned_bar_count,
        "first_timestamp": "2026-01-01T09:15:00+05:30",
        "last_timestamp": "2026-01-01T09:16:00+05:30",
        "consumer_mode": "consumer_audit_only",
        "strategy_execution_mode": "not_executed_consumer_only",
        "broker_execution_mode": "broker_disabled",
        "output_mode": "consumer_audit_manifest_only",
    }


def _consumer(status="pass", ready=True, events=None):
    consumed_events = events if events is not None else [_consumed_event()]
    return {
        "status": status,
        "ready_for_future_consumer_evidence": ready,
        "input_event_count": len(consumed_events),
        "consumed_event_count": len(consumed_events),
        "total_planned_bars": sum(
            event.get("planned_bar_count", 0) for event in consumed_events
        ),
        "consumed_events": consumed_events,
    }


def _write_consumer(tmp_path, payload):
    path = tmp_path / "paper_strategy_adapter_dry_run_consumer.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_consumer_acceptance_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not execute strategy logic" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_consumer_report_fails(tmp_path):
    report = build_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "adapter_dry_run_consumer_missing" for issue in report.issues)


def test_invalid_json_fails(tmp_path):
    path = tmp_path / "paper_strategy_adapter_dry_run_consumer.json"
    path.write_text("{bad-json", encoding="utf-8")

    report = build_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_dry_run_consumer_invalid_json" for issue in report.issues)


def test_valid_consumer_is_accepted(tmp_path):
    path = _write_consumer(tmp_path, _consumer())

    report = build_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.accepted is True
    assert report.consumed_event_count == 1
    assert report.total_planned_bars == 2


def test_not_ready_consumer_fails(tmp_path):
    path = _write_consumer(tmp_path, _consumer(status="pass", ready=False))

    report = build_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_dry_run_consumer_not_ready" for issue in report.issues)


def test_warn_consumer_fails_by_default(tmp_path):
    path = _write_consumer(tmp_path, _consumer(status="warn", ready=True))

    report = build_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "adapter_dry_run_consumer_warn" for issue in report.issues)


def test_warn_consumer_can_be_accepted_when_allowed(tmp_path):
    path = _write_consumer(tmp_path, _consumer(status="warn", ready=True))

    report = build_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.accepted is True


def test_min_consumed_events_rule_can_fail(tmp_path):
    path = _write_consumer(tmp_path, _consumer())

    report = build_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=path,
        output_dir=tmp_path / "out",
        min_consumed_events=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_consumed_events" for issue in report.issues)


def test_min_total_planned_bars_rule_can_fail(tmp_path):
    path = _write_consumer(
        tmp_path,
        _consumer(events=[_consumed_event(planned_bar_count=1)]),
    )

    report = build_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=path,
        output_dir=tmp_path / "out",
        min_total_planned_bars=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_total_planned_bars" for issue in report.issues)


def test_wrong_modes_and_forbidden_fields_fail(tmp_path):
    event = _consumed_event()
    event["consumer_mode"] = "execute"
    event["order_id"] = "not-allowed"
    path = _write_consumer(tmp_path, _consumer(events=[event]))

    report = build_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "consumed_event_wrong_modes" for issue in report.issues)
    assert any(issue.code == "consumed_event_forbidden_fields" for issue in report.issues)


def test_build_write_outputs_and_docs_reference_consumer_acceptance(tmp_path):
    path = _write_consumer(tmp_path, _consumer())

    report, outputs = build_and_write_adapter_dry_run_consumer_acceptance_report(
        consumer_report_path=path,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["paper_strategy_adapter_dry_run_consumer_acceptance_txt"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_ADAPTER_DRY_RUN_CONSUMER_ACCEPTANCE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_strategy_adapter_dry_run_consumer_acceptance_json"].exists()
    assert outputs["paper_strategy_adapter_dry_run_consumer_acceptance_txt"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["accepted"] is True
    assert "hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance.bat" in combined_docs
    assert "paper/simulation" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
