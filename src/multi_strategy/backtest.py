"""Registry-backed adapter for HQE's existing BacktestPipeline.

This module does not replace the existing backtest engine. It creates a
reviewed registered strategy, passes it to the existing pipeline, and returns
the unchanged BacktestResult alongside immutable strategy identity metadata.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.multi_strategy.contract import StrategyImplementation
from src.multi_strategy.execution import (
    ExecutionMode,
    StrategyRunMetadata,
)
from src.multi_strategy.registry import StrategyRegistry

if TYPE_CHECKING:
    from src.backtesting.backtest_result import BacktestResult
    from src.backtesting.base_trade_plan_deduplicator import (
        BaseTradePlanDeduplicator,
    )
    from src.historical_data.providers.base_historical_data_provider import (
        BaseHistoricalDataProvider,
    )
    from src.risk.base_risk_manager import BaseRiskManager
    from src.risk.risk_profile import RiskProfile
    from src.strategy.context_factories.base_strategy_context_factory import (
        BaseStrategyContextFactory,
    )
    from src.trade_planning.base_trade_candidate_planner import (
        BaseTradeCandidatePlanner,
    )


@dataclass(frozen=True)
class RegisteredBacktestResult:
    """Existing HQE backtest result plus additive strategy metadata."""

    backtest_result: "BacktestResult"
    metadata: StrategyRunMetadata

    @property
    def trades(self):
        """Preserve convenient access to the existing trade tuple."""

        return self.backtest_result.trades

    @property
    def performance_summary(self):
        """Preserve convenient access to the existing summary."""

        return self.backtest_result.performance_summary


def _default_pipeline_factory(**kwargs):
    from src.backtesting.backtest_pipeline import BacktestPipeline

    return BacktestPipeline(**kwargs)


class RegisteredBacktestPipeline:
    """Route one reviewed registry strategy through BacktestPipeline."""

    def __init__(
        self,
        *,
        registry: StrategyRegistry,
        strategy_id: str,
        strategy_version: str,
        parameters: Mapping[str, Any] | None,
        historical_data_provider: "BaseHistoricalDataProvider",
        trade_candidate_planner: "BaseTradeCandidatePlanner",
        risk_manager: "BaseRiskManager",
        risk_profile: "RiskProfile",
        symbol: str,
        timeframe: str,
        data_identity: str,
        data_start: str | None = None,
        data_end: str | None = None,
        strategy_context_factory: (
            "BaseStrategyContextFactory | None"
        ) = None,
        trade_plan_deduplicator: (
            "BaseTradePlanDeduplicator | None"
        ) = None,
        pipeline_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._registry = registry
        self._strategy_id = str(strategy_id)
        self._strategy_version = str(strategy_version)
        self._parameters = dict(parameters or {})
        self._historical_data_provider = historical_data_provider
        self._trade_candidate_planner = trade_candidate_planner
        self._risk_manager = risk_manager
        self._risk_profile = risk_profile
        self._symbol = str(symbol)
        self._timeframe = str(timeframe)
        self._data_identity = str(data_identity)
        self._data_start = data_start
        self._data_end = data_end
        self._strategy_context_factory = strategy_context_factory
        self._trade_plan_deduplicator = trade_plan_deduplicator
        self._pipeline_factory = (
            pipeline_factory or _default_pipeline_factory
        )

    def run(self) -> RegisteredBacktestResult:
        """Execute the existing pipeline with a reviewed registered strategy."""

        registration = self._registry.get(
            self._strategy_id,
            self._strategy_version,
        )
        manifest = registration.manifest
        if manifest.required_timeframe != self._timeframe:
            raise ValueError(
                "backtest timeframe "
                f"'{self._timeframe}' does not match registered strategy "
                f"requirement '{manifest.required_timeframe}'"
            )

        normalized = manifest.validate_parameters(
            self._parameters
        )
        strategy = self._registry.create(
            self._strategy_id,
            self._strategy_version,
            parameters=normalized,
        )

        if not isinstance(strategy, StrategyImplementation):
            raise TypeError(
                "registered implementation "
                f"'{self._strategy_id}@{self._strategy_version}' "
                "does not support the existing generate(context) "
                "backtest contract"
            )

        metadata = StrategyRunMetadata.from_registration(
            registration,
            parameters=normalized,
            execution_mode=ExecutionMode.BACKTEST,
            symbol=self._symbol,
            timeframe=self._timeframe,
            data_identity=self._data_identity,
            data_start=self._data_start,
            data_end=self._data_end,
        )

        pipeline_kwargs = {
            "historical_data_provider": self._historical_data_provider,
            "strategy": strategy,
            "trade_candidate_planner": self._trade_candidate_planner,
            "risk_manager": self._risk_manager,
            "risk_profile": self._risk_profile,
            "symbol": self._symbol,
            "timeframe": self._timeframe,
        }
        if self._strategy_context_factory is not None:
            pipeline_kwargs["strategy_context_factory"] = (
                self._strategy_context_factory
            )
        if self._trade_plan_deduplicator is not None:
            pipeline_kwargs["trade_plan_deduplicator"] = (
                self._trade_plan_deduplicator
            )

        existing_result = self._pipeline_factory(
            **pipeline_kwargs
        ).run()
        return RegisteredBacktestResult(
            backtest_result=existing_result,
            metadata=metadata,
        )


def write_registered_backtest_metadata(
    result: RegisteredBacktestResult,
    path: str | Path,
) -> Path:
    """Write an additive JSON sidecar without changing existing reports."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            result.metadata.to_dict(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return target
