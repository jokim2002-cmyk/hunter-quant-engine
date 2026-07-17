from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_multi_strategy_phase4_complete_rehearsal.py"


def load_module():
    spec = importlib.util.spec_from_file_location("phase4_complete_rehearsal", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_phase4_complete_rehearsal_passes(tmp_path):
    module = load_module()
    payload = module.run_rehearsal(tmp_path)
    assert payload["status"] == "PASS"
    assert payload["flat_cycle"]["prepare_status"] == "CUTOVER_PREPARED_PAPER_ONLY"
    assert payload["flat_cycle"]["open_event"] == "POSITION_OPENED"
    assert payload["flat_cycle"]["close_event"] == "POSITION_CLOSED"
    assert payload["flat_cycle"]["open_switch_blocked"] is True
    assert payload["flat_cycle"]["running_switch_blocked"] is True
    assert payload["flat_cycle"]["legacy_unchanged_during_namespaced_run"] is True
    assert payload["flat_cycle"]["rollback_complete"] is True
    assert payload["open_migration"]["state_hash_preserved"] is True
    assert payload["open_migration"]["ledger_hash_preserved"] is True
    assert payload["open_migration"]["open_state_preserved"] is True
    assert payload["open_migration"]["rollback_while_open_blocked"] is True
    assert payload["real_orders_allowed"] is False
    assert payload["broker_execution_allowed"] is False
    assert payload["real_money_allowed"] is False
    assert len(payload["evidence_hash"]) == 64
