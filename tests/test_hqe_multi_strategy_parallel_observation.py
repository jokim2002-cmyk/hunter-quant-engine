from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from src.multi_strategy.decision import StrategyDecision
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.manifest import ParameterSpec, StrategyManifest
from src.multi_strategy.parallel_observation import (
    LANE_EVENTS_FILE,
    LANE_LEDGER_FILE,
    LANE_STATE_FILE,
    ObservationLaneConfig,
    ParallelObservationError,
    close_parallel_observation_session,
    create_parallel_observation_session,
    eligible_parallel_observation_strategies,
    guard_payload,
    load_recorded_input_from_csv,
    parallel_observation_snapshot,
    run_parallel_observation_cycle,
)
from src.multi_strategy.recorded import RecordedStrategyInput
from src.multi_strategy.registry import StrategyRegistry


def manifest(strategy_id: str, implementation_key: str) -> StrategyManifest:
    return StrategyManifest(
        strategy_id=strategy_id,
        display_name=strategy_id,
        strategy_version="1.0.0",
        description="parallel observation test strategy",
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


class Adapter:
    def __init__(
        self,
        strategy_id: str,
        parameters: dict[str, Any],
        *,
        fail: bool = False,
    ) -> None:
        self.strategy_id = strategy_id
        self.parameters = dict(parameters)
        self.parameters_hash = canonical_mapping_hash(self.parameters)
        self.fail = fail

    def evaluate_from_csv(
        self,
        index_csv: Path,
        premium_csv: Path,
        er20: float | None,
    ) -> StrategyDecision:
        del index_csv, premium_csv
        if self.fail:
            raise RuntimeError("synthetic evaluation failure")
        base = float(self.parameters["base_entry"])
        increment = float(self.parameters["target_increment"])
        opening = float(er20 or 0.0) < 1.5
        return StrategyDecision(
            strategy_id=self.strategy_id,
            strategy_version="1.0.0",
            parameters_hash=self.parameters_hash,
            signal="LONG" if opening else "NEUTRAL",
            option_side="CE_BUY" if opening else "NO_TRADE",
            entry_eligible=opening,
            fallback_to_legacy=False,
            reason_text="open" if opening else "mark",
            reason_tokens=("test",),
            entry=base if opening else None,
            stop_loss=base - 5.0,
            target=base + increment,
            latest_price=base if opening else base + increment + 2.0,
            dte=3,
            close_change=0.0,
            legacy_payload={"test": True},
        )


class Incompatible:
    def generate(self, context):
        del context
        return ()


def registry(
    *,
    include_metadata: bool = False,
    include_incompatible: bool = False,
    fail_beta: bool = False,
) -> StrategyRegistry:
    alpha = manifest("phase7_alpha_test", "hqe.reviewed.phase7_alpha_test_v1")
    beta = manifest("phase7_beta_test", "hqe.reviewed.phase7_beta_test_v1")
    factories: dict[str, Any] = {
        alpha.implementation_key: (
            lambda parameters: Adapter(alpha.strategy_id, dict(parameters))
        ),
        beta.implementation_key: (
            lambda parameters: Adapter(
                beta.strategy_id,
                dict(parameters),
                fail=fail_beta,
            )
        ),
    }
    if include_incompatible:
        incompatible = manifest(
            "phase7_incompatible_test",
            "hqe.reviewed.phase7_incompatible_test_v1",
        )
        factories[incompatible.implementation_key] = lambda parameters: Incompatible()
    result = StrategyRegistry(factories)
    result.register(alpha, source="test:alpha")
    result.register(beta, source="test:beta")
    if include_metadata:
        result.register(
            manifest(
                "phase7_metadata_test",
                "hqe.unreviewed.phase7_metadata_test_v1",
            ),
            source="test:metadata",
        )
    if include_incompatible:
        result.register(incompatible, source="test:incompatible")
    return result


def lanes() -> tuple[ObservationLaneConfig, ObservationLaneConfig]:
    return (
        ObservationLaneConfig(
            strategy_id="phase7_alpha_test",
            strategy_version="1.0.0",
            parameters={"base_entry": 100.0, "target_increment": 10.0},
        ),
        ObservationLaneConfig(
            strategy_id="phase7_beta_test",
            strategy_version="1.0.0",
            parameters={"base_entry": 50.0, "target_increment": 5.0},
        ),
    )


def request(er20: float = 1.0) -> RecordedStrategyInput:
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
    )


