from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
MODULE = SCRIPTS / "hqe_automatic_daily_current_day_workflow.py"
IST = ZoneInfo("Asia/Kolkata")


def load_module():
    name = "hqe_expiry_day_next_week_selection_test"
    spec = importlib.util.spec_from_file_location(name, MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def expiry_rows():
    return [
        {
            "date": "14-07-2026",
            "expiry": 1784023200,
            "expiry_flag": "W",
        },
        {
            "date": "21-07-2026",
            "expiry": 1784628000,
            "expiry_flag": "W",
        },
        {
            "date": "28-07-2026",
            "expiry": 1785232800,
            "expiry_flag": "M",
        },
    ]


def test_expiry_day_selects_next_genuine_listed_expiry():
    module = load_module()
    selected = module._next_non_expiring_expiry_timestamp(
        expiry_rows(),
        "2026-07-14",
        min_dte=1,
    )
    assert selected == "1784628000"


def test_normal_day_keeps_default_nearest_expiry_request():
    module = load_module()
    selected = module._next_non_expiring_expiry_timestamp(
        expiry_rows()[1:],
        "2026-07-14",
        min_dte=1,
    )
    assert selected == ""


def test_run_cycle_requeries_only_on_dte_zero_expiry_day(tmp_path):
    module = load_module()
    calls = []

    chain_ready = {
        "readiness": {
            "both_sides_ready": True,
            "ce_count": 41,
            "pe_count": 41,
        },
        "expiry_data": expiry_rows(),
    }

    def option_chain(**kwargs):
        calls.append(dict(kwargs))
        return dict(chain_ready)

    history = {
        "status": "SELECTED_CE_PE_HISTORY_5M_READY",
        "rows": {
            "ce": 20,
            "pe": 20,
            "combined": 40,
        },
        "selection": {
            "strike_price": 24200,
            "dte": 7,
        },
    }
    replay = {
        "status": "RECORDED_DATA_REPLAY_EVALUATED",
        "index_rows": 30,
        "evaluation_count": 10,
        "accepted_evaluation_count": 0,
        "decision_counts": {
            "LONG": 0,
            "SHORT": 0,
            "NEUTRAL": 10,
        },
        "accepted_side_counts": {},
        "signal_generated": False,
        "outputs": {
            "report_html": "report.html",
            "summary_json": "summary.json",
            "evaluations_csv": "evaluations.csv",
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

    deps = module.WorkflowDependencies(
        auth_status=lambda: {
            "status": "READY",
            "access_token_present": True,
        },
        apply_auth=lambda **kwargs: {"status": "APPLIED"},
        option_chain=option_chain,
        selected_history=lambda **kwargs: history,
        recorded_replay=lambda **kwargs: replay,
    )

    payload = module.run_cycle(
        workspace=tmp_path,
        now=datetime(2026, 7, 14, 11, 0, tzinfo=IST),
        dependencies=deps,
    )

    assert payload["status"] == "COMPLETE"
    assert len(calls) == 2
    assert calls[0]["expiry_timestamp"] == ""
    assert calls[1]["expiry_timestamp"] == "1784628000"
    assert payload["position_opened"] is False
    assert payload["pnl_calculated"] is False
    assert payload["real_orders_allowed"] is False


def test_source_preserves_execution_blocks():
    text = MODULE.read_text(encoding="utf-8-sig")
    assert "HQE_EXPIRY_DAY_NEXT_WEEK_SELECTION_V1" in text
    forbidden = (
        ".place_order(",
        ".submit_order(",
        ".modify_order(",
        ".cancel_order(",
        ".exit_positions(",
    )
    assert not any(marker in text for marker in forbidden)
