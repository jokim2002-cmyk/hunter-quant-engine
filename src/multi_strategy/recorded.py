"""Normalized recorded-data evaluation for reviewed HQE strategies.

The surface is mode-neutral and temporary-file based only because the verified
current SMC implementation still consumes CSV paths. It does not connect to or
change the canonical product paper runtime.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.contract import ForwardPaperCompatibilityAdapter
from src.multi_strategy.decision import StrategyDecision
from src.multi_strategy.execution import (
    ExecutionMode,
    StrategyRunMetadata,
)
from src.multi_strategy.registry import StrategyRegistry

_INPUT_SCHEMA_VERSION = "1.0.0"
_ALLOWED_EXECUTION_MODES = frozenset(
    {
        ExecutionMode.BACKTEST,
        ExecutionMode.RECORDED_REPLAY,
        ExecutionMode.FORWARD_PAPER,
    }
)

_INDEX_REQUIRED_GROUPS = (
    ("timestamp", "datetime", "date_time", "time", "date"),
    ("open", "o"),
    ("high", "h"),
    ("low", "l"),
    ("close", "c", "ltp"),
)
_PREMIUM_REQUIRED_GROUPS = (
    ("timestamp", "datetime", "date_time", "time", "date"),
    (
        "signal_side",
        "side",
        "option_type",
        "right",
        "instrument_type",
        "option_symbol",
        "symbol",
        "tradingsymbol",
        "instrument",
        "ticker",
    ),
    ("last_traded_price", "ltp", "price", "premium", "entry_price", "close"),
    ("dte", "days_to_expiry"),
)


def _normalize_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("recorded input cannot contain NaN or infinity")
        return format(value, ".15g")
    return str(value).strip()


def _normalize_rows(
    rows: Sequence[Mapping[str, Any]] | Iterable[Mapping[str, Any]],
    *,
    label: str,
    required_groups: tuple[tuple[str, ...], ...],
) -> tuple[Mapping[str, str], ...]:
    if isinstance(rows, Mapping):
        raise ValueError(f"{label} must be a sequence of row mappings")

    normalized_rows: list[Mapping[str, str]] = []
    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(
                f"{label} row {row_number} must be a mapping"
            )

        normalized: dict[str, str] = {}
        for raw_key, raw_value in row.items():
            key = str(raw_key).strip()
            if not key:
                raise ValueError(
                    f"{label} row {row_number} contains an empty column name"
                )
            if key in normalized:
                raise ValueError(
                    f"{label} row {row_number} contains duplicate column "
                    f"'{key}' after normalization"
                )
            normalized[key] = _normalize_scalar(raw_value)

        lowered = {key.lower(): value for key, value in normalized.items()}
        for group in required_groups:
            if not any(lowered.get(name, "") for name in group):
                raise ValueError(
                    f"{label} row {row_number} is missing one of "
                    f"{list(group)}"
                )

        normalized_rows.append(
            MappingProxyType(dict(sorted(normalized.items())))
        )

    if not normalized_rows:
        raise ValueError(f"{label} cannot be empty")
    return tuple(normalized_rows)


def _rows_payload(rows: tuple[Mapping[str, str], ...]) -> list[dict[str, str]]:
    return [dict(row) for row in rows]


def _csv_bytes(rows: tuple[Mapping[str, str], ...]) -> bytes:
    fieldnames = sorted(
        {
            column
            for row in rows
            for column in row
        }
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=fieldnames,
        extrasaction="raise",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    return stream.getvalue().encode("utf-8")


@dataclass(frozen=True)
class RecordedStrategyInput:
    """Immutable normalized index and option-premium snapshot."""

    index_rows: Sequence[Mapping[str, Any]]
    premium_rows: Sequence[Mapping[str, Any]]
    er20: float | None
    symbol: str
    timeframe: str
    data_start: str | None = None
    data_end: str | None = None

    def __post_init__(self) -> None:
        symbol = str(self.symbol).strip()
        timeframe = str(self.timeframe).strip()
        if not symbol:
            raise ValueError("symbol is required")
        if not timeframe:
            raise ValueError("timeframe is required")
        if self.er20 is not None:
            er20 = float(self.er20)
            if not math.isfinite(er20):
                raise ValueError("er20 must be finite")
            object.__setattr__(self, "er20", er20)

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(
            self,
            "index_rows",
            _normalize_rows(
                self.index_rows,
                label="index_rows",
                required_groups=_INDEX_REQUIRED_GROUPS,
            ),
        )
        object.__setattr__(
            self,
            "premium_rows",
            _normalize_rows(
                self.premium_rows,
                label="premium_rows",
                required_groups=_PREMIUM_REQUIRED_GROUPS,
            ),
        )

    @property
    def input_identity(self) -> str:
        payload = {
            "schema_version": _INPUT_SCHEMA_VERSION,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "er20": self.er20,
            "data_start": self.data_start,
            "data_end": self.data_end,
            "index_rows": _rows_payload(self.index_rows),
            "premium_rows": _rows_payload(self.premium_rows),
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

    def index_csv_bytes(self) -> bytes:
        return _csv_bytes(self.index_rows)

    def premium_csv_bytes(self) -> bytes:
        return _csv_bytes(self.premium_rows)

    def materialize_csv(self, directory: str | Path) -> tuple[Path, Path]:
        """Write deterministic compatibility CSVs into an explicit directory."""

        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        index_path = target / "index.csv"
        premium_path = target / "premium.csv"
        index_path.write_bytes(self.index_csv_bytes())
        premium_path.write_bytes(self.premium_csv_bytes())
        return index_path, premium_path


@dataclass(frozen=True)
class RecordedStrategyEvaluationResult:
    """One structured decision with immutable run and input identity."""

    decision: StrategyDecision
    metadata: StrategyRunMetadata
    input_identity: str
    index_row_count: int
    premium_row_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.to_dict(),
            "metadata": self.metadata.to_dict(),
            "input_identity": self.input_identity,
            "index_row_count": self.index_row_count,
            "premium_row_count": self.premium_row_count,
        }


class RegisteredRecordedEvaluator:
    """Evaluate a reviewed file-compatible strategy over normalized input."""

    def __init__(
        self,
        *,
        registry: StrategyRegistry,
        strategy_id: str = CURRENT_SMC_STRATEGY_ID,
        strategy_version: str = CURRENT_SMC_STRATEGY_VERSION,
        parameters: Mapping[str, Any] | None = None,
    ) -> None:
        self._registry = registry
        self._strategy_id = str(strategy_id)
        self._strategy_version = str(strategy_version)
        self._parameters = dict(parameters or {})

    def evaluate(
        self,
        request: RecordedStrategyInput,
        *,
        execution_mode: ExecutionMode = ExecutionMode.RECORDED_REPLAY,
    ) -> RecordedStrategyEvaluationResult:
        if execution_mode not in _ALLOWED_EXECUTION_MODES:
            raise ValueError(
                f"unsupported execution mode '{execution_mode}'"
            )

        registration = self._registry.get(
            self._strategy_id,
            self._strategy_version,
        )
        manifest = registration.manifest
        if request.timeframe != manifest.required_timeframe:
            raise ValueError(
                "recorded input timeframe "
                f"'{request.timeframe}' does not match registered strategy "
                f"requirement '{manifest.required_timeframe}'"
            )

        normalized_parameters = manifest.validate_parameters(
            self._parameters
        )
        implementation = self._registry.create(
            self._strategy_id,
            self._strategy_version,
            parameters=normalized_parameters,
        )
        if not isinstance(
            implementation,
            ForwardPaperCompatibilityAdapter,
        ):
            raise TypeError(
                "registered implementation "
                f"'{self._strategy_id}@{self._strategy_version}' "
                "does not support evaluate_from_csv compatibility"
            )

        metadata = StrategyRunMetadata.from_registration(
            registration,
            parameters=normalized_parameters,
            execution_mode=execution_mode,
            symbol=request.symbol,
            timeframe=request.timeframe,
            data_identity=request.input_identity,
            data_start=request.data_start,
            data_end=request.data_end,
        )

        with tempfile.TemporaryDirectory(
            prefix="hqe_multi_strategy_recorded_"
        ) as temporary_directory:
            index_csv, premium_csv = request.materialize_csv(
                temporary_directory
            )
            decision = implementation.evaluate_from_csv(
                index_csv,
                premium_csv,
                request.er20,
            )

        if decision.strategy_id != metadata.strategy_id:
            raise ValueError("decision strategy_id does not match metadata")
        if decision.strategy_version != metadata.strategy_version:
            raise ValueError(
                "decision strategy_version does not match metadata"
            )
        if decision.parameters_hash != metadata.parameters_hash:
            raise ValueError(
                "decision parameters_hash does not match metadata"
            )

        return RecordedStrategyEvaluationResult(
            decision=decision,
            metadata=metadata,
            input_identity=request.input_identity,
            index_row_count=len(request.index_rows),
            premium_row_count=len(request.premium_rows),
        )

    def evaluate_many(
        self,
        requests: Iterable[RecordedStrategyInput],
        *,
        execution_mode: ExecutionMode = ExecutionMode.RECORDED_REPLAY,
    ) -> tuple[RecordedStrategyEvaluationResult, ...]:
        return tuple(
            self.evaluate(
                request,
                execution_mode=execution_mode,
            )
            for request in requests
        )
