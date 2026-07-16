from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts import hqe_smc_live_direction as legacy
from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.decision import StrategyDecision
from src.multi_strategy.execution import (
    ExecutionMode,
    canonical_mapping_hash,
)
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.recorded import (
    RecordedStrategyInput,
    RegisteredRecordedEvaluator,
)
from src.multi_strategy.registry import StrategyRegistry


FAKE_ID = "test_recorded_evaluator"
FAKE_VERSION = "1.0.0"
FAKE_KEY = "hqe.test.recorded_evaluator_v1"


def index_rows(count: int = 30) -> list[dict]:
    rows = []
    for index in range(count):
        base = 24000.0 + index
        rows.append(
            {
                "timestamp": f"2026-07-13 10:{index:02d}:00",
                "open": base,
                "high": base + 10,
                "low": base - 10,
                "close": base + 2,
                "volume": 1000 + index,
            }
        )
    return rows


def premium_rows() -> list[dict]:
    return [
        {
            "timestamp": "2026-07-13 10:29:00",
            "symbol": "NIFTY_TEST_PE",
            "ltp": "95",
            "dte": "2",
        },
        {
            "timestamp": "2026-07-13 10:29:00",
            "symbol": "NIFTY_TEST_CE",
            "ltp": "120",
            "dte": "2",
        },
    ]


def request(**overrides) -> RecordedStrategyInput:
    values = {
        "index_rows": index_rows(),
        "premium_rows": premium_rows(),
        "er20": 0.45,
        "symbol": "NIFTY",
        "timeframe": "5m",
        "data_start": "2026-07-13T09:15:00",
        "data_end": "2026-07-13T10:29:00",
    }
    values.update(overrides)
    return RecordedStrategyInput(**values)


class FakeRecordedAdapter:
    def __init__(self, parameters):
        self.parameters_hash = canonical_mapping_hash(parameters)
        self.seen_paths: list[Path] = []

    def evaluate_from_csv(self, index_csv, premium_csv, er20):
        self.seen_paths = [Path(index_csv), Path(premium_csv)]
        assert self.seen_paths[0].is_file()
        assert self.seen_paths[1].is_file()
        return StrategyDecision(
            strategy_id=FAKE_ID,
            strategy_version=FAKE_VERSION,
            parameters_hash=self.parameters_hash,
            signal="NEUTRAL",
            option_side="NO_TRADE",
            entry_eligible=False,
            fallback_to_legacy=False,
            reason_text=f"ER20={er20}",
            reason_tokens=(f"ER20={er20}",),
            entry=None,
            stop_loss=None,
            target=None,
            latest_price=None,
            dte=None,
            close_change=None,
            legacy_payload={"decision": "NEUTRAL"},
        )


def fake_registry(holder: dict) -> StrategyRegistry:
    manifest = StrategyManifest(
        strategy_id=FAKE_ID,
        display_name="Test Recorded Evaluator",
        strategy_version=FAKE_VERSION,
        description="Test-only file-compatible evaluator.",
        implementation_key=FAKE_KEY,
        supported_instruments=("TEST",),
        required_timeframe="5m",
        required_data_columns=("timestamp", "open", "high", "low", "close"),
        warmup_bars=0,
        parameters=(),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    )

    def factory(parameters):
        adapter = FakeRecordedAdapter(parameters)
        holder["adapter"] = adapter
        return adapter

    registry = StrategyRegistry({FAKE_KEY: factory})
    registry.register(manifest)
    return registry


def test_input_identity_ignores_mapping_key_order():
    first = request()
    reversed_index = [
        dict(reversed(list(row.items())))
        for row in index_rows()
    ]
    reversed_premium = [
        dict(reversed(list(row.items())))
        for row in premium_rows()
    ]
    second = request(
        index_rows=reversed_index,
        premium_rows=reversed_premium,
    )

    assert first.input_identity == second.input_identity
    assert first.index_csv_bytes() == second.index_csv_bytes()
    assert first.premium_csv_bytes() == second.premium_csv_bytes()


def test_input_identity_changes_when_data_changes():
    first = request()
    changed = index_rows()
    changed[-1]["close"] = 99999
    second = request(index_rows=changed)

    assert first.input_identity != second.input_identity


