from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_final_rc_signoff_engine.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def acceptance_payload(status: str) -> dict:
    return {
        "generated_at_utc": "2026-07-10T00:00:00+00:00",
        "decision": {
            "status": status,
            "message": "Acceptance decision.",
        },
        "check_count": 10,
        "passed_count": 10 if status != "ACCEPTED_WITH_REVIEW" else 8,
        "review_count": 2 if status == "ACCEPTED_WITH_REVIEW" else 0,
        "failed_count": 0,
        "operations_executed": {
            "paper_watch": False,
            "market_data_fetch": False,
            "backtest": False,
            "report_generation": False,
            "backup": False,
            "restore": False,
            "broker_action": False,
            "real_order": False,
        },
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def test_acceptance_validation_and_status_mapping():
    module = load("signoff_validation")
    accepted = module.validate_acceptance_report(
        acceptance_payload("ACCEPTED_FOR_PAPER_ONLY_RC")
    )
    assert accepted["valid_for_signoff"] is True
    assert module.signoff_status(
        accepted["decision_status"]
    ) == "PAPER_ONLY_RC_SIGNED_OFF"

    review = module.validate_acceptance_report(
        acceptance_payload("ACCEPTED_WITH_REVIEW")
    )
    assert review["valid_for_signoff"] is True
    assert review["warnings"]
    assert module.signoff_status(
        review["decision_status"]
    ) == "PAPER_ONLY_RC_CONDITIONALLY_SIGNED_OFF"


def test_blocked_acceptance_is_rejected():
    module = load("signoff_blocked")
    payload = acceptance_payload("BLOCKED")
    payload["failed_count"] = 1
    result = module.validate_acceptance_report(payload)
    assert result["valid_for_signoff"] is False
    assert any(
        "blocked" in error.lower()
        for error in result["errors"]
    )


def test_enabled_execution_flag_is_rejected():
    module = load("signoff_execution_flag")
    payload = acceptance_payload(
        "ACCEPTED_FOR_PAPER_ONLY_RC"
    )
    payload["nested"] = {"real_orders_enabled": True}
    result = module.validate_acceptance_report(payload)
    assert result["valid_for_signoff"] is False
    assert any(
        "execution flags" in error.lower()
        for error in result["errors"]
    )


def test_create_signoff_preserves_acceptance_decision(tmp_path):
    module = load("signoff_create")
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    report_dir = (
        workspace
        / "HQE_RELEASE_CENTER"
        / "operator_acceptance"
        / "ACCEPTANCE_20260710_000000"
    )
    report_dir.mkdir(parents=True)
    report = acceptance_payload("ACCEPTED_WITH_REVIEW")
    report_path = report_dir / "HQE_OPERATOR_ACCEPTANCE.json"
    report_path.write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    result = module.create_signoff_manifest(
        repo,
        workspace,
        source_head="3bb135d",
    )
    assert result["signoff_status"] == (
        "PAPER_ONLY_RC_CONDITIONALLY_SIGNED_OFF"
    )
    assert result["review_items_remain"] is True
    assert result["real_orders_enabled"] is False
    assert Path(result["signoff_path"]).exists()


def test_guard_locks_execution():
    module = load("signoff_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["new_product_features"] is False
    assert payload["blocked_acceptance_rejected"] is True
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["option_selling_enabled"] is False
