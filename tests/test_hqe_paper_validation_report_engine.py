from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_paper_validation_report_engine.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_trade_log(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["trade_id", "status"])
        for index in range(count):
            writer.writerow([index + 1, "PAPER"])


def test_progress_weekly_and_no_trade_reason(tmp_path):
    module = load("validation_progress")
    trade_log = tmp_path / "DAY_001_FORWARD_TRADE_LOG.csv"
    write_trade_log(trade_log, 2)
    no_trade_status = tmp_path / "DAY_002_STATUS.json"
    no_trade_status.write_text(
        json.dumps(
            {
                "status": "NO_TRADE",
                "reason": "Low efficiency sideways market.",
            }
        ),
        encoding="utf-8",
    )

    sessions = [
        {
            "day_number": 1,
            "day_label": "DAY_001",
            "trading_date": "2026-07-10",
            "artifact_count": 1,
            "artifacts": [
                {
                    "category": "trade_log",
                    "path": str(trade_log),
                }
            ],
        },
        {
            "day_number": 2,
            "day_label": "DAY_002",
            "trading_date": "2026-07-13",
            "artifact_count": 1,
            "artifacts": [
                {
                    "category": "status",
                    "path": str(no_trade_status),
                }
            ],
        },
    ]
    daily = module.build_daily_records(sessions)
    progress = module.progress_from_daily_records(daily)
    weekly = module.weekly_summaries(daily)

    assert progress["observed_days"] == 2
    assert progress["observed_trades"] == 2
    assert progress["valid_trade_days"] == 1
    assert progress["no_trade_days"] == 1
    assert progress["expiry_weeks"] == 2
    assert daily[1]["no_trade_reason"] == (
        "SIDEWAYS_OR_LOW_EFFICIENCY"
    )
    assert len(weekly) == 2


def test_no_trade_classifier_categories():
    module = load("validation_reasons")
    assert module.classify_no_trade_reason(
        "No valid signal. Conditions not met."
    ) == "NO_VALID_SIGNAL"
    assert module.classify_no_trade_reason(
        "Fyers token expired and login required."
    ) == "BROKER_AUTH_OR_TOKEN"
    assert module.classify_no_trade_reason(
        "Minimum DTE and option LTP range rejected."
    ) == "OPTION_FILTER_REJECTED"


def test_decision_priority():
    module = load("validation_decision")
    incomplete = {
        "validation_minimums_complete": False,
    }
    complete = {
        "validation_minimums_complete": True,
    }

    kill = module.decision_status(
        progress=complete,
        drift={"drift_detected": False},
        safety={
            "kill_switch_status": "TRIGGERED",
            "overall_status": "ATTENTION_REQUIRED",
        },
    )
    assert kill["status"] == "KILL_SWITCH_TRIGGERED"

    drift = module.decision_status(
        progress=complete,
        drift={"drift_detected": True},
        safety={
            "kill_switch_status": "CLEAR",
            "overall_status": "LOCKED_SAFE",
        },
    )
    assert drift["status"] == "DRIFT_REVIEW_REQUIRED"

    hold = module.decision_status(
        progress=incomplete,
        drift={"drift_detected": False},
        safety={
            "kill_switch_status": "CLEAR",
            "overall_status": "LOCKED_SAFE",
        },
    )
    assert hold["status"] == "HOLD_MORE_DATA_REQUIRED"

    ready = module.decision_status(
        progress=complete,
        drift={"drift_detected": False},
        safety={
            "kill_switch_status": "CLEAR",
            "overall_status": "LOCKED_SAFE",
        },
    )
    assert ready["status"] == "READY_FOR_FORMAL_REVIEW"


def test_strategy_drift_defaults_to_locked_candidate(tmp_path):
    module = load("validation_drift")
    snapshot = module.strategy_drift_snapshot(
        REPO,
        tmp_path / "workspace",
    )
    assert snapshot["drift_detected"] is False
    assert snapshot["status"] == "LOCKED_CANDIDATE_DEFAULT"


def test_report_pack_exports_all_formats(tmp_path, monkeypatch):
    module = load("validation_exports")

    fake_snapshot = {
        "version": module.VERSION,
        "generated_at_utc": "2026-07-10T00:00:00+00:00",
        "display_text": "test",
        "decision": {
            "status": "HOLD_MORE_DATA_REQUIRED",
            "message": "More data required.",
        },
        "progress": {
            "observed_days": 1,
            "observed_trades": 0,
            "valid_trade_days": 0,
            "no_trade_days": 1,
            "expiry_weeks": 1,
            "minimum_days": 20,
            "minimum_trades": 30,
            "minimum_expiry_weeks": 4,
        },
        "strategy_drift": {
            "status": "LOCKED_CANDIDATE_DEFAULT",
            "message": "Locked baseline.",
        },
        "safety": {
            "overall_status": "LOCKED_SAFE",
            "kill_switch_status": "CLEAR",
        },
        "daily_records": [
            {
                "day_number": 1,
                "day_label": "DAY_001",
                "trading_date": "2026-07-10",
                "iso_week": "2026-W28",
                "trade_count": 0,
                "valid_trade_day": False,
                "no_trade_reason": "NO_VALID_SIGNAL",
                "artifact_count": 1,
                "day_folder": "x",
            }
        ],
        "weekly_summaries": [
            {
                "iso_week": "2026-W28",
                "observed_days": 1,
                "trade_count": 0,
                "valid_trade_days": 0,
                "no_trade_days": 1,
                "top_no_trade_reason": "NO_VALID_SIGNAL",
            }
        ],
        "no_trade_reasons": [
            {
                "reason": "NO_VALID_SIGNAL",
                "count": 1,
                "percent_of_no_trade_days": 100.0,
            }
        ],
    }

    monkeypatch.setattr(
        module,
        "validation_snapshot",
        lambda _repo, _workspace: fake_snapshot,
    )
    payload = module.generate_report_pack(
        REPO,
        tmp_path / "workspace",
    )

    assert payload["status"] == "PASS"
    assert Path(payload["json_path"]).exists()
    assert Path(payload["html_path"]).exists()
    assert Path(payload["daily_csv_path"]).exists()
    assert Path(payload["weekly_csv_path"]).exists()
    assert Path(payload["reasons_csv_path"]).exists()
    assert Path(payload["zip_path"]).exists()


def test_engine_guard_locks_execution():
    module = load("validation_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["paper_only"] is True
    assert payload["report_formats"] == [
        "JSON",
        "HTML",
        "CSV",
        "ZIP",
    ]
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["option_selling_enabled"] is False
