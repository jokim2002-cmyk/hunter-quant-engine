from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.multi_strategy.decision import StrategyDecision
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.manifest import ParameterSpec, StrategyManifest
from src.multi_strategy.parallel_observation import (
    ObservationLaneConfig,
    ParallelObservationError,
    close_parallel_observation_session,
    create_parallel_observation_session,
    guard_payload,
    parallel_observation_snapshot,
    run_parallel_observation_cycle,
)
from src.multi_strategy.recorded import RecordedStrategyInput
from src.multi_strategy.registry import StrategyRegistry


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(strategy_id: str, implementation_key: str) -> StrategyManifest:
    return StrategyManifest(
        strategy_id=strategy_id,
        display_name=strategy_id.replace("_", " ").title(),
        strategy_version="1.0.0",
        description="Deterministic Phase 7 rehearsal adapter.",
        implementation_key=implementation_key,
        supported_instruments=("NIFTY_INDEX_OPTION_BUY",),
        required_timeframe="5m",
        required_data_columns=(
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "option_symbol",
            "ltp",
            "dte",
        ),
        warmup_bars=1,
        parameters=(
            ParameterSpec(
                name="base_entry",
                value_type="number",
                default=100.0,
                minimum=1.0,
            ),
            ParameterSpec(
                name="target_increment",
                value_type="number",
                default=10.0,
                minimum=1.0,
            ),
        ),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
    ).require_valid()


class _RehearsalAdapter:
    def __init__(self, strategy_id: str, parameters: dict[str, Any]) -> None:
        self.strategy_id = strategy_id
        self.strategy_version = "1.0.0"
        self.parameters = dict(parameters)
        self.parameters_hash = canonical_mapping_hash(self.parameters)

    def evaluate_from_csv(
        self,
        index_csv: Path,
        premium_csv: Path,
        er20: float | None,
    ) -> StrategyDecision:
        del index_csv, premium_csv
        base = float(self.parameters["base_entry"])
        increment = float(self.parameters["target_increment"])
        opening = float(er20 or 0.0) < 1.5
        signal = "LONG" if opening else "NEUTRAL"
        option_side = "CE_BUY" if opening else "NO_TRADE"
        latest = base if opening else base + increment + 2.0
        return StrategyDecision(
            strategy_id=self.strategy_id,
            strategy_version=self.strategy_version,
            parameters_hash=self.parameters_hash,
            signal=signal,
            option_side=option_side,
            entry_eligible=opening,
            fallback_to_legacy=False,
            reason_text="rehearsal open" if opening else "rehearsal mark",
            reason_tokens=("rehearsal",),
            entry=base if opening else None,
            stop_loss=base - 5.0,
            target=base + increment,
            latest_price=latest,
            dte=3,
            close_change=0.0,
            legacy_payload={"mode": "PHASE7_REHEARSAL"},
        )


def _registry() -> StrategyRegistry:
    alpha_manifest = _manifest(
        "phase7_alpha_observer",
        "hqe.reviewed.phase7_alpha_observer_v1",
    )
    beta_manifest = _manifest(
        "phase7_beta_observer",
        "hqe.reviewed.phase7_beta_observer_v1",
    )
    registry = StrategyRegistry(
        {
            alpha_manifest.implementation_key: (
                lambda parameters: _RehearsalAdapter(
                    alpha_manifest.strategy_id,
                    dict(parameters),
                )
            ),
            beta_manifest.implementation_key: (
                lambda parameters: _RehearsalAdapter(
                    beta_manifest.strategy_id,
                    dict(parameters),
                )
            ),
        }
    )
    registry.register(alpha_manifest, source="rehearsal:reviewed-alpha")
    registry.register(beta_manifest, source="rehearsal:reviewed-beta")
    return registry


def _request(er20: float) -> RecordedStrategyInput:
    return RecordedStrategyInput(
        index_rows=(
            {
                "timestamp": "2026-07-17T09:20:00+05:30",
                "open": 25000,
                "high": 25010,
                "low": 24990,
                "close": 25005,
                "volume": 1000,
            },
        ),
        premium_rows=(
            {
                "timestamp": "2026-07-17T09:20:00+05:30",
                "signal_side": "CE_BUY",
                "last_traded_price": 100,
                "dte": 3,
            },
        ),
        er20=er20,
        symbol="NSE:NIFTY50-INDEX",
        timeframe="5m",
        data_start="2026-07-17T09:20:00+05:30",
        data_end="2026-07-17T09:20:00+05:30",
    )


