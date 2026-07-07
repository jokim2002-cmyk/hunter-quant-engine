import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run_consumer_readiness import (
    build_adapter_dry_run_consumer_readiness_report,
    build_and_write_adapter_dry_run_consumer_readiness_report,
    safety_notice,
)


def _readiness(status="pass", ready=True):
    return {
        "status": status,
        "ready_for_future_paper_strategy_adapter_evidence_release": ready,
    }


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


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_jsonl(path, rows):
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _inputs(tmp_path, readiness=None, events=None):
    readiness_path = _write_json(
        tmp_path / "adapter_evidence_readiness.json",
        readiness or _readiness(),
    )
    events_path = _write_jsonl(
        tmp_path / "adapter_dry_run_events.jsonl",
        events or [_event()],
    )
    return readiness_path, events_path


def _build(tmp_path, **kwargs):
    readiness_path, events_path = _inputs(
        tmp_path,
        readiness=kwargs.pop("readiness", None),
        events=kwargs.pop("events", None),
    )
    return build_adapter_dry_run_consumer_readiness_report(
        adapter_evidence_readiness_path=readiness_path,
        adapter_dry_run_events_path=events_path,
        consumer_output_dir=tmp_path / "consumer",
        consumer_acceptance_output_dir=tmp_path / "consumer_acceptance",
        readiness_output_dir=tmp_path / "consumer_readiness",
        **kwargs,
    )


def test_safety_notice_preserves_consumer_readiness_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not execute strategy logic" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_consumer_readiness_passes_valid_inputs(tmp_path):
    report = _build(tmp_path)

    assert report.status == "pass"
    assert report.ready_for_future_consumer_evidence_release is True
    assert [stage.stage for stage in report.stage_results] == [
        "recorded_data_paper_strategy_adapter_dry_run_consumer",
        "recorded_data_paper_strategy_adapter_dry_run_consumer_acceptance",
    ]


def test_consumer_readiness_fails_when_min_events_not_met(tmp_path):
    report = _build(tmp_path, min_events=2)

    assert report.status == "fail"
    assert report.ready_for_future_consumer_evidence_release is False
    assert report.stage_results[0].accepted is False


def test_consumer_readiness_fails_when_min_total_bars_not_met(tmp_path):
    report = _build(tmp_path, events=[_event(planned_bar_count=1)], min_total_planned_bars=2)

    assert report.status == "fail"
    assert report.stage_results[1].accepted is False


def test_consumer_readiness_blocks_warning_by_default(tmp_path):
    report = _build(
        tmp_path,
        readiness=_readiness(status="warn", ready=True),
    )

    assert report.status == "fail"
    assert report.ready_for_future_consumer_evidence_release is False


def test_consumer_readiness_allows_warning_when_requested(tmp_path):
    report = _build(
        tmp_path,
        readiness=_readiness(status="warn", ready=True),
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_consumer_evidence_release is True
    assert report.stage_results[1].accepted is True


def test_consumer_readiness_fails_invalid_readiness(tmp_path):
    report = _build(
        tmp_path,
        readiness=_readiness(status="fail", ready=False),
    )

    assert report.status == "fail"
    assert report.stage_results[0].status == "fail"


def test_consumer_readiness_fails_wrong_event_modes(tmp_path):
    event = _event()
    event["adapter_dry_run_mode"] = "execute"

    report = _build(tmp_path, events=[event])

    assert report.status == "fail"
    assert report.stage_results[0].accepted is False


def test_consumer_readiness_fails_forbidden_event_fields(tmp_path):
    event = _event()
    event["order_id"] = "not-allowed"

    report = _build(tmp_path, events=[event])

    assert report.status == "fail"
    assert report.stage_results[0].accepted is False


def test_build_and_write_consumer_readiness_outputs_safety_and_no_profit_claim(tmp_path):
    readiness_path, events_path = _inputs(tmp_path)

    report, outputs = build_and_write_adapter_dry_run_consumer_readiness_report(
        adapter_evidence_readiness_path=readiness_path,
        adapter_dry_run_events_path=events_path,
        consumer_output_dir=tmp_path / "consumer",
        consumer_acceptance_output_dir=tmp_path / "consumer_acceptance",
        readiness_output_dir=tmp_path / "consumer_readiness",
    )

    text_report = outputs["paper_strategy_adapter_dry_run_consumer_readiness_txt"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert outputs["paper_strategy_adapter_dry_run_consumer_readiness_json"].exists()
    assert outputs["paper_strategy_adapter_dry_run_consumer_readiness_txt"].exists()
    assert outputs["manifest_json"].exists()
    assert report.status == "pass"
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_consumer_evidence_release"] is True


def test_documentation_mentions_consumer_readiness_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_ADAPTER_DRY_RUN_CONSUMER_READINESS.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_adapter_dry_run_consumer_readiness.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
