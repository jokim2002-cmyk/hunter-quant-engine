from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_daily_workflow_evidence_handoff import (
    SAFETY_LOCK,
    decide_validation_status,
    validate_daily_workflow_evidence,
)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _module140_summary(day_dir: Path, status: str = "PASS_PAPER_ONLY") -> Path:
    source_file = day_dir / "FORWARD_PAPER_DAILY_WORKFLOW_SUMMARY.json"
    _write_json(
        source_file,
        {
            "module": "Module 140 - Forward Paper Daily Workflow Wrapper",
            "workflow_status": status,
            "trading_date": "2026-07-09",
            "completed_trades": 0,
            "safety_lock": SAFETY_LOCK,
        },
    )
    return source_file


def _module141_handoff(day_dir: Path, source_file: Path, safety_lock: dict | None = None) -> Path:
    handoff_dir = day_dir / "MODULE_141_OPERATOR_HANDOFF"
    handoff_json = handoff_dir / "MODULE_141_OPERATOR_HANDOFF.json"
    handoff_md = handoff_dir / "MODULE_141_OPERATOR_HANDOFF.md"
    handoff_csv = handoff_dir / "MODULE_141_FILE_INSPECTION_TARGETS.csv"

    _write_json(
        handoff_json,
        {
            "module": "Module 141 - Daily Workflow Operator Checklist / Handoff Pack",
            "generated_at": "2026-07-09T09:15:00",
            "safety_lock": safety_lock or SAFETY_LOCK,
            "source": {
                "source_status": "found_explicit_file",
                "source_file": str(source_file),
                "source_dir": str(source_file.parent),
                "source_kind": "json",
                "extracted_status_fields": {"workflow_status": "PASS_PAPER_ONLY"},
            },
            "operator_checklist": {"before_market": ["paper-only"]},
        },
    )
    handoff_md.write_text("# Module 141\n\nThis is not a profitability claim.\n", encoding="utf-8")
    handoff_csv.write_text("relative_path,file_name,size_bytes,modified_time,inspection_note\n", encoding="utf-8")
    return handoff_json


def test_module142_passes_complete_paper_only_evidence(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    day_dir = runs_root / "HQE_FORWARD_PAPER_DAILY_WORKFLOW_20260709"
    day_dir.mkdir(parents=True)

    module140_source = _module140_summary(day_dir)
    handoff_json = _module141_handoff(day_dir, module140_source)

    (day_dir / "DAY_001_FORWARD_TRADE_LOG.csv").write_text("trade_id,status\n", encoding="utf-8")
    (day_dir / "FORWARD_VALIDATION_MASTER_LEDGER.csv").write_text("day,status\n1,PAPER_ONLY\n", encoding="utf-8")
    (day_dir / "DASHBOARD_INDEX.html").write_text("<html>paper dashboard</html>", encoding="utf-8")

    out_dir = tmp_path / "validation"
    report = validate_daily_workflow_evidence(
        runs_root=runs_root,
        output_dir=out_dir,
        handoff_file=handoff_json,
        daily_output_file=module140_source,
    )

    assert report["validation_status"] == "PASS"
    assert Path(report["outputs"]["markdown"]).exists()
    assert Path(report["outputs"]["json"]).exists()
    assert Path(report["outputs"]["checks_csv"]).exists()
    assert Path(report["outputs"]["inventory_csv"]).exists()

    markdown = Path(report["outputs"]["markdown"]).read_text(encoding="utf-8")
    assert "This is not a profitability claim" in markdown
    assert "Validation status: `PASS`" in markdown


def test_module142_holds_when_module140_source_missing(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    day_dir = runs_root / "HQE_FORWARD_PAPER_DAILY_WORKFLOW_20260709"
    day_dir.mkdir(parents=True)

    missing_source = day_dir / "FORWARD_PAPER_DAILY_WORKFLOW_SUMMARY.json"
    handoff_json = _module141_handoff(day_dir, missing_source)

    report = validate_daily_workflow_evidence(
        runs_root=runs_root,
        output_dir=tmp_path / "validation",
        handoff_file=handoff_json,
    )

    assert report["validation_status"] == "HOLD_EVIDENCE_INCOMPLETE"
    failed_ids = {check["check_id"] for check in report["checks"] if check["status"] == "FAIL"}
    assert "module140.source.exists" in failed_ids


def test_module142_blocks_unsafe_handoff_flags(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    day_dir = runs_root / "HQE_FORWARD_PAPER_DAILY_WORKFLOW_20260709"
    day_dir.mkdir(parents=True)

    module140_source = _module140_summary(day_dir)

    unsafe_lock = dict(SAFETY_LOCK)
    unsafe_lock["real_orders"] = True
    unsafe_lock["broker_execution"] = True

    handoff_json = _module141_handoff(day_dir, module140_source, safety_lock=unsafe_lock)

    report = validate_daily_workflow_evidence(
        runs_root=runs_root,
        output_dir=tmp_path / "validation",
        handoff_file=handoff_json,
        daily_output_file=module140_source,
    )

    assert report["validation_status"] == "BLOCKED_SAFETY_RISK"
    safety_fails = [
        check
        for check in report["checks"]
        if check["status"] == "FAIL" and check["severity"] == "SAFETY"
    ]
    assert any(check["check_id"] == "module141.real_orders.false" for check in safety_fails)
    assert any(check["check_id"] == "module141.broker_execution.false" for check in safety_fails)


def test_module142_blocks_safety_risk_pattern_in_source(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    day_dir = runs_root / "HQE_FORWARD_PAPER_DAILY_WORKFLOW_20260709"
    day_dir.mkdir(parents=True)

    source_file = _module140_summary(day_dir)
    source_file.write_text(
        json.dumps(
            {
                "module": "Module 140 - Forward Paper Daily Workflow Wrapper",
                "workflow_status": "PASS_PAPER_ONLY",
                "safety_lock": SAFETY_LOCK,
                "bad_code_preview": "place_order(symbol='NIFTY')",
            }
        ),
        encoding="utf-8",
    )
    handoff_json = _module141_handoff(day_dir, source_file)

    report = validate_daily_workflow_evidence(
        runs_root=runs_root,
        output_dir=tmp_path / "validation",
        handoff_file=handoff_json,
        daily_output_file=source_file,
    )

    assert report["validation_status"] == "BLOCKED_SAFETY_RISK"
    assert any(check["check_id"] == "safety.risk_pattern_scan" and check["status"] == "FAIL" for check in report["checks"])
