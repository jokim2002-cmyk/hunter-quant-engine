import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run_readiness import (
    build_adapter_dry_run_readiness_report,
    build_and_write_adapter_dry_run_readiness_report,
    safety_notice,
)


def _adapter_readiness(status="pass", ready=True):
    return {
        "status": status,
        "ready_for_future_adapter_dry_run": ready,
    }


def _request(planned_bar_count=2):
    return {
        "request_id": "paper_strategy_adapter_request_001",
        "scenario_id": "recorded_strategy_replay_scenario_001",
        "source_path": "sample.csv",
        "source_type": "csv",
        "planned_bar_count": planned_bar_count,
        "first_timestamp": "2026-01-01T09:15:00+05:30",
        "last_timestamp": "2026-01-01T09:16:00+05:30",
        "adapter_mode": "contract_only_no_strategy_execution",
        "strategy_execution_mode": "not_executed_contract_only",
        "broker_execution_mode": "broker_disabled",
        "output_mode": "adapter_request_manifest_only",
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


def _inputs(tmp_path, readiness=None, requests=None):
    readiness_path = _write_json(
        tmp_path / "adapter_readiness.json",
        readiness or _adapter_readiness(),
    )
    requests_path = _write_jsonl(
        tmp_path / "adapter_requests.jsonl",
        requests or [_request()],
    )
    return readiness_path, requests_path


def _build(tmp_path, **kwargs):
    readiness, requests = _inputs(
        tmp_path,
        readiness=kwargs.pop("readiness", None),
        requests=kwargs.pop("requests", None),
    )
    return build_adapter_dry_run_readiness_report(
        adapter_readiness_path=readiness,
        adapter_requests_path=requests,
        dry_run_output_dir=tmp_path / "dry_run",
        dry_run_acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        **kwargs,
    )


def test_safety_notice_preserves_adapter_dry_run_readiness_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not execute strategy logic" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_adapter_dry_run_readiness_passes_valid_inputs(tmp_path):
    report = _build(tmp_path)

    assert report.status == "pass"
    assert report.ready_for_future_adapter_evidence is True
    assert [stage.stage for stage in report.stage_results] == [
        "recorded_data_paper_strategy_adapter_dry_run",
        "recorded_data_paper_strategy_adapter_dry_run_acceptance",
    ]


def test_adapter_dry_run_readiness_fails_when_min_events_not_met(tmp_path):
    report = _build(tmp_path, min_events=2)

    assert report.status == "fail"
    assert report.ready_for_future_adapter_evidence is False
    assert report.stage_results[0].accepted is False


def test_adapter_dry_run_readiness_fails_when_min_total_bars_not_met(tmp_path):
    report = _build(tmp_path, min_total_planned_bars=3)

    assert report.status == "fail"
    assert report.stage_results[1].accepted is False
    assert report.stage_results[1].summary["total_planned_bars"] == 2


def test_adapter_dry_run_readiness_blocks_warning_by_default(tmp_path):
    report = _build(
        tmp_path,
        readiness=_adapter_readiness(status="warn", ready=True),
    )

    assert report.status == "fail"
    assert report.ready_for_future_adapter_evidence is False


def test_adapter_dry_run_readiness_allows_warning_when_requested(tmp_path):
    report = _build(
        tmp_path,
        readiness=_adapter_readiness(status="warn", ready=True),
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_adapter_evidence is True
    assert report.stage_results[1].accepted is True


def test_adapter_dry_run_readiness_fails_invalid_adapter_readiness(tmp_path):
    report = _build(
        tmp_path,
        readiness=_adapter_readiness(status="fail", ready=False),
    )

    assert report.status == "fail"
    assert report.stage_results[0].status == "fail"


def test_adapter_dry_run_readiness_fails_wrong_request_modes(tmp_path):
    request = _request()
    request["adapter_mode"] = "execute"

    report = _build(tmp_path, requests=[request])

    assert report.status == "fail"
    assert report.stage_results[0].summary["dry_run_event_count"] == 0


def test_adapter_dry_run_readiness_fails_forbidden_request_fields(tmp_path):
    request = _request()
    request["order_id"] = "not-allowed"

    report = _build(tmp_path, requests=[request])

    assert report.status == "fail"
    assert report.stage_results[0].accepted is False


def test_build_and_write_adapter_dry_run_readiness_outputs_safety_and_no_profit_claim(tmp_path):
    readiness, requests = _inputs(tmp_path)

    report, outputs = build_and_write_adapter_dry_run_readiness_report(
        adapter_readiness_path=readiness,
        adapter_requests_path=requests,
        dry_run_output_dir=tmp_path / "dry_run",
        dry_run_acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
    )

    text_report = outputs["paper_strategy_adapter_dry_run_readiness_txt"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert outputs["paper_strategy_adapter_dry_run_readiness_json"].exists()
    assert outputs["paper_strategy_adapter_dry_run_readiness_txt"].exists()
    assert outputs["manifest_json"].exists()
    assert report.status == "pass"
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_adapter_evidence"] is True


def test_documentation_mentions_adapter_dry_run_readiness_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_ADAPTER_DRY_RUN_READINESS.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_adapter_dry_run_readiness.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
