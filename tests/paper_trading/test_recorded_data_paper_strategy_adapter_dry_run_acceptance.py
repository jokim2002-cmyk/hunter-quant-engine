import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run_acceptance import (
    build_adapter_dry_run_acceptance_report,
    build_and_write_adapter_dry_run_acceptance_report,
    safety_notice,
)


def _event(planned_bar_count=2):
    return {
        "event_index": 1,
        "event_type": "adapter_dry_run_request_received",
        "request_id": "paper_strategy_adapter_request_001",
        "scenario_id": "recorded_strategy_replay_scenario_001",
        "source_path": "sample.csv",
        "source_type": "csv",
        "planned_bar_count": planned_bar_count,
        "first_timestamp": "2026-01-01T09:15:00+05:30",
        "last_timestamp": "2026-01-01T09:16:00+05:30",
        "adapter_dry_run_mode": "dry_run_no_strategy_execution",
        "strategy_execution_mode": "not_executed_dry_run_only",
        "broker_execution_mode": "broker_disabled",
        "output_mode": "dry_run_event_manifest_only",
    }


def _dry_run(status="pass", ready=True, events=None):
    dry_run_events = events if events is not None else [_event()]
    return {
        "status": status,
        "ready_for_future_adapter_evidence": ready,
        "request_count": len(dry_run_events),
        "dry_run_event_count": len(dry_run_events),
        "total_planned_bars": sum(event.get("planned_bar_count", 0) for event in dry_run_events),
        "dry_run_events": dry_run_events,
    }


def _write_dry_run(tmp_path, payload):
    path = tmp_path / "paper_strategy_adapter_dry_run.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_adapter_dry_run_acceptance_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not execute strategy logic" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_adapter_dry_run_fails(tmp_path):
    report = build_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "adapter_dry_run_missing" for issue in report.issues)


def test_invalid_json_fails(tmp_path):
    path = tmp_path / "paper_strategy_adapter_dry_run.json"
    path.write_text("{bad-json", encoding="utf-8")

    report = build_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_dry_run_invalid_json" for issue in report.issues)


def test_valid_dry_run_is_accepted(tmp_path):
    path = _write_dry_run(tmp_path, _dry_run())

    report = build_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.accepted is True
    assert report.event_count == 1
    assert report.total_planned_bars == 2


def test_not_ready_dry_run_fails(tmp_path):
    path = _write_dry_run(tmp_path, _dry_run(status="pass", ready=False))

    report = build_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_dry_run_not_ready" for issue in report.issues)


def test_warn_dry_run_fails_by_default(tmp_path):
    path = _write_dry_run(tmp_path, _dry_run(status="warn", ready=True))

    report = build_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "adapter_dry_run_warn" for issue in report.issues)


def test_warn_dry_run_can_be_accepted_when_allowed(tmp_path):
    path = _write_dry_run(tmp_path, _dry_run(status="warn", ready=True))

    report = build_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.accepted is True


def test_min_events_rule_can_fail(tmp_path):
    path = _write_dry_run(tmp_path, _dry_run())

    report = build_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=path,
        output_dir=tmp_path / "out",
        min_events=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_dry_run_events" for issue in report.issues)


def test_min_total_bars_rule_can_fail(tmp_path):
    path = _write_dry_run(tmp_path, _dry_run(events=[_event(planned_bar_count=1)]))

    report = build_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=path,
        output_dir=tmp_path / "out",
        min_total_planned_bars=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_total_planned_bars" for issue in report.issues)


def test_wrong_modes_and_forbidden_fields_fail(tmp_path):
    event = _event()
    event["adapter_dry_run_mode"] = "execute"
    event["order_id"] = "not-allowed"
    path = _write_dry_run(tmp_path, _dry_run(events=[event]))

    report = build_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_dry_run_event_wrong_modes" for issue in report.issues)
    assert any(issue.code == "adapter_dry_run_event_forbidden_fields" for issue in report.issues)


def test_build_and_write_acceptance_outputs_safety_and_no_profit_claim(tmp_path):
    path = _write_dry_run(tmp_path, _dry_run())

    report, outputs = build_and_write_adapter_dry_run_acceptance_report(
        adapter_dry_run_path=path,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["paper_strategy_adapter_dry_run_acceptance_txt"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["paper_strategy_adapter_dry_run_acceptance_json"].exists()
    assert outputs["paper_strategy_adapter_dry_run_acceptance_txt"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["accepted"] is True


def test_documentation_mentions_adapter_dry_run_acceptance_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_ADAPTER_DRY_RUN_ACCEPTANCE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_adapter_dry_run_acceptance.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