def create(tmp_path: Path, *, use_registry: StrategyRegistry | None = None):
    return create_parallel_observation_session(
        tmp_path,
        use_registry or registry(),
        lanes(),
        session_id="session-one",
        created_by="tester",
        symbol="NSE:NIFTY50-INDEX",
        timeframe="5m",
        event_time="2026-07-17T09:19:00+05:30",
    )


def selected(snapshot: dict[str, Any]) -> dict[str, Any]:
    return snapshot["selected_session"]


def test_guard_is_strictly_observation_only():
    payload = guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["minimum_lane_count"] == 2
    assert payload["per_lane_state_isolation"] is True
    assert payload["per_lane_ledger_isolation"] is True
    assert payload["per_lane_pnl_isolation"] is True
    assert payload["canonical_runtime_connected"] is False
    assert payload["canonical_selection_allowed"] is False
    assert payload["canonical_activation_allowed"] is False
    assert payload["real_orders_allowed"] is False


def test_lane_config_has_deterministic_identity():
    first = lanes()[0]
    second = ObservationLaneConfig(
        strategy_id=first.strategy_id,
        strategy_version=first.strategy_version,
        parameters=dict(first.parameters),
    )
    assert first.parameters_hash == second.parameters_hash
    assert first.lane_id == second.lane_id


def test_session_requires_two_lanes(tmp_path):
    with pytest.raises(ParallelObservationError, match="at least two"):
        create_parallel_observation_session(
            tmp_path,
            registry(),
            (lanes()[0],),
            session_id="too-small",
            created_by="tester",
            symbol="NSE:NIFTY50-INDEX",
            timeframe="5m",
        )


def test_duplicate_lane_after_parameter_normalization_is_blocked(tmp_path):
    duplicate = (
        ObservationLaneConfig(
            strategy_id="phase7_alpha_test",
            strategy_version="1.0.0",
            parameters={},
        ),
        ObservationLaneConfig(
            strategy_id="phase7_alpha_test",
            strategy_version="1.0.0",
            parameters={"base_entry": 100.0, "target_increment": 10.0},
        ),
    )
    with pytest.raises(ParallelObservationError, match="after parameter normalization"):
        create_parallel_observation_session(
            tmp_path,
            registry(),
            duplicate,
            session_id="duplicate-normalized",
            created_by="tester",
            symbol="NSE:NIFTY50-INDEX",
            timeframe="5m",
        )


def test_metadata_only_lane_is_blocked(tmp_path):
    metadata_lane = ObservationLaneConfig(
        strategy_id="phase7_metadata_test",
        strategy_version="1.0.0",
        parameters={"base_entry": 80.0, "target_increment": 8.0},
    )
    with pytest.raises(ParallelObservationError, match="not reviewed"):
        create_parallel_observation_session(
            tmp_path,
            registry(include_metadata=True),
            (lanes()[0], metadata_lane),
            session_id="metadata-blocked",
            created_by="tester",
            symbol="NSE:NIFTY50-INDEX",
            timeframe="5m",
        )


def test_incompatible_reviewed_lane_is_blocked(tmp_path):
    incompatible_lane = ObservationLaneConfig(
        strategy_id="phase7_incompatible_test",
        strategy_version="1.0.0",
        parameters={"base_entry": 80.0, "target_increment": 8.0},
    )
    with pytest.raises(ParallelObservationError, match="lacks forward-paper"):
        create_parallel_observation_session(
            tmp_path,
            registry(include_incompatible=True),
            (lanes()[0], incompatible_lane),
            session_id="incompatible-blocked",
            created_by="tester",
            symbol="NSE:NIFTY50-INDEX",
            timeframe="5m",
        )


def test_eligible_snapshot_distinguishes_reviewed_metadata_and_incompatible():
    records = eligible_parallel_observation_strategies(
        registry(include_metadata=True, include_incompatible=True)
    )
    by_id = {record["strategy_id"]: record for record in records}
    assert by_id["phase7_alpha_test"]["eligible"] is True
    assert by_id["phase7_beta_test"]["eligible"] is True
    assert by_id["phase7_metadata_test"]["eligible"] is False
    assert by_id["phase7_incompatible_test"]["eligible"] is False


