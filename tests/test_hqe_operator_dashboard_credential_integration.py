from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_operator_live_status_dashboard.py"


def load_module():
    scripts_dir = str(SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    spec = importlib.util.spec_from_file_location("hqe_dashboard_credential_integration_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dashboard_credential_payload(monkeypatch, tmp_path):
    module = load_module()

    monkeypatch.setattr(
        module,
        "collect_health",
        lambda workspace, write=True: {
            "overall_health": "DEGRADED_DATA_STALE",
            "heartbeat_ist": "10-07-2026 11:00:00 AM IST",
            "last_successful_data_update_ist": "10-07-2026 10:30:00 AM IST",
            "consecutive_stale_cycles": 3,
            "fetch_failure_reason": "NONE_REPORTED",
        },
    )
    monkeypatch.setattr(
        module,
        "build_truth",
        lambda workspace: {
            "fetch_truth": "FETCH_COMPLETED_BUT_CANDLE_STALE",
            "latest_candle_ist": "10-07-2026 10:20:00 AM IST",
            "latest_candle_age_minutes": 40.0,
            "canonical_watch_pid": 100,
            "watch_process_count": 2,
            "operator_recommendation": "RESTART_WATCH_ONLY_AFTER_FETCH_DIAGNOSTIC",
        },
    )
    monkeypatch.setattr(
        module,
        "build_credential_status",
        lambda repo, workspace, run_revalidation=False: {
            "auth_status": "AUTH_FAILED_CODE_-16",
            "recommendation": "REFRESH_FYERS_ACCESS_TOKEN_AND_REVALIDATE",
            "client_id": {"fingerprint": "CLIENT123", "hygiene_status": "PASS"},
            "access_token": {"fingerprint": "TOKEN123", "hygiene_status": "PASS"},
        },
    )

    payload = module.derive_status(tmp_path)

    assert payload["fyers_auth_status"] == "AUTH_FAILED_CODE_-16"
    assert payload["access_token_fingerprint"] == "TOKEN123"
    assert payload["real_orders_enabled"] is False
