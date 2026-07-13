from __future__ import annotations

import importlib
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load_guard():
    sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module("hqe_current_day_session_guard")


def write_report(path: Path, day_label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "day_label": day_label,
                "paper_only": True,
                "real_orders_allowed": False,
            }
        ),
        encoding="utf-8",
    )


def test_today_report_is_ready(tmp_path):
    guard = load_guard()
    report = tmp_path / "daily.json"
    write_report(report, "DAY_004_2026-07-13")

    status = guard.current_day_report_status(
        tmp_path,
        now=date(2026, 7, 13),
        report_path=report,
        evidence_path=report,
    )
    assert status["state"] == "TODAY_READY"
    assert status["today_ready"] is True
    assert status["report_date"] == "2026-07-13"


def test_old_report_is_blocked(tmp_path):
    guard = load_guard()
    report = tmp_path / "DAY_001_2026-07-10" / "daily.json"
    write_report(report, "DAY_001_2026-07-10")

    status = guard.current_day_report_status(
        tmp_path,
        now=date(2026, 7, 13),
        report_path=report,
        evidence_path=report,
    )
    assert status["state"] == "STALE_REPORT_BLOCKED"
    assert status["today_ready"] is False
    assert "latest report is from 10 Jul 2026" in status["message"]


def test_undated_report_is_blocked(tmp_path):
    guard = load_guard()
    report = tmp_path / "daily.json"
    report.write_text('{"paper_only": true}', encoding="utf-8")

    status = guard.current_day_report_status(
        tmp_path,
        now=date(2026, 7, 13),
        report_path=report,
        evidence_path=None,
    )
    assert status["state"] == "REPORT_DATE_UNVERIFIED"
    assert status["today_ready"] is False


def test_app_has_all_current_day_guards():
    text = APP.read_text(encoding="utf-8-sig")
    guard_text = (
        SCRIPTS / "hqe_current_day_session_guard.py"
    ).read_text(encoding="utf-8-sig")

    assert "current_day_report_status" in text
    assert "freshness[\"message\"]" in text
    assert "Historical report opening is blocked" in guard_text
    assert "Waiting for fresh current-day data" in text
    assert "def today_report_candidates" in text
    assert "def open_report" in text
    assert "def open_daily_close_artifact" in text
    assert 'text="Open Trader Report"' in text
    assert 'text="Open Technical Evidence (JSON)"' in text
    assert 'text="Refresh Trader Report"' in text
