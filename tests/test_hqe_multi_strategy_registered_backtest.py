from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

import pytest

from src.multi_strategy.backtest import (
    RegisteredBacktestPipeline,
    write_registered_backtest_metadata,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.manifest import (
    CANONICAL_OPTION_MAPPING,
    CANONICAL_SIGNALS,
    StrategyManifest,
)
from src.multi_strategy.registry import StrategyRegistry
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal


FAKE_ID = "test_registered_backtest"
FAKE_VERSION = "1.0.0"
FAKE_IMPLEMENTATION_KEY = "hqe.test.registered_backtest_v1"


class FakeStrategy:
    def generate(self, context):
        return (
            TradeSignal(
                signal_type=SignalType.NEUTRAL,
                strength=SignalStrength.WEAK,
                confidence=0.0,
                rationale=("test",),
                created_at=datetime(2026, 1, 1),
            ),
        )


def build_fake_registry() -> StrategyRegistry:
    manifest = StrategyManifest(
        strategy_id=FAKE_ID,
        display_name="Test Registered Backtest",
        strategy_version=FAKE_VERSION,
        description="Test-only reviewed strategy.",
        implementation_key=FAKE_IMPLEMENTATION_KEY,
        supported_instruments=("TEST",),
        required_timeframe="5m",
        required_data_columns=("datetime", "open", "high", "low", "close"),
        warmup_bars=0,
        parameters=(),
        state_schema_version="1.0.0",
        compatibility_version="1.0.0",
        signal_outputs=CANONICAL_SIGNALS,
        option_mapping=CANONICAL_OPTION_MAPPING,
    )
    registry = StrategyRegistry(
        {FAKE_IMPLEMENTATION_KEY: lambda parameters: FakeStrategy()}
    )
    registry.register(manifest)
    return registry


@dataclass(frozen=True)
class FakeBacktestResult:
    trades: tuple
    performance_summary: object


class FakePipeline:
    def __init__(self, calls, result, **kwargs):
        self._calls = calls
        self._result = result
        self._calls.append(kwargs)

    def run(self):
        return self._result


def build_registered_pipeline(
    *,
    registry=None,
    strategy_id=FAKE_ID,
    strategy_version=FAKE_VERSION,
    parameters=None,
    calls=None,
    result=None,
):
    calls = [] if calls is None else calls
    result = result or FakeBacktestResult(
        trades=("trade-1",),
        performance_summary={"total_trades": 1},
    )

    def factory(**kwargs):
        return FakePipeline(calls, result, **kwargs)

    pipeline = RegisteredBacktestPipeline(
        registry=registry or build_fake_registry(),
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        parameters=parameters or {},
        historical_data_provider=object(),
        trade_candidate_planner=object(),
        risk_manager=object(),
        risk_profile=object(),
        symbol="NIFTY",
        timeframe="5m",
        data_identity="sha256:dataset",
        data_start="2026-01-01T09:15:00",
        data_end="2026-01-31T15:30:00",
        pipeline_factory=factory,
    )
    return pipeline, calls, result


def test_registered_backtest_delegates_to_existing_pipeline():
    pipeline, calls, existing = build_registered_pipeline()
    result = pipeline.run()

    assert result.backtest_result is existing
    assert result.trades == ("trade-1",)
    assert len(calls) == 1
    assert isinstance(calls[0]["strategy"], FakeStrategy)
    assert calls[0]["symbol"] == "NIFTY"
    assert calls[0]["timeframe"] == "5m"
    assert result.metadata.strategy_id == FAKE_ID
    assert result.metadata.parameters == {}
    assert result.metadata.data_identity == "sha256:dataset"


def test_registered_backtest_metadata_sidecar_is_additive(tmp_path):
    pipeline, _, _ = build_registered_pipeline()
    result = pipeline.run()

    target = write_registered_backtest_metadata(
        result,
        tmp_path / "strategy_metadata.json",
    )
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert payload["execution_mode"] == "BACKTEST"
    assert payload["strategy_id"] == FAKE_ID
    assert payload["data_start"] == "2026-01-01T09:15:00"


def test_registered_backtest_rejects_wrong_timeframe():
    calls = []
    result = FakeBacktestResult(
        trades=(),
        performance_summary={"total_trades": 0},
    )

    def factory(**kwargs):
        return FakePipeline(calls, result, **kwargs)

    pipeline = RegisteredBacktestPipeline(
        registry=build_fake_registry(),
        strategy_id=FAKE_ID,
        strategy_version=FAKE_VERSION,
        parameters={},
        historical_data_provider=object(),
        trade_candidate_planner=object(),
        risk_manager=object(),
        risk_profile=object(),
        symbol="NIFTY",
        timeframe="15m",
        data_identity="sha256:dataset",
        pipeline_factory=factory,
    )

    with pytest.raises(ValueError, match="does not match"):
        pipeline.run()
    assert calls == []


def test_current_file_compatibility_adapter_fails_closed_for_backtest():
    pipeline, _, _ = build_registered_pipeline(
        registry=build_phase3_registry(),
        strategy_id=CURRENT_SMC_STRATEGY_ID,
        strategy_version=CURRENT_SMC_STRATEGY_VERSION,
    )

    with pytest.raises(TypeError, match="does not support"):
        pipeline.run()
