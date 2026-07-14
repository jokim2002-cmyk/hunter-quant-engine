from __future__ import annotations

import ast
import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
MODULE = SCRIPTS / "hqe_automatic_daily_current_day_workflow.py"
APP = SCRIPTS / "hqe_product_app_v2.py"
IST = ZoneInfo("Asia/Kolkata")


def load_module():
    spec = importlib.util.spec_from_file_location(
        "hqe_automatic_daily_current_day_workflow_test",
        MODULE,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ready_dependencies(module):
    chain = {
        "readiness": {
            "both_sides_ready": True,
            "ce_count": 41,
            "pe_count": 41,
        }
    }
    history = {
        "status": "SELECTED_CE_PE_HISTORY_5M_READY",
        "rows": {
            "ce": 20,
            "pe": 20,
            "combined": 40,
        },
        "selection": {
            "strike_price": 24200,
            "dte": 1,
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

    return module.WorkflowDependencies(
        auth_status=lambda: {
            "status": "READY",
            "access_token_present": True,
        },
        apply_auth=lambda **kwargs: {"status": "APPLIED"},
        option_chain=lambda **kwargs: chain,
        selected_history=lambda **kwargs: history,
        recorded_replay=lambda **kwargs: replay,
    )


def test_market_phase_guards_weekend_pre_market_and_active():
    module = load_module()
    assert module.market_phase(
        datetime(2026, 7, 12, 10, 0, tzinfo=IST)
    ) == "WEEKEND"
    assert module.market_phase(
        datetime(2026, 7, 14, 8, 30, tzinfo=IST)
    ) == "PRE_MARKET"
    assert module.market_phase(
        datetime(2026, 7, 14, 11, 30, tzinfo=IST)
    ) == "MARKET_ACTIVE"
    assert module.market_phase(
        datetime(2026, 7, 14, 16, 0, tzinfo=IST)
    ) == "POST_MARKET"


def test_complete_cycle_uses_all_three_data_only_stages(tmp_path):
    module = load_module()
    payload = module.run_cycle(
        workspace=tmp_path,
        now=datetime(2026, 7, 14, 11, 30, tzinfo=IST),
        dependencies=ready_dependencies(module),
    )

    assert payload["status"] == "COMPLETE"
    assert payload["option_chain"]["ce_rows"] == 41
    assert payload["option_chain"]["pe_rows"] == 41
    assert payload["selected_history"]["combined_rows"] == 40
    assert payload["recorded_replay"]["evaluation_count"] == 10
    assert payload["position_opened"] is False
    assert payload["pnl_calculated"] is False
    assert payload["real_orders_allowed"] is False


def test_insufficient_bars_waits_and_retries(tmp_path):
    module = load_module()
    deps = ready_dependencies(module)

    def not_enough(**kwargs):
        raise RuntimeError(
            "Not enough NIFTY 5-minute bars for SMC replay. "
            "Required=21, actual=12."
        )

    deps = module.WorkflowDependencies(
        auth_status=deps.auth_status,
        apply_auth=deps.apply_auth,
        option_chain=deps.option_chain,
        selected_history=deps.selected_history,
        recorded_replay=not_enough,
    )

    payload = module.run_cycle(
        workspace=tmp_path,
        now=datetime(2026, 7, 14, 10, 0, tzinfo=IST),
        dependencies=deps,
    )

    assert payload["status"] == "WAITING_MORE_DATA"
    assert payload["next_retry_seconds"] == 300


def test_weekend_does_not_call_broker_data(tmp_path):
    module = load_module()

    def forbidden(*args, **kwargs):
        raise AssertionError("No data call is allowed on weekend guard.")

    deps = module.WorkflowDependencies(
        auth_status=forbidden,
        apply_auth=forbidden,
        option_chain=forbidden,
        selected_history=forbidden,
        recorded_replay=forbidden,
    )

    payload = module.run_cycle(
        workspace=tmp_path,
        now=datetime(2026, 7, 12, 10, 0, tzinfo=IST),
        dependencies=deps,
    )

    assert payload["status"] == "MARKET_CLOSED_WEEKEND"


def test_app_launches_non_blocking_automatic_worker():
    text = APP.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)

    assert (
        "from hqe_automatic_daily_current_day_workflow "
        "import launch_app_background_worker"
    ) in text
    assert "HQE_AUTOMATIC_DAILY_WORKFLOW_V1" in text
    assert "lambda: launch_app_background_worker(workspace)" in text

    mainloop_lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "mainloop"
    ]
    launch_lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "launch_app_background_worker"
    ]
    assert mainloop_lines
    assert launch_lines
    assert min(launch_lines) < min(mainloop_lines)


def test_source_has_no_order_or_position_execution_calls():
    text = MODULE.read_text(encoding="utf-8-sig")
    forbidden = (
        ".place_order(",
        ".submit_order(",
        ".modify_order(",
        ".cancel_order(",
        ".exit_positions(",
        "POSITION_OPENED",
    )
    assert not any(marker in text for marker in forbidden)
    assert "daemon=True" in text
    assert "recorded_data_evaluation_only" in text
