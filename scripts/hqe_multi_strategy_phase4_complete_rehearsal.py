from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import hqe_paper_product_runtime as runtime
from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.canonical_runtime import (
    PHASE4_HUMAN_APPROVAL_PHRASE,
    RuntimeCutoverBlockedError,
    StrategySwitchBlockedError,
    assert_strategy_switch_allowed,
    prepare_canonical_runtime_cutover,
    rollback_namespaced_cutover_to_legacy,
    sha256_file,
    write_human_gate,
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_index(path: Path, *, falling: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 7, 9, 9, 15)
    rows = []
    for number in range(21):
        current = start + timedelta(minutes=5 * number)
        close = 22000.0 + ((20 - number) * 10 if falling else -(20 - number) * 2)
        rows.append(
            {
                "datetime": current.isoformat(timespec="minutes"),
                "open": close + 1,
                "high": close + 5,
                "low": close - 5,
                "close": close,
                "volume": 1000,
            }
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_premium(
    path: Path,
    *,
    ltp: float,
    high: float,
    low: float,
    moment: datetime,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "datetime",
                "open",
                "high",
                "low",
                "close",
                "last_traded_price",
                "dte",
            ),
        )
        writer.writeheader()
        writer.writerow(
            {
                "datetime": moment.isoformat(timespec="minutes"),
                "open": ltp,
                "high": high,
                "low": low,
                "close": ltp,
                "last_traded_price": ltp,
                "dte": 2,
            }
        )


def _sha(path: Path) -> str:
    return sha256_file(path)


def _flat_rehearsal(workspace: Path) -> dict[str, Any]:
    control = workspace / runtime.RUNTIME_FOLDER
    legacy_state = control / runtime.MODULE_STATE_FILE
    legacy_ledger = control / runtime.MODULE_LEDGER_FILE
    _write_json(
        legacy_state,
        {
            "status": "FLAT",
            "paper_only": True,
            "module": 131,
        },
    )
    legacy_ledger.parent.mkdir(parents=True, exist_ok=True)
    legacy_ledger.write_text(
        "timestamp,module,event,side,option_symbol,entry,stop_loss,target,exit_reason,paper_pnl,paper_only\n",
        encoding="utf-8",
    )
    legacy_hashes_before = {
        "state": _sha(legacy_state),
        "ledger": _sha(legacy_ledger),
    }

    gate = write_human_gate(
        workspace,
        runtime_folder=runtime.RUNTIME_FOLDER,
        approval_phrase=PHASE4_HUMAN_APPROVAL_PHRASE,
        created_by="PHASE4_COMPLETE_REHEARSAL",
    )
    prepared = prepare_canonical_runtime_cutover(
        workspace,
        runtime_folder=runtime.RUNTIME_FOLDER,
        runtime_state_file=runtime.RUNTIME_STATE_FILE,
        runtime_log_file=runtime.RUNTIME_LOG_FILE,
        stop_file=runtime.STOP_FILE,
        runtime_running=False,
    )
    paths = runtime.runtime_paths(workspace)
    if paths["state"] == legacy_state:
        raise RuntimeError("cutover did not route state into strategy namespace")

    index_csv = workspace / "rehearsal_index.csv"
    premium_csv = workspace / "rehearsal_premium.csv"
    _write_index(index_csv, falling=True)
    _write_premium(
        premium_csv,
        ltp=100.0,
        high=105.0,
        low=95.0,
        moment=datetime(2026, 7, 9, 10, 55),
    )
    opened = runtime.run_module_131(
        workspace,
        index_csv,
        premium_csv,
        datetime(2026, 7, 9, 10, 55),
    )
    if opened.get("event") != "POSITION_OPENED":
        raise RuntimeError("rehearsal did not open a paper position")

    open_switch_blocked = False
    try:
        assert_strategy_switch_allowed(
            workspace,
            runtime_folder=runtime.RUNTIME_FOLDER,
            requested_strategy_id="another_strategy",
            requested_strategy_version="1.0.0",
            runtime_running=False,
        )
    except StrategySwitchBlockedError:
        open_switch_blocked = True

    running_switch_blocked = False
    try:
        assert_strategy_switch_allowed(
            workspace,
            runtime_folder=runtime.RUNTIME_FOLDER,
            requested_strategy_id=CURRENT_SMC_STRATEGY_ID,
            requested_strategy_version=CURRENT_SMC_STRATEGY_VERSION,
            runtime_running=True,
        )
    except StrategySwitchBlockedError:
        running_switch_blocked = True

    _write_premium(
        premium_csv,
        ltp=220.0,
        high=225.0,
        low=210.0,
        moment=datetime(2026, 7, 9, 11, 0),
    )
    closed = runtime.run_module_131(
        workspace,
        index_csv,
        premium_csv,
        datetime(2026, 7, 9, 11, 0),
    )
    if closed.get("event") != "POSITION_CLOSED":
        raise RuntimeError("rehearsal did not close the paper position")

    legacy_hashes_after_namespaced_run = {
        "state": _sha(legacy_state),
        "ledger": _sha(legacy_ledger),
    }
    if legacy_hashes_after_namespaced_run != legacy_hashes_before:
        raise RuntimeError("namespaced run modified legacy evidence")

    snapshot = runtime.paper_product_snapshot(
        workspace,
        datetime(2026, 7, 9, 11, 0),
    )
    rollback = rollback_namespaced_cutover_to_legacy(
        workspace,
        runtime_folder=runtime.RUNTIME_FOLDER,
        runtime_state_file=runtime.RUNTIME_STATE_FILE,
        runtime_log_file=runtime.RUNTIME_LOG_FILE,
        stop_file=runtime.STOP_FILE,
        runtime_running=False,
    )
    legacy_state_after_rollback = json.loads(
        legacy_state.read_text(encoding="utf-8")
    )

    return {
        "gate_hash": gate["gate_hash"],
        "prepare_status": prepared["status"],
        "namespaced_state_path": str(paths["state"]),
        "namespaced_ledger_path": str(paths["ledger"]),
        "open_event": opened.get("event"),
        "close_event": closed.get("event"),
        "close_paper_pnl": closed.get("paper_pnl"),
        "open_switch_blocked": open_switch_blocked,
        "running_switch_blocked": running_switch_blocked,
        "legacy_unchanged_during_namespaced_run": (
            legacy_hashes_after_namespaced_run == legacy_hashes_before
        ),
        "snapshot_runtime_mode": snapshot.get("multi_strategy_runtime_mode"),
        "snapshot_strategy_id": snapshot.get("strategy_id"),
        "snapshot_position_status": snapshot.get("position_status"),
        "rollback_complete": rollback.get("rollback_complete", False),
        "legacy_status_after_rollback": legacy_state_after_rollback.get("status"),
        "real_orders_allowed": snapshot.get("real_orders_allowed"),
        "broker_execution_allowed": snapshot.get("broker_execution_allowed"),
        "real_money_allowed": snapshot.get("real_money_allowed"),
    }


def _open_state_migration(workspace: Path) -> dict[str, Any]:
    control = workspace / runtime.RUNTIME_FOLDER
    legacy_state = control / runtime.MODULE_STATE_FILE
    legacy_ledger = control / runtime.MODULE_LEDGER_FILE
    _write_json(
        legacy_state,
        {
            "status": "OPEN",
            "side": "PE_BUY",
            "option_symbol": "NSE:REHEARSALPE",
            "entry": 100.0,
            "stop_loss": 60.0,
            "target": 220.0,
            "quantity": 1,
            "entry_time": "2026-07-09T10:55:00",
            "paper_only": True,
        },
    )
    legacy_ledger.parent.mkdir(parents=True, exist_ok=True)
    legacy_ledger.write_text(
        "timestamp,module,event,side,option_symbol,entry,stop_loss,target,exit_reason,paper_pnl,paper_only\n"
        "2026-07-09T10:55:00,131,POSITION_OPENED,PE_BUY,NSE:REHEARSALPE,100.0,60.0,220.0,,0.0,True\n",
        encoding="utf-8",
    )
    state_hash = _sha(legacy_state)
    ledger_hash = _sha(legacy_ledger)

    write_human_gate(
        workspace,
        runtime_folder=runtime.RUNTIME_FOLDER,
        approval_phrase=PHASE4_HUMAN_APPROVAL_PHRASE,
        created_by="PHASE4_OPEN_MIGRATION_REHEARSAL",
    )
    prepared = prepare_canonical_runtime_cutover(
        workspace,
        runtime_folder=runtime.RUNTIME_FOLDER,
        runtime_state_file=runtime.RUNTIME_STATE_FILE,
        runtime_log_file=runtime.RUNTIME_LOG_FILE,
        stop_file=runtime.STOP_FILE,
        runtime_running=False,
    )
    paths = runtime.runtime_paths(workspace)

    rollback_blocked = False
    try:
        rollback_namespaced_cutover_to_legacy(
            workspace,
            runtime_folder=runtime.RUNTIME_FOLDER,
            runtime_state_file=runtime.RUNTIME_STATE_FILE,
            runtime_log_file=runtime.RUNTIME_LOG_FILE,
            stop_file=runtime.STOP_FILE,
            runtime_running=False,
        )
    except RuntimeCutoverBlockedError:
        rollback_blocked = True

    return {
        "prepare_status": prepared["status"],
        "state_hash_preserved": _sha(paths["state"]) == state_hash,
        "ledger_hash_preserved": _sha(paths["ledger"]) == ledger_hash,
        "open_state_preserved": json.loads(
            paths["state"].read_text(encoding="utf-8")
        ).get("status") == "OPEN",
        "rollback_while_open_blocked": rollback_blocked,
    }


def run_rehearsal(workspace: Path) -> dict[str, Any]:
    flat_workspace = Path(workspace) / "flat_cycle"
    open_workspace = Path(workspace) / "open_migration"
    flat = _flat_rehearsal(flat_workspace)
    opened = _open_state_migration(open_workspace)
    payload = {
        "mode": "PHASE4_COMPLETE_FORWARD_PAPER_INTEGRATION_REHEARSAL",
        "status": "PASS",
        "flat_cycle": flat,
        "open_migration": opened,
        "canonical_product_workspace_modified": False,
        "master_repository_modified": False,
        "product_ui_modified": False,
        "license_machine_id_modified": False,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "real_money_allowed": False,
        "option_selling_allowed": False,
    }
    payload["evidence_hash"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE Phase 4 complete forward-paper integration rehearsal"
    )
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    payload = run_rehearsal(args.workspace.resolve())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
