from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_operator_acceptance_engine.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_safety_flag_detection_blocks_component():
    module = load("acceptance_safety")
    payload = {
        "display_text": "unsafe",
        "nested": {
            "real_orders_enabled": True,
        },
    }
    result = module.evaluate_component_payload(
        "Unsafe Component",
        payload,
    )
    assert result["status"] == "FAILED"
    assert result["unsafe_flags"] == [
        "nested.real_orders_enabled"
    ]


def test_safe_component_payload_passes():
    module = load("acceptance_component")
    result = module.evaluate_component_payload(
        "Safe Component",
        {
            "display_text": "Component ready.",
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        },
    )
    assert result["status"] == "PASS"


def test_acceptance_decision_priority():
    module = load("acceptance_decision")
    blocked = module.acceptance_decision(
        [
            {"status": "PASS"},
            {"status": "FAILED"},
        ]
    )
    assert blocked["status"] == "BLOCKED"

    review = module.acceptance_decision(
        [
            {"status": "PASS"},
            {"status": "CHECK_REQUIRED"},
        ]
    )
    assert review["status"] == "ACCEPTED_WITH_REVIEW"

    accepted = module.acceptance_decision(
        [{"status": "PASS"}]
    )
    assert accepted["status"] == "ACCEPTED_FOR_PAPER_ONLY_RC"


def test_html_report_contains_safety_and_decision():
    module = load("acceptance_html")
    snapshot = {
        "generated_at_utc": "2026-07-10T00:00:00+00:00",
        "decision": {
            "status": "ACCEPTED_FOR_PAPER_ONLY_RC",
            "message": "Accepted.",
        },
        "journey": "One Icon → Review",
        "checks": [
            {
                "status": "PASS",
                "name": "Launcher",
                "message": "Ready.",
            }
        ],
    }
    rendered = module.render_html(snapshot)
    assert "ACCEPTED_FOR_PAPER_ONLY_RC" in rendered
    assert "REAL ORDERS: NO" in rendered
    assert "This is not a profitability claim." in rendered


def test_existing_freeze_manifest_and_launcher_pass():
    module = load("acceptance_existing_release")
    from hqe_release_candidate_audit import (
        launcher_check,
        verify_freeze_manifest,
    )

    assert launcher_check(REPO)["status"] == "PASS"
    assert verify_freeze_manifest(REPO)["status"] == "PASS"


def test_guard_locks_execution():
    module = load("acceptance_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["read_only_snapshots"] is True
    assert payload["new_product_features"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["option_selling_enabled"] is False