def test_recorded_evaluator_adds_metadata_and_removes_temp_files():
    holder = {}
    evaluator = RegisteredRecordedEvaluator(
        registry=fake_registry(holder),
        strategy_id=FAKE_ID,
        strategy_version=FAKE_VERSION,
    )
    result = evaluator.evaluate(request())

    assert result.metadata.execution_mode is ExecutionMode.RECORDED_REPLAY
    assert result.metadata.data_identity == result.input_identity
    assert result.index_row_count == 30
    assert result.premium_row_count == 2
    assert result.decision.signal == "NEUTRAL"
    assert all(
        not path.exists()
        for path in holder["adapter"].seen_paths
    )


def test_same_request_and_implementation_have_mode_neutral_decision():
    holder = {}
    evaluator = RegisteredRecordedEvaluator(
        registry=fake_registry(holder),
        strategy_id=FAKE_ID,
        strategy_version=FAKE_VERSION,
    )
    recorded = evaluator.evaluate(
        request(),
        execution_mode=ExecutionMode.RECORDED_REPLAY,
    )
    forward = evaluator.evaluate(
        request(),
        execution_mode=ExecutionMode.FORWARD_PAPER,
    )

    assert recorded.decision == forward.decision
    assert recorded.input_identity == forward.input_identity
    assert recorded.metadata.execution_mode is ExecutionMode.RECORDED_REPLAY
    assert forward.metadata.execution_mode is ExecutionMode.FORWARD_PAPER


def test_evaluate_many_preserves_request_order():
    holder = {}
    evaluator = RegisteredRecordedEvaluator(
        registry=fake_registry(holder),
        strategy_id=FAKE_ID,
        strategy_version=FAKE_VERSION,
    )
    second_rows = index_rows()
    second_rows[-1]["close"] = 25000
    inputs = (request(), request(index_rows=second_rows))

    results = evaluator.evaluate_many(inputs)

    assert tuple(item.input_identity for item in results) == tuple(
        item.input_identity for item in inputs
    )


def test_malformed_or_empty_input_fails_closed():
    with pytest.raises(ValueError, match="cannot be empty"):
        request(index_rows=[])
    with pytest.raises(ValueError, match="missing one of"):
        request(index_rows=[{"timestamp": "2026-07-13 10:00:00"}])
    with pytest.raises(ValueError, match="NaN or infinity"):
        request(
            index_rows=[
                {
                    "timestamp": "2026-07-13 10:00:00",
                    "open": float("nan"),
                    "high": 2,
                    "low": 0,
                    "close": 1,
                }
            ]
        )


def test_timeframe_mismatch_fails_before_strategy_execution():
    holder = {}
    evaluator = RegisteredRecordedEvaluator(
        registry=fake_registry(holder),
        strategy_id=FAKE_ID,
        strategy_version=FAKE_VERSION,
    )
    with pytest.raises(ValueError, match="does not match"):
        evaluator.evaluate(request(timeframe="15m"))
    assert holder == {}


def test_current_smc_registered_surface_preserves_legacy_payload(
    monkeypatch,
):
    monkeypatch.setattr(
        legacy,
        "evaluate_from_csv",
        lambda index_csv, premium_csv, candidate, er20: {
            "fallback_to_legacy": False,
            "decision": "LONG",
            "side": "CE_BUY",
            "signal_generated": True,
            "reason": "SMC_DECISION=LONG;OPTION_SIDE=CE_BUY;TEST",
            "entry": 120.0,
            "stop_loss": 72.0,
            "target": 264.0,
            "ltp": 120.0,
            "dte": 2,
            "close_change": 200.0,
        },
    )
    evaluator = RegisteredRecordedEvaluator(
        registry=build_phase3_registry(),
        strategy_id=CURRENT_SMC_STRATEGY_ID,
        strategy_version=CURRENT_SMC_STRATEGY_VERSION,
    )

    result = evaluator.evaluate(request())

    assert result.decision.signal == "LONG"
    assert result.decision.option_side == "CE_BUY"
    assert result.decision.to_legacy_payload()["entry"] == 120.0
    assert result.metadata.strategy_id == CURRENT_SMC_STRATEGY_ID
