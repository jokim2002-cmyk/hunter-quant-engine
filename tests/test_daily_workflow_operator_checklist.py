from __future__ import annotations

import json
from pathlib import Path

from scripts.build_daily_workflow_operator_checklist import (
    SAFETY_LOCK,
    build_pack,
    find_source_context,
)


def test_module_141_builds_handoff_from_explicit_daily_output_file(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    day_dir = runs_root / "HQE_FORWARD_PAPER_DAILY_WORKFLOW_20260709"
    day_dir.mkdir(parents=True)

    source_file = day_dir / "FORWARD_PAPER_DAILY_WORKFLOW_SUMMARY.json"
    source_file.write_text(
        json.dumps(
            {
                "workflow_status": "PASS_PAPER_ONLY",
                "trading_date": "2026-07-09",
                "completed_trades": 0,
                "dashboard_index": str(day_dir / "dashboard_index.html"),
                "master_ledger": str(day_dir / "FORWARD_VALIDATION_MASTER_LEDGER.csv"),
            }
        ),
        encoding="utf-8",
    )

    (day_dir / "DAY_001_FORWARD_TRADE_LOG.csv").write_text("trade_id,status\n", encoding="utf-8")
    (day_dir / "FORWARD_VALIDATION_MASTER_LEDGER.csv").write_text("day,status\n1,PAPER_ONLY\n", encoding="utf-8")
    (day_dir / "DASHBOARD_INDEX.html").write_text("<html>paper dashboard</html>", encoding="utf-8")

    out_dir = tmp_path / "operator_pack"

    pack = build_pack(
        runs_root=runs_root,
        output_dir=out_dir,
        daily_output_file=source_file,
    )

    assert pack["source"]["source_status"] == "found_explicit_file"
    assert pack["source"]["extracted_status_fields"]["workflow_status"] == "PASS_PAPER_ONLY"
    assert pack["safety_lock"]["paper_simulation_only"] is True
    assert pack["safety_lock"]["broker_execution"] is False
    assert pack["safety_lock"]["real_orders"] is False
    assert pack["safety_lock"]["auto_trading"] is False
    assert pack["safety_lock"]["option_selling"] is False
    assert pack["safety_lock"]["profitability_claim"] is False

    markdown_path = out_dir / "MODULE_141_OPERATOR_HANDOFF.md"
    json_path = out_dir / "MODULE_141_OPERATOR_HANDOFF.json"
    csv_path = out_dir / "MODULE_141_FILE_INSPECTION_TARGETS.csv"

    assert markdown_path.exists()
    assert json_path.exists()
    assert csv_path.exists()

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Paper/simulation only: `YES`" in markdown
    assert "This is not a profitability claim" in markdown
    assert "Real money/broker/orders/auto trading/option selling: all NO" in markdown


def test_module_141_scan_finds_latest_daily_workflow_summary(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    old_dir = runs_root / "old"
    new_dir = runs_root / "new"
    old_dir.mkdir(parents=True)
    new_dir.mkdir(parents=True)

    old_file = old_dir / "daily_workflow_summary.json"
    old_file.write_text(json.dumps({"workflow_status": "OLD"}), encoding="utf-8")

    new_file = new_dir / "forward_paper_daily_workflow_summary.json"
    new_file.write_text(json.dumps({"workflow_status": "NEW", "trade_count": 3}), encoding="utf-8")

    # Make the new file definitely latest on filesystems with coarse mtime.
    old_time = 1_700_000_000
    new_time = old_time + 100
    import os

    os.utime(old_file, (old_time, old_time))
    os.utime(new_file, (new_time, new_time))

    context = find_source_context(runs_root=runs_root)
    assert context.source_status == "found_by_scan"
    assert context.source_file == new_file
    assert context.parsed_summary["workflow_status"] == "NEW"


def test_module_141_generates_generic_pack_when_module_140_output_missing(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    out_dir = tmp_path / "operator_pack"
    pack = build_pack(runs_root=runs_root, output_dir=out_dir)

    assert pack["source"]["source_status"] == "not_found"
    assert (out_dir / "MODULE_141_OPERATOR_HANDOFF.md").exists()
    assert (out_dir / "MODULE_141_OPERATOR_HANDOFF.json").exists()
    assert (out_dir / "MODULE_141_FILE_INSPECTION_TARGETS.csv").exists()

    saved = json.loads((out_dir / "MODULE_141_OPERATOR_HANDOFF.json").read_text(encoding="utf-8"))
    assert saved["safety_lock"] == SAFETY_LOCK
    assert "before_market" in saved["operator_checklist"]
