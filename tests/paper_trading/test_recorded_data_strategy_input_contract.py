import json
from pathlib import Path

from src.paper_trading.recorded_data_strategy_input_contract import (
    build_and_write_strategy_input_contract_report,
    build_strategy_input_contract_report,
    safety_notice,
    write_strategy_input_contract_report,
)


def _event(timestamp="2026-01-01T09:15:00+05:30", close=105):
    return {
        "event_index": 1,
        "event_type": "recorded_market_data_bar",
        "source_path": "sample.csv",
        "source_type": "csv",
        "row_number": 1,
        "timestamp": timestamp,
        "open": 100,
        "high": 110,
        "low": 95,
        "close": close,
        "volume": 1000,
        "safety_mode": "paper_simulation_only",
    }


def _write_events(tmp_path, events):
    path = tmp_path / "dry_run_events.jsonl"
    path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )
    return path


def test_safety_notice_preserves_contract_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "real orders" in notice
    assert "prove profitability" in notice


def test_missing_dry_run_events_fails(tmp_path):
    report = build_strategy_input_contract_report(
        dry_run_events_path=tmp_path / "missing.jsonl",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted_bar_count == 0
    assert any(issue.code == "dry_run_events_missing" for issue in report.issues)


def test_invalid_jsonl_line_fails(tmp_path):
    path = tmp_path / "dry_run_events.jsonl"
    path.write_text("{bad-json\n", encoding="utf-8")

    report = build_strategy_input_contract_report(
        dry_run_events_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dry_run_events_invalid_jsonl" for issue in report.issues)


def test_invalid_event_shape_fails(tmp_path):
    path = tmp_path / "dry_run_events.jsonl"
    path.write_text(json.dumps(["not", "object"]) + "\n", encoding="utf-8")

    report = build_strategy_input_contract_report(
        dry_run_events_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dry_run_events_invalid_shape" for issue in report.issues)


def test_valid_dry_run_event_produces_strategy_input_bar(tmp_path):
    path = _write_events(tmp_path, [_event()])

    report = build_strategy_input_contract_report(
        dry_run_events_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.input_event_count == 1
    assert report.accepted_bar_count == 1
    assert report.bars[0].timestamp == "2026-01-01T09:15:00+05:30"
    assert report.bars[0].close == 105.0
    assert report.bars[0].execution_mode == "paper_simulation_only"


def test_max_events_limits_contract_generation(tmp_path):
    path = _write_events(
        tmp_path,
        [
            _event("2026-01-01T09:15:00+05:30", 105),
            _event("2026-01-01T09:16:00+05:30", 108),
        ],
    )

    report = build_strategy_input_contract_report(
        dry_run_events_path=path,
        output_dir=tmp_path / "out",
        max_events=1,
    )

    assert report.input_event_count == 1
    assert report.accepted_bar_count == 1
    assert report.last_timestamp == "2026-01-01T09:15:00+05:30"


def test_min_bars_rule_can_fail_contract(tmp_path):
    path = _write_events(tmp_path, [_event()])

    report = build_strategy_input_contract_report(
        dry_run_events_path=path,
        output_dir=tmp_path / "out",
        min_bars=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_contract_bars" for issue in report.issues)


def test_missing_timestamp_or_close_event_is_skipped_with_warning(tmp_path):
    path = _write_events(
        tmp_path,
        [
            _event(),
            _event(timestamp="", close=None),
        ],
    )

    report = build_strategy_input_contract_report(
        dry_run_events_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "warn"
    assert report.input_event_count == 2
    assert report.accepted_bar_count == 1
    assert any(issue.code == "unplayable_contract_event" for issue in report.issues)


def test_forbidden_execution_fields_fail_contract(tmp_path):
    event = _event()
    event["order_id"] = "not-allowed"
    event["pnl"] = 99
    path = _write_events(tmp_path, [event])

    report = build_strategy_input_contract_report(
        dry_run_events_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "forbidden_execution_fields" for issue in report.issues)


def test_write_strategy_input_contract_report_creates_outputs(tmp_path):
    path = _write_events(tmp_path, [_event()])
    report = build_strategy_input_contract_report(
        dry_run_events_path=path,
        output_dir=tmp_path / "out",
    )

    outputs = write_strategy_input_contract_report(report, tmp_path / "out")

    assert outputs["strategy_input_contract_json"].exists()
    assert outputs["strategy_input_bars_jsonl"].exists()
    assert outputs["strategy_input_contract_txt"].exists()
    assert outputs["manifest_json"].exists()


def test_build_and_write_strategy_input_contract_manifest(tmp_path):
    path = _write_events(tmp_path, [_event()])

    report, outputs = build_and_write_strategy_input_contract_report(
        dry_run_events_path=path,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["strategy_input_contract_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert "not a profitability claim" in text_report
    assert manifest["accepted_bar_count"] == 1


def test_documentation_mentions_strategy_input_contract_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_STRATEGY_INPUT_CONTRACT.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_strategy_input_contract.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
