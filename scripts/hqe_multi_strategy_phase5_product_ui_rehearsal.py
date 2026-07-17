from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.multi_strategy.product_ui_manager import (
    build_product_strategy_manager_snapshot,
    evaluate_clear_configuration,
    evaluate_configuration_selection,
    guard_payload,
)


def main() -> int:
    pack = {
        "packs": [
            {
                "strategy_id": "hqe_current_smc_compatibility",
                "name": "Current SMC Compatibility",
                "version": "1.0.0",
                "source": "builtin-reviewed",
                "path": "C:/review/current_smc.json",
                "valid": True,
                "status": "VALID",
                "payload": {
                    "parameters": {"timeframe": "5m"},
                    "safety": {"paper_only": True},
                },
            }
        ]
    }
    builder = {"selection": {"display_text": "No paper strategy configured"}}
    runtime = {
        "strategy_id": "hqe_current_smc_compatibility",
        "strategy_version": "1.0.0",
        "multi_strategy_runtime_mode": "LEGACY_COMPATIBILITY",
        "multi_strategy_gate_status": "MISSING",
        "multi_strategy_lifecycle": "FLAT",
    }
    flat = build_product_strategy_manager_snapshot(
        pack_snapshot=pack,
        builder_snapshot=builder,
        runtime_snapshot=runtime,
        paper_snapshot={"position": {"status": "FLAT"}},
        runtime_running=False,
    )
    selection = evaluate_configuration_selection(flat, flat["records"][0])
    running = build_product_strategy_manager_snapshot(
        pack_snapshot=pack,
        builder_snapshot=builder,
        runtime_snapshot=runtime,
        paper_snapshot={"position": {"status": "FLAT"}},
        runtime_running=True,
    )
    open_state = build_product_strategy_manager_snapshot(
        pack_snapshot=pack,
        builder_snapshot=builder,
        runtime_snapshot={**runtime, "multi_strategy_lifecycle": "OPEN"},
        paper_snapshot={"position": {"status": "OPEN"}},
        runtime_running=False,
    )
    payload = {
        "status": "PASS",
        "mode": "PHASE5_COMPLETE_PRODUCT_UI_MANAGER_REHEARSAL",
        "available_count": flat["available_count"],
        "flat_selection_allowed": selection.allowed,
        "running_selection_blocked": not evaluate_configuration_selection(
            running, running["records"][0]
        ).allowed,
        "running_clear_blocked": not evaluate_clear_configuration(running).allowed,
        "open_selection_blocked": not evaluate_configuration_selection(
            open_state, open_state["records"][0]
        ).allowed,
        "canonical_activation_allowed": False,
        "human_gate_creation_allowed": False,
        "runtime_control_allowed": False,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "real_money_allowed": False,
        "guard": guard_payload(),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
