from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "hqe_recorded_replay_today_report.py"
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def load_module():
    spec = importlib.util.spec_from_file_location("replay_today", MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_payload(workspace: Path, day: str, files: bool = True) -> None:
    folder = workspace / "HQE_CURRENT_DAY_RECORDED_REPLAY" / day
    folder.mkdir(parents=True)
    report = folder / "report.html"
    summary = folder / "summary.json"
    evaluations = folder / "evaluations.csv"
    if files:
        report.write_text("<html></html>", encoding="utf-8")
        summary.write_text("{}", encoding="utf-8")
        evaluations.write_text("timestamp\n", encoding="utf-8")

    payload = {
        "status": "RECORDED_DATA_REPLAY_EVALUATED",
        "trading_date": day,
        "evaluation_count": 55,
        "accepted_evaluation_count": 0,
        "decision_counts": {"LONG": 0, "SHORT": 0, "NEUTRAL": 55},
        "accepted_side_counts": {},
        "signal_generated": False,
        "outputs": {
            "report_html": str(report),
            "summary_json": str(summary),
            "evaluations_csv": str(evaluations),
        },
        "replay_truth": {
            "paper_trade_created": False,
            "position_opened": False,
            "pnl_calculated": False,
            "historical_execution_claim": False,
        },
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
    }
    (workspace / "HQE_CURRENT_DAY_RECORDED_REPLAY_STATUS.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_current_day_replay_ready(tmp_path):
    module = load_module()
    write_payload(tmp_path, "2026-07-13")
    status = module.recorded_replay_status(
        tmp_path,
        now=date(2026, 7, 13),
    )
    assert status["ready"] is True
    assert status["state"] == "RECORDED_REPLAY_READY"
    assert status["decision_counts"]["NEUTRAL"] == 55


def test_stale_and_missing_files_are_blocked(tmp_path):
    module = load_module()
    write_payload(tmp_path, "2026-07-12")
    stale = module.recorded_replay_status(
        tmp_path,
        now=date(2026, 7, 13),
    )
    assert stale["state"] == "RECORDED_REPLAY_STALE_BLOCKED"

    other = tmp_path / "other"
    write_payload(other, "2026-07-13", files=False)
    missing = module.recorded_replay_status(
        other,
        now=date(2026, 7, 13),
    )
    assert missing["state"] == "RECORDED_REPLAY_FILES_MISSING"


def test_app_has_replay_today_report_integration():
    text = APP.read_text(encoding="utf-8-sig")
    for marker in (
        "recorded_replay_status",
        "RECORDED REPLAY READY",
        "Open Recorded Replay Evidence (JSON)",
        "LONG -> CE BUY",
        "SHORT -> PE BUY",
        "NEUTRAL -> NO TRADE",
        "No position or P&L was created",
    ):
        assert marker in text