def test_create_session_writes_two_isolated_lane_namespaces(tmp_path):
    snapshot = create(tmp_path)
    session = selected(snapshot)
    assert session["lane_count"] == 2
    roots = {Path(lane["state_path"]).parent for lane in session["lanes"]}
    assert len(roots) == 2
    for root in roots:
        assert (root / LANE_STATE_FILE).is_file()
        assert (root / LANE_LEDGER_FILE).is_file()
        assert (root / LANE_EVENTS_FILE).is_file()


def test_same_strategy_with_different_parameters_can_use_two_lanes(tmp_path):
    configurations = (
        ObservationLaneConfig(
            strategy_id="phase7_alpha_test",
            strategy_version="1.0.0",
            parameters={"base_entry": 100.0, "target_increment": 10.0},
        ),
        ObservationLaneConfig(
            strategy_id="phase7_alpha_test",
            strategy_version="1.0.0",
            parameters={"base_entry": 110.0, "target_increment": 10.0},
        ),
    )
    snapshot = create_parallel_observation_session(
        tmp_path,
        registry(),
        configurations,
        session_id="same-strategy-two-params",
        created_by="tester",
        symbol="NSE:NIFTY50-INDEX",
        timeframe="5m",
    )
    assert selected(snapshot)["lane_count"] == 2
    assert selected(snapshot)["unique_strategy_count"] == 1


def test_open_cycle_writes_one_row_per_lane(tmp_path):
    create(tmp_path)
    snapshot = run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="cycle-open",
        request=request(1.0),
        event_time="2026-07-17T09:20:00+05:30",
    )
    session = selected(snapshot)
    assert session["cycle_count"] == 1
    assert session["active_position_count"] == 2
    assert {lane["ledger_row_count"] for lane in session["lanes"]} == {1}
    assert {lane["position_status"] for lane in session["lanes"]} == {"OPEN"}


def test_second_cycle_closes_lanes_with_isolated_pnl(tmp_path):
    create(tmp_path)
    run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="cycle-open",
        request=request(1.0),
    )
    snapshot = run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="cycle-close",
        request=request(2.0),
    )
    session = selected(snapshot)
    assert session["active_position_count"] == 0
    assert sorted(lane["realized_pnl"] for lane in session["lanes"]) == [7.0, 12.0]
    assert session["aggregate_realized_pnl"] == 19.0
    assert {lane["ledger_row_count"] for lane in session["lanes"]} == {2}


def test_duplicate_cycle_is_blocked(tmp_path):
    create(tmp_path)
    run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="same-cycle",
        request=request(1.0),
    )
    with pytest.raises(ParallelObservationError, match="duplicate"):
        run_parallel_observation_cycle(
            tmp_path,
            registry(),
            session_id="session-one",
            cycle_id="same-cycle",
            request=request(1.0),
        )


def test_restart_snapshot_and_new_registry_resume(tmp_path):
    create(tmp_path)
    run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="cycle-open",
        request=request(1.0),
    )
    restarted = parallel_observation_snapshot(tmp_path, session_id="session-one")
    assert selected(restarted)["cycle_count"] == 1
    resumed = run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="cycle-close",
        request=request(2.0),
    )
    assert selected(resumed)["cycle_count"] == 2


def test_evaluation_failure_leaves_all_lanes_at_prior_cycle(tmp_path):
    create(tmp_path)
    with pytest.raises(RuntimeError, match="synthetic evaluation failure"):
        run_parallel_observation_cycle(
            tmp_path,
            registry(fail_beta=True),
            session_id="session-one",
            cycle_id="failed-cycle",
            request=request(1.0),
        )
    snapshot = parallel_observation_snapshot(tmp_path, session_id="session-one")
    assert selected(snapshot)["cycle_count"] == 0
    assert {lane["ledger_row_count"] for lane in selected(snapshot)["lanes"]} == {0}


def test_open_lane_blocks_session_close(tmp_path):
    create(tmp_path)
    run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="cycle-open",
        request=request(1.0),
    )
    with pytest.raises(ParallelObservationError, match="lane is OPEN"):
        close_parallel_observation_session(
            tmp_path,
            session_id="session-one",
            closed_by="tester",
        )