def run_rehearsal(workspace: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    canonical = workspace / "HQE_PAPER_PRODUCT_RUNTIME"
    canonical.mkdir(parents=True, exist_ok=True)
    canonical_state = canonical / "MODULE_131_POSITION_STATE.json"
    canonical_ledger = canonical / "MODULE_131_PAPER_LEDGER.csv"
    selection = workspace / "HQE_MULTI_STRATEGY_ACTIVE_SELECTION.json"
    canonical_state.write_text('{"status":"FLAT","protected":true}\n', encoding="utf-8")
    canonical_ledger.write_text("event,pnl\nLEGACY,0\n", encoding="utf-8")
    selection.write_text('{"strategy_id":"protected-selection"}\n', encoding="utf-8")
    protected_hashes = {
        "state": _sha(canonical_state),
        "ledger": _sha(canonical_ledger),
        "selection": _sha(selection),
    }

    registry = _registry()
    lanes = (
        ObservationLaneConfig(
            strategy_id="phase7_alpha_observer",
            strategy_version="1.0.0",
            parameters={"base_entry": 100.0, "target_increment": 10.0},
        ),
        ObservationLaneConfig(
            strategy_id="phase7_beta_observer",
            strategy_version="1.0.0",
            parameters={"base_entry": 50.0, "target_increment": 5.0},
        ),
    )

    created = create_parallel_observation_session(
        workspace,
        registry,
        lanes,
        session_id="phase7-complete-rehearsal",
        created_by="phase7-rehearsal",
        symbol="NSE:NIFTY50-INDEX",
        timeframe="5m",
        event_time="2026-07-17T09:19:00+05:30",
    )
    opened = run_parallel_observation_cycle(
        workspace,
        registry,
        session_id="phase7-complete-rehearsal",
        cycle_id="cycle-open",
        request=_request(1.0),
        event_time="2026-07-17T09:20:00+05:30",
    )

    close_while_open_blocked = False
    try:
        close_parallel_observation_session(
            workspace,
            session_id="phase7-complete-rehearsal",
            closed_by="phase7-rehearsal",
            event_time="2026-07-17T09:21:00+05:30",
        )
    except ParallelObservationError:
        close_while_open_blocked = True

    # Reload the session from disk before the second cycle to prove restart
    # recovery and tamper verification rather than relying on process memory.
    restarted = parallel_observation_snapshot(
        workspace,
        session_id="phase7-complete-rehearsal",
    )
    closed_positions = run_parallel_observation_cycle(
        workspace,
        _registry(),
        session_id="phase7-complete-rehearsal",
        cycle_id="cycle-close",
        request=_request(2.0),
        event_time="2026-07-17T09:25:00+05:30",
    )

    duplicate_cycle_blocked = False
    try:
        run_parallel_observation_cycle(
            workspace,
            _registry(),
            session_id="phase7-complete-rehearsal",
            cycle_id="cycle-close",
            request=_request(2.0),
            event_time="2026-07-17T09:25:01+05:30",
        )
    except ParallelObservationError:
        duplicate_cycle_blocked = True

    final = close_parallel_observation_session(
        workspace,
        session_id="phase7-complete-rehearsal",
        closed_by="phase7-rehearsal",
        event_time="2026-07-17T09:26:00+05:30",
    )
    selected = final["selected_session"]
    lane_summaries = selected["lanes"]
    lane_roots = {str(Path(item["state_path"]).parent) for item in lane_summaries}
    realized = sorted(float(item["realized_pnl"]) for item in lane_summaries)

    protected_unchanged = protected_hashes == {
        "state": _sha(canonical_state),
        "ledger": _sha(canonical_ledger),
        "selection": _sha(selection),
    }

    checks = {
        "created_lane_count": created["selected_session"]["lane_count"],
        "opened_position_count": opened["selected_session"]["active_position_count"],
        "restart_cycle_count": restarted["selected_session"]["cycle_count"],
        "closed_position_count": closed_positions["selected_session"]["active_position_count"],
        "final_status": selected["status"],
        "final_cycle_count": selected["cycle_count"],
        "lane_directory_count": len(lane_roots),
        "lane_realized_pnl": realized,
        "aggregate_realized_pnl": selected["aggregate_realized_pnl"],
        "close_while_open_blocked": close_while_open_blocked,
        "duplicate_cycle_blocked": duplicate_cycle_blocked,
        "protected_canonical_files_unchanged": protected_unchanged,
        "canonical_runtime_connected": selected["canonical_runtime_connected"],
        "canonical_selection_allowed": selected["canonical_selection_allowed"],
        "canonical_activation_allowed": selected["canonical_activation_allowed"],
        "real_orders_allowed": selected["real_orders_allowed"],
        "broker_execution_allowed": selected["broker_execution_allowed"],
        "real_money_allowed": selected["real_money_allowed"],
    }
    status = (
        checks["created_lane_count"] == 2
        and checks["opened_position_count"] == 2
        and checks["restart_cycle_count"] == 1
        and checks["closed_position_count"] == 0
        and checks["final_status"] == "CLOSED"
        and checks["final_cycle_count"] == 2
        and checks["lane_directory_count"] == 2
        and checks["lane_realized_pnl"] == [7.0, 12.0]
        and checks["aggregate_realized_pnl"] == 19.0
        and checks["close_while_open_blocked"]
        and checks["duplicate_cycle_blocked"]
        and checks["protected_canonical_files_unchanged"]
        and not checks["canonical_runtime_connected"]
        and not checks["canonical_selection_allowed"]
        and not checks["canonical_activation_allowed"]
        and not checks["real_orders_allowed"]
        and not checks["broker_execution_allowed"]
        and not checks["real_money_allowed"]
    )

    return {
        "mode": "PHASE7_COMPLETE_PARALLEL_ISOLATED_PAPER_OBSERVATION_REHEARSAL",
        "status": "PASS" if status else "FAILED",
        "guard": guard_payload(),
        **checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    payload = run_rehearsal(Path(args.workspace))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
