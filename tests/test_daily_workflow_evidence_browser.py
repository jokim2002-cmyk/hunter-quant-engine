from __future__ import annotations

import json
from pathlib import Path

from scripts.build_daily_workflow_evidence_browser import (
    SAFETY_LOCK,
    build_evidence_browser,
    collect_evidence_files,
)


def test_module143_builds_local_evidence_browser(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    day_dir = runs_root / "HQE_FORWARD_PAPER_DAILY_WORKFLOW_20260709"
    validation_dir = day_dir / "MODULE_142_EVIDENCE_VALIDATION"
    handoff_dir = day_dir / "MODULE_141_OPERATOR_HANDOFF"
    validation_dir.mkdir(parents=True)
    handoff_dir.mkdir(parents=True)

    (day_dir / "FORWARD_PAPER_DAILY_WORKFLOW_SUMMARY.json").write_text(
        json.dumps({"workflow_status": "PASS_PAPER_ONLY", "safety_lock": SAFETY_LOCK}),
        encoding="utf-8",
    )
    (handoff_dir / "MODULE_141_OPERATOR_HANDOFF.json").write_text(
        json.dumps({"module": "Module 141", "safety_lock": SAFETY_LOCK}),
        encoding="utf-8",
    )
    (validation_dir / "MODULE_142_EVIDENCE_VALIDATION_REPORT.json").write_text(
        json.dumps({"module": "Module 142", "validation_status": "PASS", "safety_lock": SAFETY_LOCK}),
        encoding="utf-8",
    )
    (day_dir / "DAY_001_FORWARD_TRADE_LOG.csv").write_text("trade_id,status\n", encoding="utf-8")
    (day_dir / "DASHBOARD_INDEX.html").write_text("<html>paper dashboard</html>", encoding="utf-8")

    out_dir = tmp_path / "browser"
    report = build_evidence_browser(runs_root=runs_root, output_dir=out_dir)

    assert report["summary"]["browser_status"] == "PASS"
    assert report["summary"]["run_count"] == 1
    assert report["summary"]["file_count"] >= 5
    assert report["safety_lock"]["real_money"] is False
    assert report["safety_lock"]["broker_execution"] is False
    assert report["safety_lock"]["real_orders"] is False
    assert report["safety_lock"]["auto_trading"] is False
    assert report["safety_lock"]["option_selling"] is False
    assert report["safety_lock"]["profitability_claim"] is False

    html_path = out_dir / "MODULE_143_EVIDENCE_BROWSER.html"
    json_path = out_dir / "MODULE_143_EVIDENCE_BROWSER_INDEX.json"
    md_path = out_dir / "MODULE_143_EVIDENCE_BROWSER_INDEX.md"
    csv_path = out_dir / "MODULE_143_EVIDENCE_BROWSER_INVENTORY.csv"

    assert html_path.exists()
    assert json_path.exists()
    assert md_path.exists()
    assert csv_path.exists()

    html = html_path.read_text(encoding="utf-8")
    markdown = md_path.read_text(encoding="utf-8")
    assert "This is not a profitability claim" in html
    assert "paper/simulation only" in html.lower()
    assert "Browser status: `PASS`" in markdown


def test_module143_holds_when_no_evidence_found(tmp_path: Path) -> None:
    runs_root = tmp_path / "empty_runs"
    runs_root.mkdir()

    report = build_evidence_browser(runs_root=runs_root, output_dir=tmp_path / "browser")

    assert report["summary"]["browser_status"] == "HOLD_NO_EVIDENCE_FOUND"
    assert report["summary"]["file_count"] == 0
    assert Path(report["outputs"]["html"]).exists()


def test_module143_blocks_safety_risk_pattern(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    day_dir = runs_root / "HQE_FORWARD_PAPER_DAILY_WORKFLOW_20260709"
    day_dir.mkdir(parents=True)

    (day_dir / "FORWARD_PAPER_DAILY_WORKFLOW_SUMMARY.json").write_text(
        json.dumps(
            {
                "workflow_status": "PASS_PAPER_ONLY",
                "safety_lock": SAFETY_LOCK,
                "bad_code_preview": "place_order(symbol='NIFTY')",
            }
        ),
        encoding="utf-8",
    )

    report = build_evidence_browser(runs_root=runs_root, output_dir=tmp_path / "browser")

    assert report["summary"]["browser_status"] == "BLOCKED_SAFETY_RISK"
    assert report["summary"]["risk_file_count"] == 1
    risky_files = [item for run in report["runs"] for item in run["files"] if item["risk_hits"]]
    assert risky_files


def test_module143_can_index_specific_evidence_dir(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    other_dir = runs_root / "unrelated"
    evidence_dir = runs_root / "selected_day"
    other_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)

    (other_dir / "DAY_999_FORWARD_TRADE_LOG.csv").write_text("should,not,index\n", encoding="utf-8")
    (evidence_dir / "DAY_001_FORWARD_TRADE_LOG.csv").write_text("trade_id,status\n", encoding="utf-8")
    (evidence_dir / "MODULE_142_EVIDENCE_VALIDATION_REPORT.md").write_text("# pass\n", encoding="utf-8")

    files = collect_evidence_files(runs_root=runs_root, evidence_dir=evidence_dir)
    assert files
    assert all(str(evidence_dir) in str(item.path) for item in files)

    report = build_evidence_browser(
        runs_root=runs_root,
        evidence_dir=evidence_dir,
        output_dir=tmp_path / "browser",
    )
    assert report["summary"]["browser_status"] == "PASS"
    assert report["summary"]["run_count"] == 1
    assert all(run["run_dir"] == str(evidence_dir) for run in report["runs"])