def test_flat_session_closes_and_rejects_more_cycles(tmp_path):
    create(tmp_path)
    run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="cycle-open",
        request=request(1.0),
    )
    run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="cycle-close",
        request=request(2.0),
    )
    closed = close_parallel_observation_session(
        tmp_path,
        session_id="session-one",
        closed_by="tester",
    )
    assert selected(closed)["status"] == "CLOSED"
    with pytest.raises(ParallelObservationError, match="not active"):
        run_parallel_observation_cycle(
            tmp_path,
            registry(),
            session_id="session-one",
            cycle_id="after-close",
            request=request(2.0),
        )


def test_tampered_lane_state_is_detected(tmp_path):
    snapshot = create(tmp_path)
    state_path = Path(selected(snapshot)["lanes"][0]["state_path"])
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    payload["realized_pnl"] = 999999
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ParallelObservationError, match="hash verification"):
        parallel_observation_snapshot(tmp_path, session_id="session-one")


def test_tampered_lane_event_chain_is_detected(tmp_path):
    snapshot = create(tmp_path)
    events_path = Path(selected(snapshot)["lanes"][0]["events_path"])
    records = events_path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(records[0])
    payload["details"]["strategy_id"] = "tampered"
    records[0] = json.dumps(payload)
    events_path.write_text("\n".join(records) + "\n", encoding="utf-8")
    with pytest.raises(ParallelObservationError, match="hash verification"):
        parallel_observation_snapshot(tmp_path, session_id="session-one")


def test_tampered_ledger_is_detected(tmp_path):
    create(tmp_path)
    snapshot = run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="cycle-open",
        request=request(1.0),
    )
    ledger_path = Path(selected(snapshot)["lanes"][0]["ledger_path"])
    ledger_path.write_text(ledger_path.read_text() + "tampered\n", encoding="utf-8")
    with pytest.raises(ParallelObservationError):
        parallel_observation_snapshot(tmp_path, session_id="session-one")


def test_canonical_sentinel_files_are_unchanged(tmp_path):
    canonical = tmp_path / "HQE_PAPER_PRODUCT_RUNTIME"
    canonical.mkdir()
    state = canonical / "MODULE_131_POSITION_STATE.json"
    ledger = canonical / "MODULE_131_PAPER_LEDGER.csv"
    selection = tmp_path / "HQE_MULTI_STRATEGY_ACTIVE_SELECTION.json"
    state.write_text('{"status":"FLAT"}\n', encoding="utf-8")
    ledger.write_text("event,pnl\nLEGACY,0\n", encoding="utf-8")
    selection.write_text('{"strategy_id":"protected"}\n', encoding="utf-8")
    before = (state.read_bytes(), ledger.read_bytes(), selection.read_bytes())
    create(tmp_path)
    run_parallel_observation_cycle(
        tmp_path,
        registry(),
        session_id="session-one",
        cycle_id="cycle-open",
        request=request(1.0),
    )
    after = (state.read_bytes(), ledger.read_bytes(), selection.read_bytes())
    assert after == before


def test_csv_loader_builds_normalized_recorded_input(tmp_path):
    index = tmp_path / "index.csv"
    premium = tmp_path / "premium.csv"
    index.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-07-17T09:20:00+05:30,1,2,0.5,1.5,100\n",
        encoding="utf-8",
    )
    premium.write_text(
        "timestamp,signal_side,last_traded_price,dte\n"
        "2026-07-17T09:20:00+05:30,CE_BUY,100,3\n",
        encoding="utf-8",
    )
    loaded = load_recorded_input_from_csv(
        index,
        premium,
        er20=0.7,
        symbol="NSE:NIFTY50-INDEX",
        timeframe="5m",
    )
    assert loaded.er20 == 0.7
    assert loaded.symbol == "NSE:NIFTY50-INDEX"
    assert len(loaded.index_rows) == 1
    assert len(loaded.premium_rows) == 1


def test_snapshot_never_claims_ranking_or_profitability(tmp_path):
    snapshot = create(tmp_path)
    session = selected(snapshot)
    assert session["comparison_only"] is True
    assert session["ranking_or_winner_claim"] is False
    assert session["profitability_claim"] is False
    assert session["profitability_claim_allowed"] is False
