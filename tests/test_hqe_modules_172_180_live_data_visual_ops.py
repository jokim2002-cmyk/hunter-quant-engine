from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_script(script: str, workspace: Path, *extra: str):
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), "--workspace", str(workspace), "--write", *extra],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(cp.stdout)


def test_module_172_ltp_offline_default_no_api(tmp_path: Path):
    payload = run_script("hqe_fyers_live_data_only_ltp_test.py", tmp_path)
    assert payload["ltp_test_status"] == "PASS"
    assert payload["external_api_calls_executed"] is False
    assert payload["order_api_invoked"] is False
    assert payload["broker_execution_invoked"] is False


def test_module_173_writes_sample_schema_no_live_call(tmp_path: Path):
    payload = run_script("hqe_fyers_historical_5m_data_only_fetcher.py", tmp_path)
    assert payload["historical_5m_fetcher_status"] == "PASS"
    assert Path(payload["sample_schema_file"]).exists()
    assert payload["external_api_calls_executed"] is False


def test_symbol_guard_allows_nifty_and_blocks_orders(tmp_path: Path):
    payload = run_script("hqe_live_data_symbol_config_guard.py", tmp_path, "--symbol", "NSE:NIFTY50-INDEX")
    assert payload["symbol_config_guard_status"] == "PASS"
    assert payload["option_selling_allowed"] is False
    assert payload["order_api_invoked_by_module_174"] is False


def test_dashboard_v2_launcher_and_report_index(tmp_path: Path):
    dash = run_script("hqe_local_visual_dashboard_live_paper_v2.py", tmp_path)
    assert dash["visual_dashboard_v2_status"] == "PASS"
    assert Path(dash["launcher_path"]).exists()
    index = run_script("hqe_live_paper_report_index_v2.py", tmp_path)
    assert index["report_index_v2_status"] == "PASS"
    assert Path(index["html_index"]).exists()


def test_runner_creates_final_readiness(tmp_path: Path):
    scripts = [
        "hqe_fyers_live_data_only_ltp_test.py",
        "hqe_fyers_historical_5m_data_only_fetcher.py",
        "hqe_live_data_symbol_config_guard.py",
        "hqe_day2_next_paper_session_generator.py",
        "hqe_local_visual_dashboard_live_paper_v2.py",
        "hqe_one_click_live_paper_session_launcher_plan.py",
        "hqe_live_paper_report_index_v2.py",
        "hqe_startup_shortcut_installer_review_pack.py",
    ]
    for script in scripts:
        run_script(script, tmp_path)
    final = run_script("hqe_live_paper_operations_final_readiness_pack.py", tmp_path)
    assert final["expected_status_files_count"] == 8
    assert final["existing_status_files_count"] == 8
    assert final["ready_for_real_money"] is False
    assert final["order_api_invoked"] is False


def test_all_guard_checks_pass():
    for script in [
        "hqe_fyers_live_data_only_ltp_test.py",
        "hqe_fyers_historical_5m_data_only_fetcher.py",
        "hqe_live_data_symbol_config_guard.py",
        "hqe_day2_next_paper_session_generator.py",
        "hqe_local_visual_dashboard_live_paper_v2.py",
        "hqe_one_click_live_paper_session_launcher_plan.py",
        "hqe_live_paper_report_index_v2.py",
        "hqe_startup_shortcut_installer_review_pack.py",
        "hqe_live_paper_operations_final_readiness_pack.py",
    ]:
        cp = subprocess.run([sys.executable, str(ROOT / "scripts" / script), "--guard-check"], cwd=str(ROOT), text=True, capture_output=True, check=True)
        payload = json.loads(cp.stdout)
        assert payload["guard_check_status"] == "PASS"
        assert payload["order_api_invoked"] is False
