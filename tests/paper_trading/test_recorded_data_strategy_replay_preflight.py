import json
from pathlib import Path

from src.paper_trading.recorded_data_strategy_replay_preflight import (
    build_and_write_strategy_replay_preflight_report,
    build_strategy_replay_preflight_report,
    safety_notice,
    write_strategy_replay_preflight_report,
)


def _write_csv(root: Path, rows: list[str] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    source = root / "sample.csv"
    body = rows or [
        "2026-01-01T09:15:00+05:30,100,110,95,105,1000",
        "2026-01-01T09:16:00+05:30,105,112,101,108,1200",
    ]
    source.write_text(
        "timestamp,open,high,low,close,volume\n" + "\n".join(body) + "\n",
        encoding="utf-8",
    )
    return source


def test_safety_notice_preserves_preflight_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not run strategies" in notice
    assert "create signals" in notice
    assert "real orders" in notice
    assert "prove profitability" in notice


def test_strategy_replay_preflight_passes_valid_recorded_data(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report = build_strategy_replay_preflight_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
        min_events=1,
        min_bars=1,
    )

    assert report.status == "pass"
    assert report.ready_for_future_paper_strategy_replay is True
    assert [stage.stage for stage in report.stage_results] == [
        "recorded_data_replay_readiness",
        "recorded_data_strategy_input_contract",
    ]


def test_preflight_fails_when_min_events_not_met(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report = build_strategy_replay_preflight_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
        min_events=3,
        min_bars=1,
    )

    assert report.status == "fail"
    assert report.ready_for_future_paper_strategy_replay is False
    assert report.stage_results[0].accepted is False


def test_preflight_fails_when_min_bars_not_met(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report = build_strategy_replay_preflight_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
        min_events=1,
        min_bars=3,
    )

    assert report.status == "fail"
    assert report.ready_for_future_paper_strategy_replay is False
    assert report.stage_results[1].accepted is False


def test_preflight_fails_invalid_recorded_data(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(
        recorded_root,
        rows=["2026-01-01T09:15:00+05:30,100,90,95,105,1000"],
    )

    report = build_strategy_replay_preflight_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
        min_events=1,
        min_bars=1,
    )

    assert report.status == "fail"
    assert report.stage_results[0].status == "fail"


def test_preflight_can_allow_warning_readiness(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(
        recorded_root,
        rows=[
            "2026-01-01T09:16:00+05:30,105,112,101,108,1200",
            "2026-01-01T09:15:00+05:30,100,110,95,105,1000",
        ],
    )

    report = build_strategy_replay_preflight_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
        min_events=1,
        min_bars=1,
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_paper_strategy_replay is True
    assert report.stage_results[0].accepted is True


def test_preflight_blocks_warning_readiness_by_default(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(
        recorded_root,
        rows=[
            "2026-01-01T09:16:00+05:30,105,112,101,108,1200",
            "2026-01-01T09:15:00+05:30,100,110,95,105,1000",
        ],
    )

    report = build_strategy_replay_preflight_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
        min_events=1,
        min_bars=1,
        allow_warnings=False,
    )

    assert report.status == "fail"
    assert report.ready_for_future_paper_strategy_replay is False


def test_preflight_max_events_flows_into_contract(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report = build_strategy_replay_preflight_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
        min_events=1,
        min_bars=1,
        max_events=1,
    )

    assert report.status == "pass"
    assert report.stage_results[1].summary["accepted_bar_count"] == 1


def test_write_preflight_report_creates_outputs(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)
    report = build_strategy_replay_preflight_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
    )

    outputs = write_strategy_replay_preflight_report(report, tmp_path / "preflight")

    assert outputs["preflight_report_json"].exists()
    assert outputs["preflight_report_txt"].exists()
    assert outputs["manifest_json"].exists()


def test_build_and_write_preflight_report_contains_safety_and_no_profit_claim(tmp_path):
    recorded_root = tmp_path / "recorded"
    _write_csv(recorded_root)

    report, outputs = build_and_write_strategy_replay_preflight_report(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[recorded_root],
        base_output_dir=tmp_path / "reports",
        evidence_output_dir=tmp_path / "evidence",
        acceptance_output_dir=tmp_path / "acceptance",
        readiness_output_dir=tmp_path / "readiness",
        contract_output_dir=tmp_path / "contract",
        preflight_output_dir=tmp_path / "preflight",
    )

    text_report = outputs["preflight_report_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.ready_for_future_paper_strategy_replay is True
    assert "does not run strategies" in text_report
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_paper_strategy_replay"] is True


def test_documentation_mentions_strategy_replay_preflight_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_STRATEGY_REPLAY_PREFLIGHT.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_strategy_replay_preflight.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
