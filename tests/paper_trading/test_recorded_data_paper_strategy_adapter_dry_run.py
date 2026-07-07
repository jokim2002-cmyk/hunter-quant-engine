import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_adapter_dry_run import (
    build_adapter_dry_run_report,
    build_and_write_adapter_dry_run_report,
    safety_notice,
)


def _readiness(status="pass", ready=True):
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
    readiness_path = _write_json(tmp_path / "adapter_readiness.json", readiness or _readiness())
    requests_path = _write_jsonl(tmp_path / "adapter_requests.jsonl", requests or [_request()])
    return readiness_path, requests_path


def test_safety_notice_preserves_adapter_dry_run_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not execute strategy logic" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_adapter_readiness_fails(tmp_path):
    _, requests = _inputs(tmp_path)

    report = build_adapter_dry_run_report(
        adapter_readiness_path=tmp_path / "missing.json",
        adapter_requests_path=requests,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_readiness_missing" for issue in report.issues)


def test_missing_adapter_requests_fails(tmp_path):
    readiness, _ = _inputs(tmp_path)

    report = build_adapter_dry_run_report(
        adapter_readiness_path=readiness,
        adapter_requests_path=tmp_path / "missing.jsonl",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_requests_missing" for issue in report.issues)


def test_valid_inputs_create_dry_run_event(tmp_path):
    readiness, requests = _inputs(tmp_path)

    report = build_adapter_dry_run_report(
        adapter_readiness_path=readiness,
        adapter_requests_path=requests,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_future_adapter_evidence is True
    assert report.request_count == 1
    assert report.dry_run_event_count == 1
    assert report.total_planned_bars == 2
    assert report.dry_run_events[0].adapter_dry_run_mode == "dry_run_no_strategy_execution"


def test_warning_readiness_fails_by_default(tmp_path):
    readiness, requests = _inputs(tmp_path, readiness=_readiness(status="warn", ready=True))

    report = build_adapter_dry_run_report(
        adapter_readiness_path=readiness,
        adapter_requests_path=requests,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_readiness_warn" for issue in report.issues)


def test_warning_readiness_can_remain_warning_when_allowed(tmp_path):
    readiness, requests = _inputs(tmp_path, readiness=_readiness(status="warn", ready=True))

    report = build_adapter_dry_run_report(
        adapter_readiness_path=readiness,
        adapter_requests_path=requests,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_adapter_evidence is True


def test_min_requests_rule_can_fail(tmp_path):
    readiness, requests = _inputs(tmp_path)

    report = build_adapter_dry_run_report(
        adapter_readiness_path=readiness,
        adapter_requests_path=requests,
        output_dir=tmp_path / "out",
        min_requests=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_dry_run_events" for issue in report.issues)


def test_min_total_planned_bars_rule_can_fail(tmp_path):
    readiness, requests = _inputs(tmp_path, requests=[_request(planned_bar_count=1)])

    report = build_adapter_dry_run_report(
        adapter_readiness_path=readiness,
        adapter_requests_path=requests,
        output_dir=tmp_path / "out",
        min_total_planned_bars=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_total_planned_bars" for issue in report.issues)


def test_wrong_modes_and_forbidden_fields_fail(tmp_path):
    request = _request()
    request["adapter_mode"] = "execute"
    request["order_id"] = "not-allowed"
    readiness, requests = _inputs(tmp_path, requests=[request])

    report = build_adapter_dry_run_report(
        adapter_readiness_path=readiness,
        adapter_requests_path=requests,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.dry_run_event_count == 0
    assert any(issue.code == "adapter_request_wrong_modes" for issue in report.issues)
    assert any(issue.code == "adapter_request_forbidden_fields" for issue in report.issues)


def test_build_and_write_dry_run_outputs_safety_and_no_profit_claim(tmp_path):
    readiness, requests = _inputs(tmp_path)

    report, outputs = build_and_write_adapter_dry_run_report(
        adapter_readiness_path=readiness,
        adapter_requests_path=requests,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["paper_strategy_adapter_dry_run_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["paper_strategy_adapter_dry_run_json"].exists()
    assert outputs["paper_strategy_adapter_dry_run_events_jsonl"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_adapter_evidence"] is True


def test_documentation_mentions_adapter_dry_run_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_ADAPTER_DRY_RUN.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_adapter_dry_run.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
